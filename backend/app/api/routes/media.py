import mimetypes
import re
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import require_roles, tenant_context
from app.models.models import Membership, RoleName, Tenant
from app.schemas.media import MediaAssetRead


router = APIRouter(tags=["media"])

MEDIA_SUFFIXES = {
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".webp": "image",
    ".mp4": "video",
    ".webm": "video",
    ".pdf": "document",
    ".doc": "document",
    ".docx": "document",
    ".ppt": "document",
    ".pptx": "document",
    ".xls": "document",
    ".xlsx": "document",
    ".txt": "document",
}

UPLOAD_SUFFIXES = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp"},
    "video": {".mp4", ".webm", ".mov", ".m4v"},
    "document": {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt"},
}

UPLOAD_MIME_TYPES = {
    "image": {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/gif",
        "image/webp",
    },
    "video": {
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/x-m4v",
    },
    "document": {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
    },
}


def _tenant_media_dir(code: str) -> str:
    sanitized = re.sub(r"[^a-z0-9-]+", "-", code.lower()).strip("-")
    return sanitized or "tenant"


def get_media_root(tenant: Tenant) -> tuple[Path, str]:
    tenant_dir = _tenant_media_dir(tenant.code)
    root = Path(__file__).resolve().parents[2] / "static" / "media" / tenant_dir
    root.mkdir(parents=True, exist_ok=True)
    return root, f"/media/{tenant_dir}"


def _asset_payload(file: Path, kind: str, public_prefix: str) -> MediaAssetRead:
    guessed_mime, _ = mimetypes.guess_type(file.name)
    fallback_mime = {
        "image": "image/*",
        "video": "video/*",
        "document": "application/octet-stream",
    }.get(kind, "application/octet-stream")
    return MediaAssetRead(
        path=f"{public_prefix}/{file.name}",
        label=file.stem.replace("-", " ").replace("_", " ").title(),
        kind=kind,
        size_bytes=file.stat().st_size,
        filename=file.name,
        mime_type=guessed_mime or fallback_mime,
    )


def _safe_filename(name: str, target_kind: str) -> str:
    source_name = Path(name or "").name
    suffix = Path(source_name).suffix.lower()
    if suffix not in UPLOAD_SUFFIXES[target_kind]:
        allowed = ", ".join(sorted(UPLOAD_SUFFIXES[target_kind]))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unsupported {target_kind} format. Allowed: {allowed}")
    stem = Path(source_name).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or target_kind
    output_suffix = ".mp4" if target_kind == "video" else suffix
    return f"{stem}-{uuid4().hex[:12]}{output_suffix}"


def _validate_upload_content_type(file: UploadFile, target_kind: str) -> None:
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if not content_type:
        return
    if content_type not in UPLOAD_MIME_TYPES[target_kind]:
        allowed = ", ".join(sorted(UPLOAD_MIME_TYPES[target_kind]))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported {target_kind} content type. Allowed: {allowed}",
        )


def _store_image(payload: bytes, destination: Path) -> None:
    destination.write_bytes(payload)


def _store_document(payload: bytes, destination: Path) -> None:
    destination.write_bytes(payload)


def _resolve_ffmpeg_binary() -> str:
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Video processing dependency is not installed on the server",
        ) from exc
    return imageio_ffmpeg.get_ffmpeg_exe()


def _transcode_video(source_file: Path, destination: Path) -> None:
    command = [
        _resolve_ffmpeg_binary(),
        "-y",
        "-i",
        str(source_file),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(destination),
    ]
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Video processing is not configured on the server",
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip().splitlines()
        error_line = stderr[-1] if stderr else "Unsupported or unreadable video file"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Video upload failed: {error_line}",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Video processing took too long. Try a shorter file or a lower resolution.",
        ) from exc


def _store_video(payload: bytes, original_name: str, destination: Path) -> None:
    suffix = Path(original_name).suffix.lower() or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(payload)
        temp_path = Path(temp_file.name)
    try:
        _transcode_video(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)


@router.get("/media/library", response_model=list[MediaAssetRead])
def list_media_library(
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
) -> list[MediaAssetRead]:
    media_root, public_prefix = get_media_root(tenant)
    assets: list[MediaAssetRead] = []
    for file in sorted(media_root.iterdir(), key=lambda item: item.name):
        if not file.is_file():
            continue
        kind = MEDIA_SUFFIXES.get(file.suffix.lower())
        if not kind:
            continue
        assets.append(_asset_payload(file, kind, public_prefix))
    return assets


@router.post("/media/upload", response_model=MediaAssetRead)
async def upload_media(
    target_kind: str = Form(...),
    file: UploadFile = File(...),
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
) -> MediaAssetRead:
    if target_kind not in UPLOAD_SUFFIXES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported media target")
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File name is required")
    _validate_upload_content_type(file, target_kind)
    media_root, public_prefix = get_media_root(tenant)
    filename = _safe_filename(file.filename, target_kind)
    destination = media_root / filename
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded file is empty")
    if target_kind == "image":
        _store_image(payload, destination)
    elif target_kind == "video":
        _store_video(payload, file.filename, destination)
    else:
        _store_document(payload, destination)
    return _asset_payload(destination, target_kind, public_prefix)
