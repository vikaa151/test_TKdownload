"""运行日志：滚动写入 logs/app.txt（纯文本，便于作为附件上传分析）。"""
from __future__ import annotations

import logging
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER = None


def setup_logger(cfg) -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER
    log_dir = cfg.log_dir()
    log_file = log_dir / "app.txt"
    logger = logging.getLogger("douyin_dl")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3,
                                 encoding="utf-8")
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(sh)
    _LOGGER = logger
    return logger


def get_logger() -> logging.Logger:
    return _LOGGER or logging.getLogger("douyin_dl")


def export_logs(cfg, dest_zip: str | Path) -> Path:
    """将 logs 目录打包导出供分析。"""
    import zipfile
    dest = Path(dest_zip)
    log_dir = cfg.log_dir()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in log_dir.glob("*"):
            if f.is_file():
                z.write(f, f"logs/{f.name}")
    return dest


def copy_logs(dest_dir: str | Path) -> int:
    """将日志文件复制到目标目录（设置页「导出运行日志」用）。"""
    from .config import app_base_dir
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    log_dir = app_base_dir() / "logs"
    n = 0
    if log_dir.exists():
        for f in log_dir.glob("*"):
            if f.is_file():
                shutil.copy(f, dest / f.name)
                n += 1
    return n
