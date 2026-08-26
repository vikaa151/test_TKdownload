"""GUI 烟雾测试 + 签名器边界测试。

仅在已安装 PySide6 时运行；通过 offscreen 平台在无显示器环境构造界面组件，
验证：主窗口可装配、各弹窗可构造、缺失签名文件时签名器明确报错（不静默）。
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pathlib
import tempfile

import pytest

from PySide6.QtWidgets import QApplication


_APP = None


def _app():
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication(sys.argv)
    return _APP


def _tmp_cfg(monkeypatch):
    import src.config as cfgmod
    tmp = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(cfgmod, "app_base_dir", lambda: tmp)
    from src.config import AppConfig
    cfg = AppConfig()
    cfg.first_run = False
    cfg.set_download_dir(str(tmp / "dl"))
    return cfg


def test_main_window_construct(monkeypatch):
    from gui.main_window import MainWindow
    _app()
    cfg = _tmp_cfg(monkeypatch)
    w = MainWindow(cfg)
    assert w.tabs.count() == 4
    w.refresh_accounts()
    assert "账号" in w.statusBar().currentMessage()


def test_dialogs_construct(monkeypatch):
    from gui.dialogs import RemarkDialog, PathDialog, CookieDialog, AccountEditDialog
    from gui.account_card import AccountCard
    from src.models import Account
    _app()
    cfg = _tmp_cfg(monkeypatch)
    PathDialog(cfg)
    RemarkDialog()
    CookieDialog(cfg)
    acc = Account(nickname="测试号", douyin_id="test_dy", uid="u1")
    summary = {"count": 0, "types": "—", "time_range": "—",
               "last_download": "—", "detail": "（暂无）"}
    AccountEditDialog(acc, summary)
    card = AccountCard(acc, summary, cfg)
    assert card.account is acc


def test_signer_builtin_abogus(monkeypatch):
    """签名已内置（纯 Python a_bogus，依赖 gmssl），无外部文件依赖。"""
    import src.config as cfgmod
    from src.signer import create_signer, SignerError
    tmp = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(cfgmod, "app_base_dir", lambda: tmp)
    from src.config import AppConfig
    cfg = AppConfig()
    try:
        signer = create_signer(cfg)
    except SignerError as e:
        if "gmssl" in str(e):
            pytest.skip("gmssl 未安装，跳过内置签名器测试")
        raise
    sig = signer.sign({"aweme_id": "1", "aid": "6383"}, "Mozilla/5.0")
    assert isinstance(sig, str) and len(sig) > 0


def test_first_run_path_dialog_accepted(monkeypatch):
    """回归：首次运行弹窗点确定不应报 'PathDialog' object has no attribute 'Accepted'。"""
    import src.config as cfgmod
    from src.config import AppConfig
    from gui.dialogs import PathDialog
    from PySide6.QtWidgets import QDialog
    _app()
    tmp = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(cfgmod, "app_base_dir", lambda: tmp)
    cfg = AppConfig()
    cfg.first_run = True
    cfg.download_dir = ""
    def fake_exec(self):
        self.path_edit.setText(str(tmp / "downloads"))
        return QDialog.Accepted
    monkeypatch.setattr(PathDialog, "exec", fake_exec)
    from gui.main_window import MainWindow
    w = MainWindow(cfg)
    assert w.cfg.download_dir, "apply() 应设置下载目录"
    assert w.cfg.first_run is False
