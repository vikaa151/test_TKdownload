"""账号卡片与账号列表。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QMenu,
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices

from src import tasks, database
from src.naming import build_account_folder_name
from src.constants import WORK_TYPE_IMAGE
from gui.mobile import ANDROID


class AccountCard(QWidget):
    """单个账号卡片：展示关键字段，点击/右键进入编辑。"""

    edit_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, account, work_summary: dict, cfg, parent=None):
        super().__init__(parent)
        self.account = account
        self.work_summary = work_summary
        self.cfg = cfg
        self.setMinimumHeight(96)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        # 左侧信息
        info = QVBoxLayout()
        title = QLabel(f"{account.nickname or '未命名'}  (@{account.douyin_id or '—'})")
        title.setStyleSheet("font-weight:bold;font-size:13px;")
        info.addWidget(title)
        sub = QLabel(
            f"UID: {account.uid or '—'}  |  作品数: {work_summary.get('count',0)}  "
            f"|  类型: {work_summary.get('types','—')}"
        )
        info.addWidget(sub)
        flags = []
        if account.remark:
            # 有备注：红色字体突出显示
            remark_lbl = QLabel(f"备注：{account.remark}")
            remark_lbl.setStyleSheet("color:#e53935;font-weight:bold;")
            info.addWidget(remark_lbl)
        else:
            info.addWidget(QLabel("—"))
        lay.addLayout(info, 1)
        # 右侧操作
        ops = QVBoxLayout()
        edit = QPushButton("编辑")
        edit.clicked.connect(lambda: self.edit_requested.emit(account.uid))
        ops.addWidget(edit)
        path_btn = QPushButton("文件路径")
        path_btn.clicked.connect(self._open_path)
        ops.addWidget(path_btn)
        lay.addLayout(ops)

    def _open_path(self):
        works = database.list_works(self.cfg, self.account.id)
        n = len(works)
        base = Path(self.cfg.download_dir)
        if n == 1 and works[0].work_type == WORK_TYPE_IMAGE:
            # 单个图集：直接指向已建好的图片文件夹
            target = Path(works[0].local_path)
        elif n >= 2:
            # 多作品：仅当已合并（文件夹已存在）才指向「作品数量共x个」
            folder = base / build_account_folder_name(
                self.account.nickname, self.account.douyin_id, "works", n)
            target = folder if folder.exists() else base
        else:
            # 单视频 / 无作品：默认下载路径根目录
            target = base
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("编辑全部字段", lambda: self.edit_requested.emit(self.account.uid))
        menu.addAction("删除账号", lambda: self.remove_requested.emit(self.account.uid))
        menu.addAction("导出该账号作品(Excel)", lambda: self.edit_requested.emit(self.account.uid))
        menu.exec(event.globalPos())


class AccountListWidget(QListWidget):
    """账号卡片列表容器。"""

    edit_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setSpacing(6)
        self.item_account = {}

    def add_account_card(self, account, work_summary: dict):
        item = QListWidgetItem(self)
        card = AccountCard(account, work_summary, self.cfg)
        card.edit_requested.connect(self.edit_requested.emit)
        card.remove_requested.connect(self.remove_requested.emit)
        item.setSizeHint(card.minimumSizeHint())
        self.addItem(item)
        self.setItemWidget(item, card)
        self.item_account[account.uid] = item

    def clear_cards(self):
        self.clear()
        self.item_account.clear()
