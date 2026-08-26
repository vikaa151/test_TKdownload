"""日志页：展示 app.txt 内容，并支持导出运行日志。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit, QHBoxLayout,
    QFileDialog, QMessageBox,
)

from src.logger import copy_logs


class LogTab(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent)
        self.mw = mw
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QPushButton("刷新", clicked=self.load))
        row.addWidget(QPushButton("导出运行日志", clicked=self.export_logs))
        row.addStretch()
        lay.addLayout(row)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        lay.addWidget(self.text, 1)
        self.load()

    def load(self):
        p = self.mw.cfg.log_dir() / "app.txt"
        if p.exists():
            try:
                self.text.setPlainText(p.read_text(encoding="utf-8", errors="ignore")[-20000:])
            except Exception as e:
                self.text.setPlainText(f"读取日志失败：{e}")
        else:
            self.text.setPlainText("（暂无日志）")

    def export_logs(self):
        d = QFileDialog.getExistingDirectory(self, "选择日志导出目录", "")
        if not d:
            return
        n = copy_logs(Path(d))
        QMessageBox.information(self, "完成", f"已导出 {n} 个日志文件到 {d}")
