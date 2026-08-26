"""应用配置：下载路径、Cookie、全局设置。

关键：配置目录基于「可执行文件/脚本所在目录」解析，
避免历史上回退到 system32 导致 PermissionError 的问题（见前期故障记录）。
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


def _is_android() -> bool:
    """是否运行在安卓（p4a 会注入 ANDROID_ARGUMENT 等环境变量）。"""
    return bool(os.environ.get("ANDROID_ARGUMENT") or os.environ.get("ANDROID_BOOTLOGO"))


def app_base_dir() -> Path:
    """返回程序根目录：打包后为 exe 所在目录，源码态为 src 的上一级。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


@dataclass
class CookieEntry:
    name: str = "默认"
    value: str = ""
    note: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(name=d.get("name", "默认"), value=d.get("value", ""), note=d.get("note", ""))


@dataclass
class AppConfig:
    download_dir: str = ""           # 全局下载根目录
    save_as_default: bool = True     # 是否记忆为默认
    cookies: list = field(default_factory=list)  # List[CookieEntry]
    concurrency: int = 3             # 下载并发数
    autostart: bool = False          # 开机自启
    theme: str = "morandi"           # 主题
    proxy: str = ""                  # 代理地址
    first_run: bool = True           # 是否首次运行（用于弹窗选路径）
    # 上次导入/导出路径记忆
    last_import_dir: str = ""
    last_export_dir: str = ""

    def cookie_values(self) -> list[str]:
        return [c.value for c in self.cookies if c.value]

    # ---------- 持久化 ----------
    def config_path(self) -> Path:
        return app_base_dir() / "config.json"

    def db_path(self) -> Path:
        return app_base_dir() / "data.db"

    def log_dir(self) -> Path:
        d = app_base_dir() / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def load(self) -> "AppConfig":
        p = self.config_path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                self._apply(data)
            except Exception:
                # 损坏配置不影响启动，使用默认值
                pass
        return self

    def _apply(self, data: dict):
        self.download_dir = data.get("download_dir", "")
        self.save_as_default = data.get("save_as_default", True)
        self.concurrency = data.get("concurrency", 3)
        self.autostart = data.get("autostart", False)
        self.theme = data.get("theme", "morandi")
        self.proxy = data.get("proxy", "")
        self.first_run = data.get("first_run", False)
        self.last_import_dir = data.get("last_import_dir", "")
        self.last_export_dir = data.get("last_export_dir", "")
        self.cookies = [CookieEntry.from_dict(c) for c in data.get("cookies", [])]

    def save(self):
        p = self.config_path()
        p.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    def set_download_dir(self, path: str, as_default: bool = True):
        self.download_dir = path
        self.save_as_default = as_default
        if as_default:
            self.save()

    def recommended_download_dir(self) -> str:
        """按平台返回推荐下载根目录。

        安卓：写入应用私有外部存储
        （/sdcard/Android/data/<pkg>/files/Downloads），始终可写、无需存储权限，
        规避 Android 11+ 分区存储限制；用户可在文件管理器该目录下取回文件。
        桌面：返回空串（由首次运行弹窗让用户自选）。
        """
        if _is_android():
            try:
                from PySide6.QtCore import QStandardPaths
                loc = QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.AppDataLocation)
                if loc:
                    d = Path(loc) / "Downloads"
                    d.mkdir(parents=True, exist_ok=True)
                    return str(d)
            except Exception:
                pass
        return ""
