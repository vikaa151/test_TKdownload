"""配置全量导入/导出：含设置、Cookie、已添加账号与作品记录、日志。

打包为 zip：config.json（含 Cookie）+ data.db（账号/作品）+ logs/。
导入时先备份当前配置，再覆盖还原。
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

from . import config
from .config import AppConfig


def export_config(cfg: AppConfig, zip_path: str | Path) -> Path:
    zip_path = Path(zip_path)
    base = config.app_base_dir()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        # 配置（含 Cookie）
        if cfg.config_path().exists():
            z.write(cfg.config_path(), "config.json")
        # 数据库（账号 + 作品）
        if cfg.db_path().exists():
            z.write(cfg.db_path(), "data.db")
        # 日志
        log_dir = cfg.log_dir()
        if log_dir.exists():
            for f in log_dir.glob("*"):
                if f.is_file():
                    z.write(f, f"logs/{f.name}")
    return zip_path


def import_config(cfg: AppConfig, zip_path: str | Path) -> None:
    zip_path = Path(zip_path)
    base = config.app_base_dir()
    # 备份当前
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = base / f"backup_before_import_{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "data.db"):
        p = base / name
        if p.exists():
            shutil.copy(p, backup / name)
    log_dir = cfg.log_dir()
    if log_dir.exists():
        (backup / "logs").mkdir(exist_ok=True)
        for f in log_dir.glob("*"):
            if f.is_file():
                shutil.copy(f, backup / "logs" / f.name)
    # 覆盖还原
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    # 重新载入配置
    cfg.load()


def read_config_json_in_zip(zip_path: str | Path) -> dict:
    with zipfile.ZipFile(zip_path, "r") as z:
        if "config.json" in z.namelist():
            return json.loads(z.read("config.json").decode("utf-8"))
    return {}
