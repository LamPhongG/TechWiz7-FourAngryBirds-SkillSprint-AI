"""Background generation with live progress, so HR sees where a long AI run is instead of a frozen spinner.

`POST /paths/jobs` starts a job and returns at once; the browser polls `GET /paths/jobs/{id}`. The job runs the same
service call as `POST /paths` in its own thread and database session, and folds the pipeline's progress events into a
`state` the UI draws as a timeline.

Jobs live in this process's memory: they survive neither a restart nor a second worker process. That is enough for
one uvicorn process; with several workers they would need a shared store (a table or Redis).
"""
import logging
import threading
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field

from app.core.errors import AppError
from app.db.base import new_id
from app.db.session import SessionLocal
from app.models import LearningPath, User

log = logging.getLogger(__name__)

STEPS = ("sources", "analysis", "plan", "modules", "coverage", "saving")
# A finished job is kept this long so a slow poll still sees its result.
KEEP_SECONDS = 3600


@dataclass
class Job:
    id: str
    kind: str
    actor_id: str
    started: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    status: str = "running"  # running | done | failed
    path_id: str | None = None
    error: dict | None = None
    state: dict = field(default_factory=lambda: {
        "steps": {s: ("active" if s == "sources" else "pending") for s in STEPS},
        "modules": [],
    })


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def _advance(steps: dict, done: str, nxt: str | None) -> None:
    steps[done] = "done"
    if nxt and steps[nxt] == "pending":
        steps[nxt] = "active"


def apply_event(state: dict, event: str, data: dict) -> None:
    """Fold one pipeline event into the job state (pure, so it is testable without threads)."""
    steps = state["steps"]
    if event == "sources":
        state["sources"] = data
        _advance(steps, "sources", "analysis")
    elif event == "analysis":
        state["analysis"] = data
        _advance(steps, "analysis", "plan")
    elif event == "plan":
        state["engine"] = data["engine"]
        state["modules"] = [m | {"phase": "waiting"} for m in data["modules"]]
        _advance(steps, "plan", "modules")
    elif event == "module":
        module = next((m for m in state["modules"] if m["id"] == data["id"]), None)
        if module is not None:
            module.update(data)
    elif event == "coverage":
        state["coverage"] = data
        _advance(steps, "modules", "coverage")
        steps["coverage"] = "done"
    elif event == "assemble":
        _advance(steps, "modules", None)
        if steps["coverage"] != "done":
            steps["coverage"] = "skipped"
        steps["saving"] = "active"
    elif event == "saving":
        # Content supplied by the client skips the pipeline; mark the skipped steps so the timeline still closes.
        for step in ("analysis", "plan", "modules", "coverage"):
            if steps[step] in ("pending", "active"):
                steps[step] = "skipped"
        steps["saving"] = "active"


def start(kind: str, actor: User, work: Callable[..., LearningPath]) -> Job:
    """Run `work(db, actor, progress)` in a thread. `work` must commit and return the path it created or changed."""
    _forget_old()
    job = Job(id=new_id("JOB"), kind=kind, actor_id=actor.id)
    with _lock:
        _jobs[job.id] = job
    threading.Thread(target=_run, args=(job, work), name=f"job-{job.id}", daemon=True).start()
    return job


def get(job_id: str, actor: User) -> Job | None:
    """A copy of the job, or None when it does not exist or belongs to someone else."""
    with _lock:
        job = _jobs.get(job_id)
        return deepcopy(job) if job and job.actor_id == actor.id else None


def _progress(job: Job) -> Callable[..., None]:
    def emit(event: str, **data) -> None:
        # Module events arrive from the pipeline's worker threads at the same time.
        with _lock:
            apply_event(job.state, event, data)
            job.updated = time.time()
    return emit


def _run(job: Job, work: Callable[..., LearningPath]) -> None:
    try:
        with SessionLocal() as db:
            actor = db.get(User, job.actor_id)
            path = work(db, actor, _progress(job))
            path_id = path.id
    except AppError as exc:
        _finish(job, error={"code": exc.code, "detail": exc.message, "vars": exc.params}, status_code=exc.status_code)
    except Exception:  # noqa: BLE001 — a crashed thread would leave the job "running" forever; report it instead
        log.exception("Generation job %s failed", job.id)
        _finish(job, error={"code": "err_generation_failed", "detail": "Generation failed unexpectedly", "vars": {}})
    else:
        _finish(job, path_id=path_id)


def _finish(job: Job, *, path_id: str | None = None, error: dict | None = None, status_code: int | None = None) -> None:
    with _lock:
        if error is None:
            steps = job.state["steps"]
            for step in STEPS:
                if steps[step] in ("pending", "active"):
                    steps[step] = "done" if step == "saving" else "skipped"
            job.status, job.path_id = "done", path_id
        else:
            job.state["steps"] = {s: ("failed" if v == "active" else v) for s, v in job.state["steps"].items()}
            job.status, job.error = "failed", error | ({"status": status_code} if status_code else {})
        job.updated = time.time()


def _forget_old() -> None:
    cutoff = time.time() - KEEP_SECONDS
    with _lock:
        for job_id in [j.id for j in _jobs.values() if j.status != "running" and j.updated < cutoff]:
            del _jobs[job_id]
