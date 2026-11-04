from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Protocol

from ..config import Settings


class StorageProvider(Protocol):
    name: str

    def save(self, tenant_id: str, filename: str, content: bytes) -> str: ...


def safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]", "_", Path(filename).name)
    return cleaned[:180] or "document.bin"


class LocalStorageProvider:
    name = "local"

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, tenant_id: str, filename: str, content: bytes) -> str:
        tenant_dir = (self.root / safe_filename(tenant_id)).resolve()
        if self.root not in tenant_dir.parents and tenant_dir != self.root:
            raise ValueError("Invalid tenant storage path")
        tenant_dir.mkdir(parents=True, exist_ok=True)
        key = f"{uuid.uuid4()}-{safe_filename(filename)}"
        target = (tenant_dir / key).resolve()
        if tenant_dir not in target.parents:
            raise ValueError("Invalid document storage path")
        target.write_bytes(content)
        return str(target.relative_to(self.root)).replace("\\", "/")


class ObsStorageProvider:
    name = "huawei-obs"

    def __init__(self, settings: Settings):
        try:
            from obs import ObsClient
        except ImportError as exc:  # pragma: no cover - optional provider
            raise RuntimeError("Install esdk-obs-python to use Huawei OBS") from exc
        self.bucket = settings.huawei_obs_bucket or ""
        self.client = ObsClient(
            access_key_id=settings.huawei_obs_access_key,
            secret_access_key=settings.huawei_obs_secret_key,
            server=settings.huawei_obs_endpoint,
        )

    def save(self, tenant_id: str, filename: str, content: bytes) -> str:
        key = f"tenants/{safe_filename(tenant_id)}/{uuid.uuid4()}-{safe_filename(filename)}"
        response = self.client.putContent(self.bucket, key, content)
        if response.status >= 300:
            raise RuntimeError(f"OBS upload failed with status {response.status}")
        return key


def get_storage_provider(settings: Settings) -> StorageProvider:
    obs_ready = all(
        [
            settings.huawei_obs_endpoint,
            settings.huawei_obs_access_key,
            settings.huawei_obs_secret_key,
            settings.huawei_obs_bucket,
        ]
    )
    if obs_ready:
        try:
            return ObsStorageProvider(settings)
        except RuntimeError:
            pass
    return LocalStorageProvider(settings.local_storage_path)
