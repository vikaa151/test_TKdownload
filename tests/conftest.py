"""pytest 公共夹具：使用临时目录作为应用根，避免污染真实环境。"""
import sys
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import AppConfig, app_base_dir
from src.database import init_db


@pytest.fixture
def tmp_app(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.app_base_dir", lambda: tmp_path)
    cfg = AppConfig()
    init_db(cfg)
    return cfg
