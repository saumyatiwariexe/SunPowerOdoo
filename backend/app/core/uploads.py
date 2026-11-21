from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from .errors import AppError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_FILENAME_PATTERN = r"^[0-9a-f]{32}\.(jpg|png|webp)$"


def _image_extension(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    return None


def _write_image(directory: Path, filename: str, data: bytes) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    output = path.open("xb")
    try:
        with output:
            output.write(data)
    except OSError:
        path.unlink(missing_ok=True)
        raise


async def save_image(upload: UploadFile, directory: Path) -> str:
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise AppError("UPLOAD_TOO_LARGE", "Images must be 5 MiB or smaller.", 413)
    extension = _image_extension(data)
    if extension is None:
        raise AppError("INVALID_IMAGE", "Upload a JPEG, PNG, or WebP image.", 400)
    filename = f"{uuid4().hex}.{extension}"
    await run_in_threadpool(_write_image, directory, filename, data)
    return filename
