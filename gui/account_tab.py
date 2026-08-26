"""账号页：卡片展示 + 全字段编辑 + 监控一键下载 + Excel 导入导出。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox, QDialog,
)
from PySide6.QtCore import QCoreApplication

from src import database, tasks
from src.excel_io import export_accounts_xlsx
from gui.mobile import row_layout
from src.models import Account
from gui.account_card import AccountListWidget
from gui.dialogs import AccountEditDialog
from src.signer import SignerError


class AccountTab(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent)
        self.mw = mw
        lay = QVBoxLayout(self)
        # 工具栏
        tb = row_layout()
        tb.addWidget(QPushButton("刷新", clicked=self.refresh))
        tb.addWidget(QPushButton("导出 Excel", clicked=self.export_excel))
        tb.addStretch()
        lay.addLayout(tb)
        self.list = AccountListWidget(self.mw.cfg)
        self.list.edit_requested.connect(self.edit_account)
        self.list.remove_requested.connect(self.remove_account)
        lay.addWidget(self.list, 1)

    def refresh(self):
        self.list.clear_cards()
        for acc in database.list_accounts(self.mw.cfg):
            self.list.add_account_card(acc, self._summary(acc))

    def _summary(self, acc: Account) -> dict:
        ws = database.list_works(self.mw.cfg, acc.id)
        types = sorted({w.work_type for w in ws})
        times = [w.publish_time for w in ws if w.publish_time]
        last_dl = sorted(w.download_time for w in ws if w.download_time)
        detail = "\n".join(
            f"[{w.work_type}] {w.publish_time} | {w.description[:60]}\n  {w.url}"
            for w in ws[:50]
        )
        return {
            "count": len(ws),
            "types": "/".join(types) if types else "—",
            "time_range": f"{times[0]} ~ {times[-1]}" if times else "—",
            "last_download": last_dl[-1] if last_dl else "—",
            "detail": detail or "（暂无已下载作品）",
        }

    def edit_account(self, uid: str):
        acc = self._find(uid)
        if not acc:
            return
        dlg = AccountEditDialog(acc, self._summary(acc), self)
        if dlg.exec() == QDialog.Accepted:
            database.update_account(self.mw.cfg, acc)
            self.mw.refresh_accounts()

    def remove_account(self, uid: str):
        acc = self._find(uid)
        if not acc:
            return
        ans = QMessageBox.question(
            self, "删除确认", f"删除账号「{acc.nickname or acc.douyin_id}」及其全部作品记录？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            database.delete_account(self.mw.cfg, acc.id)
            self.mw.refresh_accounts()

    def _find(self, uid: str) -> Account | None:
        for acc in database.list_accounts(self.mw.cfg):
            if acc.uid == uid or acc.sec_uid == uid:
                return acc
        return None

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出账号", "accounts.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        export_accounts_xlsx(path, database.list_accounts(self.mw.cfg))
        QMessageBox.information(self, "完成", f"账号已导出：{path}")
