"""Upload checks and document code/version rules (same rules as frontend `utils/documentValidation.js`)."""
import re

ALLOWED_EXTENSIONS = ("pdf", "docx", "txt", "md", "csv")
# Other spellings of an allowed format. They are stored under the canonical extension so extraction,
# preview and citations handle one name per format.
EXTENSION_ALIASES = {"markdown": "md"}
CODE_PATTERN = re.compile(r"^DOC-\d{2,}$")
VERSION_PATTERN = re.compile(r"^\d+(\.\d+){0,2}$")

_PDF_MAGIC = b"%PDF"
# DOCX is a ZIP container, so the file must start with the local-file-header signature.
_ZIP_MAGIC = b"PK\x03\x04"


class FileRejected(ValueError):
    """The upload itself is unusable. `code` is the frontend i18n key."""

    def __init__(self, code: str, **params):
        super().__init__(code)
        self.code = code
        self.params = params


def file_extension(file_name: str) -> str:
    """Lowercase extension without the dot, with aliases mapped to their canonical name (.markdown → md)."""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    return EXTENSION_ALIASES.get(ext, ext)


def check_file(content: bytes, ext: str, max_bytes: int) -> None:
    """Reject unsupported, oversized, empty or mislabelled files before anything is stored.

    Raises:
        FileRejected: with code err_file_type, err_file_too_large, err_file_empty or err_file_corrupt.
    """
    if ext not in ALLOWED_EXTENSIONS:
        raise FileRejected("err_file_type", ext=ext or "?",
                           list=", ".join(f".{e}" for e in (*ALLOWED_EXTENSIONS, *EXTENSION_ALIASES)))
    if len(content) > max_bytes:
        raise FileRejected("err_file_too_large", max=max_bytes // (1024 * 1024))
    if not content or (ext in ("txt", "md", "csv") and not content.strip()):
        raise FileRejected("err_file_empty")
    # Extension alone is not trusted: a renamed .exe must not reach the PDF parser.
    if ext == "pdf" and not content.startswith(_PDF_MAGIC):
        raise FileRejected("err_file_corrupt", ext=ext)
    if ext == "docx" and not content.startswith(_ZIP_MAGIC):
        raise FileRejected("err_file_corrupt", ext=ext)


def normalize_version(value: str) -> str:
    return value.strip().removeprefix("v").removeprefix("V")


def compare_versions(a: str, b: str) -> int:
    """Numeric comparison so "1.10" > "1.9". Returns >0, 0 or <0."""
    pa = [int(p) for p in normalize_version(a).split(".")]
    pb = [int(p) for p in normalize_version(b).split(".")]
    width = max(len(pa), len(pb))
    pa += [0] * (width - len(pa))
    pb += [0] * (width - len(pb))
    return (pa > pb) - (pa < pb)
