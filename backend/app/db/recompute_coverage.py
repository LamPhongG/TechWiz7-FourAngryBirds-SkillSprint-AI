"""Recompute the stored Coverage Score of every learning path from its current content and the current matrix.

Needed after the Role Requirement Matrix changes (import, edit) or after the coverage rule itself changes, since
`learning_paths.coverage` is only computed when a path is created, regenerated or edited.

Run from `backend/`:  python -m app.db.recompute_coverage
"""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import LearningPath
from app.services.role_matrix import compute_coverage


def run() -> list[tuple[str, float | None, float | None]]:
    """Returns (path id, old score, new score) for every path."""
    changes = []
    with SessionLocal() as db:
        for path in db.scalars(select(LearningPath).order_by(LearningPath.id)):
            old = (path.coverage or {}).get("score") if isinstance(path.coverage, dict) else None
            if path.target_job_position_id:
                path.coverage = compute_coverage(db, path.stages, path.target_job_position_id)
            changes.append((path.id, old, (path.coverage or {}).get("score")))
        db.commit()
    return changes


def _fmt(score: float | None) -> str:
    return "—" if score is None else f"{score * 100:.0f}%"


if __name__ == "__main__":
    for path_id, old, new in run():
        print(f"{path_id}: {_fmt(old)} -> {_fmt(new)}")
