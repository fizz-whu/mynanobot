import os
from pathlib import Path
from typing import Optional

from nanobot.utils.helpers import ensure_dir


class ConfigPaths:
    def __init__(self, nanobot_home: Optional[str] = None, instance: Optional[str] = None):
        self._nanobot_home = nanobot_home or os.environ.get("NANOBOT_HOME")
        self._instance = instance or os.environ.get("NANOBOT_INSTANCE")

    @property
    def base_dir(self) -> Path:
        base = Path(self._nanobot_home) if self._nanobot_home else Path.home() / ".nanobot"
        if self._instance:
            base = base.parent / f"{base.name}_{self._instance}"
        return base

    @property
    def config_file(self) -> Path:
        return self.base_dir / "config.yaml"

    @property
    def workspace_dir(self) -> Path:
        custom_workspace = os.environ.get("NANOBOT_WORKSPACE")
        if custom_workspace:
            return Path(custom_workspace)
        return self.base_dir / "workspace"

    @property
    def sessions_dir(self) -> Path:
        return self.workspace_dir / "sessions"

    @property
    def runtime_dir(self) -> Path:
        return self.base_dir / "runtime"

    @property
    def media_dir(self) -> Path:
        return self.runtime_dir / "media"

    def ensure_directories(self) -> None:
        ensure_dir(self.base_dir)
        ensure_dir(self.workspace_dir)
        ensure_dir(self.sessions_dir)
        ensure_dir(self.runtime_dir)
        ensure_dir(self.media_dir)
