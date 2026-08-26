"""主窗口：装配各标签页、客户端与配置、首次运行弹窗。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QDialog,
)
from PySide6.QtCore import QCoreApplication

from src.config import AppConfig, _is_android
from src import database
from src.douyin_client import DouyinClient
from src.signer import create_signer, SignerError
from src.logger import setup_logger

from gui.download_tab import DownloadTab
from gui.account_tab import AccountTab
from gui.settings_tab import SettingsTab
from gui.log_tab import LogTab
from gui.dialogs import PathDialog


class MainWindow(QMainWindow):
    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.cfg = cfg
        self._client = None
        setup_logger(cfg)
        database.init_db(cfg)
        self.setWindowTitle("抖音作品批量下载器")
        self.resize(900, 640)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.download_tab = DownloadTab(self)
        self.account_tab = AccountTab(self)
        self.settings_tab = SettingsTab(self)
        self.log_tab = LogTab(self)
        self.tabs.addTab(self.download_tab, "下载")
        self.tabs.addTab(self.account_tab, "账号")
        self.tabs.addTab(self.settings_tab, "设置")
        self.tabs.addTab(self.log_tab, "日志")
        self.refresh_accounts()
        QCoreApplication.processEvents()
        self._maybe_first_run()

    def _maybe_first_run(self):
        if self.cfg.first_run or not self.cfg.download_dir:
            # 安卓：默认写入应用私有目录，免去存储权限与路径选择弹窗
            if _is_android():
                rec = self.cfg.recommended_download_dir()
                if rec:
                    self.cfg.set_download_dir(rec, as_default=True)
                    self.cfg.first_run = False
                    self.cfg.save()
                    self.statusBar().showMessage(f"下载目录：{self.cfg.download_dir}")
                    self.settings_tab._load_values()
                    return
            dlg = PathDialog(self.cfg, self)
            if dlg.exec() == QDialog.Accepted:
                dlg.apply()
                self.statusBar().showMessage(f"下载目录：{self.cfg.download_dir}")
                self.settings_tab._load_values()

    def get_client(self) -> DouyinClient | None:
        if self._client is not None:
            return self._client
        try:
            signer = create_signer(self.cfg)
        except SignerError as e:
            QMessageBox.warning(self, "签名未就绪", str(e))
            return None
        self._client = DouyinClient(self.cfg, signer)
        return self._client

    def reset_client(self):
        self._client = None

    def refresh_accounts(self):
        self.account_tab.refresh()
        n_acc = len(database.list_accounts(self.cfg))
        n_work = len(database.list_works(self.cfg))
        self.statusBar().showMessage(f"账号 {n_acc} 个 | 已下载作品 {n_work} 个")
