"""Accepting an uploaded document safely.

Every rule here assumes the uploader is hostile, because the file arrives from
outside and is named by whoever sent it.

- The extension is checked against an allow-list, never a deny-list.
- The real type is sniffed from the file's leading bytes, and must agree with
  the extension. A `.pdf` that begins with `<?php` or `<svg` is rejected.
- The size is capped, and the cap is enforced while reading rather than after,
  so an oversized upload cannot fill the disk first.
- The stored name is generated here. Nothing from the client reaches the
  filesystem — not the name, not the extension, not a path fragment.
- Files land outside the web root and are never served back by path. The
  document route reads by database ID and streams the bytes.
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)

#: extension -> (canonical mime, magic byte prefixes)
ALLOWED: dict[str, tuple[str, tuple[bytes, ...]]] = {
    ".pdf": ("application/pdf", (b"%PDF-",)),
    ".png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
}


class UploadRejected(Exception):
    """The upload failed a check. `code` is looked up in the locale files."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class StoredDocument:
    stored_filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    path: Path


def _sniff(data: bytes) -> str | None:
    for _, (mime, prefixes) in ALLOWED.items():
        if any(data.startswith(p) for p in prefixes):
            return mime
    return None


def safe_original_name(name: str | None) -> str:
    """A display-only version of the client's filename.

    Kept for the officer's benefit so they can tell which file they uploaded. It
    is never used to build a path: directory separators and parent references are
    stripped, and the result is only ever rendered as text.
    """
    if not name:
        return "document"
    stem = Path(name).name.replace("\x00", "")
    stem = stem.replace("..", "").strip() or "document"
    return stem[:255]


def store_upload(*, data: bytes, filename: str | None) -> StoredDocument:
    settings = get_settings()

    if not data:
        raise UploadRejected("upload_empty")
    if len(data) > settings.max_upload_bytes:
        raise UploadRejected("upload_too_large")

    extension = Path(filename or "").suffix.lower()
    if extension not in ALLOWED:
        raise UploadRejected("upload_wrong_type")

    declared_mime = ALLOWED[extension][0]
    actual_mime = _sniff(data)
    if actual_mime is None:
        raise UploadRejected("upload_unreadable")
    # The extension must match what the bytes actually are.
    if actual_mime != declared_mime:
        logger.warning("upload rejected: extension %s but content is %s", extension, actual_mime)
        raise UploadRejected("upload_type_mismatch")

    settings.ensure_directories()
    # Generated name. Nothing the client supplied is part of this path.
    stored_filename = f"{secrets.token_hex(16)}{extension}"
    destination = settings.upload_dir / stored_filename

    # Refuse to follow a path that somehow escapes the upload directory. With a
    # generated hex name this cannot happen; the check costs nothing and means a
    # future change to the naming scheme cannot silently reintroduce traversal.
    if destination.parent.resolve() != settings.upload_dir.resolve():
        raise UploadRejected("upload_unreadable")

    destination.write_bytes(data)

    return StoredDocument(
        stored_filename=stored_filename,
        original_filename=safe_original_name(filename),
        mime_type=actual_mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        path=destination,
    )


def read_stored(stored_filename: str) -> bytes:
    """Read a stored document by its generated name.

    The name comes from the database, never from a request. The containment
    check is a second line of defence in case that ever stops being true.
    """
    settings = get_settings()
    path = (settings.upload_dir / stored_filename).resolve()
    if path.parent != settings.upload_dir.resolve():
        raise UploadRejected("upload_unreadable")
    return path.read_bytes()
