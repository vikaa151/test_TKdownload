"""通用弹窗组件。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit, QPushButton,
    QCheckBox, QFileDialog, QMessageBox,
)

from src.config import AppConfig
from src import tasks
from gui.mobile import row_layout, ANDROID


class RemarkDialog(QDialog):
    """下载前填入备注。context 用于明确「当前正在为哪一个作品备注」。"""

    def __init__(self, parent=None, default="", context: str = ""):
        super().__init__(parent)
        self.setWindowTitle("填入备注")
        self.resize(460, 230)
        lay = QVBoxLayout(self)
        if context:
            info = QLabel(context)
            info.setWordWrap(True)
            info.setStyleSheet(
                "color:#222;background:#f3f5f8;padding:8px;border-radius:6px;"
                "border:1px solid #d7dde6;")
            lay.addWidget(info)
        lay.addWidget(QLabel("为该作品填写备注（可留空）："))
        self.edit = QTextEdit(default)
        self.edit.setMaximumHeight(120 if ANDROID else 80)
        lay.addWidget(self.edit)
        btns = row_layout()
        ok = QPushButton("确定并下载")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)

    def value(self) -> str:
        return self.edit.toPlainText().strip()


class PathDialog(QDialog):
    """首次运行选择下载路径。"""

    def __init__(self, cfg: AppConfig, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("选择下载文件存储路径")
        self.resize(520, 160)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("请选择作品下载保存目录："))
        row = QHBoxLayout()
        self.path_edit = QLineEdit(cfg.download_dir)
        row.addWidget(self.path_edit, 1)
        browse = QPushButton("浏览...")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        lay.addLayout(row)
        self.default_chk = QCheckBox("保存为默认下载路径")
        self.default_chk.setChecked(True)
        lay.addWidget(self.default_chk)
        btns = row_layout()
        ok = QPushButton("确定")
        ok.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(ok)
        lay.addLayout(btns)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录", self.path_edit.text())
        if d:
            self.path_edit.setText(d)

    def apply(self):
        self.cfg.set_download_dir(self.path_edit.text(),
                                  as_default=self.default_chk.isChecked())
        self.cfg.first_run = False
        self.cfg.save()


class CookieDialog(QDialog):
    """Cookie 配置窗口：填入一条抖音网页版 Cookie 即可。"""

    def __init__(self, cfg: AppConfig, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Cookie 配置")
        self.resize(620, 360)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "粘贴抖音网页版登录后的 Cookie（浏览器开发者工具 → Network → "
            "任意请求 → Request Headers 中的 Cookie 整段）："))
        self.edit = QTextEdit()
        self.edit.setPlaceholderText(
            "例如：sessionid=...; passport_csrf_token=...; ttwid=...; odin_tt=...")
        existing = self.cfg.cookies[0].value if self.cfg.cookies else ""
        self.edit.setPlainText(existing)
        lay.addWidget(self.edit, 1)
        btns = row_layout()
        save = QPushButton("保存")
        save.clicked.connect(self._save)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)
        lay.addLayout(btns)

    def _save(self):
        from src.config import CookieEntry
        val = self.edit.toPlainText().strip()
        if not val:
            QMessageBox.warning(self, "提示", "Cookie 不能为空。")
            return
        self.cfg.cookies = [CookieEntry(name="默认", value=val)]
        self.cfg.save()
        QMessageBox.information(self, "已保存", "Cookie 已保存。")
        self.accept()


class AccountEditDialog(QDialog):
    """账号全字段编辑。"""

    FIELDS = [
        ("nickname", "昵称"), ("douyin_id", "抖音号"), ("uid", "UID"),
        ("share_url", "主页/分享链接"), ("download_dir", "下载目录"),
        ("remark", "备注"),
    ]

    def __init__(self, account, work_summary: dict, parent=None):
        super().__init__(parent)
        self.account = account
        self.setWindowTitle(f"编辑账号：{account.nickname or account.douyin_id}")
        self.resize(560, 480)
        lay = QVBoxLayout(self)
        self.edits = {}
        for key, label in self.FIELDS:
            h = QHBoxLayout()
            h.addWidget(QLabel(label), 0)
            le = QLineEdit(str(getattr(account, key, "")))
            self.edits[key] = le
            h.addWidget(le, 1)
            lay.addLayout(h)
        # 已下载作品只读汇总
        lay.addWidget(QLabel("— 已下载作品汇总（只读）—"))
        info = (f"作品数：{work_summary.get('count',0)}  "
                f"类型：{work_summary.get('types','')}  "
                f"发布时间范围：{work_summary.get('time_range','')}  "
                f"最近下载：{work_summary.get('last_download','')}")
        lay.addWidget(QLabel(info))
        lay.addWidget(QLabel("详细文字描述 / 作品链接见下方（只读）："))
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlainText(work_summary.get("detail", ""))
        lay.addWidget(self.detail)
        btns = row_layout()
        ok = QPushButton("保存")
        ok.clicked.connect(self._save)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)

    def _save(self):
        for key, le in self.edits.items():
            setattr(self.account, key, le.text().strip())
        self.account.updated_at = ""
        self.accept()

        self.accept()
