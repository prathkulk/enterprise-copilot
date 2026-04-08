from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
import shutil

from fastapi import UploadFile

from backend.app.core.config import get_settings

settings = get_settings()


@dataclass
class StoredFile:
    storage_path: str
    absolute_path: Path
    original_filename: str
    content_type: str
    uploaded_at: str


class LocalFileStorage:
    def __init__(self, root: Path | None = None):
        self.root = root or settings.resolved_storage_root
        self.root.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file: UploadFile, collection_id: int) -> StoredFile:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        safe_name = Path(file.filename or "upload.bin").name
        suffix = Path(safe_name).suffix.lower()
        target_dir = self.root / f"collection_{collection_id}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_name = f"{timestamp}_{uuid4().hex}{suffix}"
        target_path = target_dir / target_name

        file.file.seek(0)
        with target_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

        uploaded_at = datetime.now(UTC).isoformat()
        try:
            storage_path = str(target_path.relative_to(Path.cwd()))
        except ValueError:
            storage_path = str(target_path)
        return StoredFile(
            storage_path=storage_path,
            absolute_path=target_path,
            original_filename=safe_name,
            content_type=file.content_type or "application/octet-stream",
            uploaded_at=uploaded_at,
        )

    def delete_file(self, storage_path: str | None) -> None:
        if not storage_path:
            return

        target_path = self.resolve_path(storage_path)

        if target_path.exists():
            target_path.unlink()

    def resolve_path(self, storage_path: str) -> Path:
        target_path = Path(storage_path)
        if not target_path.is_absolute():
            target_path = Path.cwd() / target_path
        return target_path
