"""设置页：下载路径、Cookie、并发、配置全量导入导出。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QSpinBox, QGroupBox, QCheckBox, QDialog,
)
from src import config_io
from src.config import AppConfig
from gui.dialogs import CookieDialog
from gui.mobile import row_layout


class SettingsTab(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent)
        self.mw = mw
        lay = QVBoxLayout(self)

        # 下载路径
        g1 = QGroupBox("下载文件存储路径")
        v1 = QVBoxLayout(g1)
        row = row_layout()
        self.path_edit = QLineEdit(self.mw.cfg.download_dir)
        row.addWidget(self.path_edit, 1)
        browse = QPushButton("浏览")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        v1.addLayout(row)
        self.default_chk = QCheckBox("保存为默认下载路径")
        self.default_chk.setChecked(self.mw.cfg.save_as_default)
        v1.addWidget(self.default_chk)
        apply = QPushButton("应用路径")
        apply.clicked.connect(self._apply_path)
        v1.addWidget(apply)
        lay.addWidget(g1)

        # 运行设置（仅 Cookie 配置 + 并发下载）
        g2 = QGroupBox("运行设置")
        v2 = QVBoxLayout(g2)
        cookie = QPushButton("Cookie 配置")
        cookie.clicked.connect(self._cookies)
        v2.addWidget(cookie)
        ccol = row_layout()
        ccol.addWidget(QLabel("并发下载数:"))
        self.conc = QSpinBox()
        self.conc.setRange(1, 10)
        self.conc.setValue(self.mw.cfg.concurrency)
        ccol.addWidget(self.conc)
        ccol.addStretch()
        v2.addLayout(ccol)
        lay.addWidget(g2)

        # 配置与日志
        g3 = QGroupBox("配置全量导入导出")
        v3 = QVBoxLayout(g3)
        h3 = row_layout()
        h3.addWidget(QPushButton("导出全量配置(zip)", clicked=self._export_cfg))
        h3.addWidget(QPushButton("导入全量配置(zip)", clicked=self._import_cfg))
        v3.addLayout(h3)
        lay.addWidget(g3)
        lay.addStretch()

    def _load_values(self):
        """从配置回填控件（首启选路径、导入配置后自动刷新）。"""
        self.path_edit.setText(self.mw.cfg.download_dir)
        self.conc.setValue(self.mw.cfg.concurrency)
        self.default_chk.setChecked(self.mw.cfg.save_as_default)

    def showEvent(self, event):
        self._load_values()
        super().showEvent(event)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择下载目录", self.path_edit.text())
        if d:
            self.path_edit.setText(d)

    def _apply_path(self):
        from PySide6.QtWidgets import QMessageBox
        self.mw.cfg.set_download_dir(self.path_edit.text(), as_default=self.default_chk.isChecked())
        self.mw.cfg.save()
        QMessageBox.information(self, "已保存", "下载路径已更新。")

    def _cookies(self):
        from PySide6.QtWidgets import QMessageBox
        dlg = CookieDialog(self.mw.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            self.mw.cfg.concurrency = self.conc.value()
            self.mw.cfg.save()
            self.mw.reset_client()

    def _export_cfg(self):
        from PySide6.QtWidgets import QMessageBox
        path, _ = QFileDialog.getSaveFileName(self, "导出配置", "douyin_config.zip", "ZIP (*.zip)")
        if not path:
            return
        config_io.export_config(self.mw.cfg, path)
        QMessageBox.information(self, "完成", f"配置已导出：{path}")

    def _import_cfg(self):
        from PySide6.QtWidgets import QMessageBox
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "ZIP (*.zip)")
        if not path:
            return
        ans = QMessageBox.question(self, "导入确认",
                                  "导入将覆盖当前配置（已自动备份）。是否继续？",
                                  QMessageBox.Yes | QMessageBox.No)
        if ans != QMessageBox.Yes:
            return
        config_io.import_config(self.mw.cfg, path)
        self.mw.reset_client()
        self.mw.refresh_accounts()
        QMessageBox.information(self, "完成", "配置已导入（当前配置已备份）。")
