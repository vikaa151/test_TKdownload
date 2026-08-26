"""下载页：链接解析 → 备注 → 下载，按账户作品保存规则落盘。"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QMessageBox, QDialog,
)
from PySide6.QtCore import QCoreApplication

from src import tasks, database
from src.douyin_client import extract_douyin_urls
from gui.dialogs import RemarkDialog
from gui.mobile import row_layout, ANDROID


class DownloadTab(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent)
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("粘贴抖音作品链接（每行一个，支持批量）："))
        self.links = QTextEdit()
        self.links.setPlaceholderText("可直接粘贴抖音「分享」复制出的整段文案，或 https://v.douyin.com/xxxx/ 、https://www.douyin.com/video/xxxx")
        self.links.setMaximumHeight(160 if ANDROID else 120)
        lay.addWidget(self.links)
        row = row_layout()
        self.btn = QPushButton("解析并下载")
        self.btn.clicked.connect(self.run)
        clear = QPushButton("清空")
        clear.clicked.connect(self._clear_all)
        row.addWidget(self.btn)
        row.addWidget(clear)
        row.addStretch()
        lay.addLayout(row)
        self.progress = QTextEdit()
        self.progress.setReadOnly(True)
        lay.addWidget(self.progress, 1)

    def _clear_all(self):
        self.links.clear()
        self.progress.clear()

    def _log(self, msg: str):
        self.progress.append(msg)
        QCoreApplication.processEvents()

    def run(self):
        client = self.mw.get_client()
        if client is None:
            return
        # 从每行文本中提取抖音链接（兼容「分享文案」整段粘贴）
        links: list[str] = []
        for line in self.links.toPlainText().splitlines():
            links.extend(extract_douyin_urls(line))
        if not links:
            QMessageBox.information(self, "提示", "未识别到有效的抖音链接，请检查粘贴内容。")
            return
        self.btn.setEnabled(False)
        # 每次运行重置进度框，仅展示当前批次进度
        self.progress.clear()

        # 1. 解析所有链接
        parsed_items: list[tuple[str, object]] = []
        for url in links:
            self._log(f"解析：{url}")
            QCoreApplication.processEvents()
            try:
                parsed = client.parse_work(url)
            except Exception as e:
                self._log(f"  解析失败：{e}")
                continue
            self._log(f"  解析成功：{parsed.work_type} | {parsed.account.nickname or parsed.account.douyin_id}")
            parsed_items.append((url, parsed))

        if not parsed_items:
            self._log("— 无可下载内容 —")
            self.btn.setEnabled(True)
            return

        # 2. 按账号分组（douyin_id 优先，否则 uid）
        accounts = {a.douyin_id or a.uid: a for a in database.list_accounts(self.mw.cfg)}
        groups: dict[str, list] = defaultdict(list)
        for url, parsed in parsed_items:
            key = parsed.account.douyin_id or parsed.account.uid or url
            groups[key].append((url, parsed))

        total = len(parsed_items)
        done = 0
        for key, items in groups.items():
            is_batch = len(items) >= 2  # 同时批量下载同一账号多个视频
            acc = accounts.get(key)
            hist = database.list_works(self.mw.cfg, acc.id) if acc else []
            for url, parsed in items:
                done += 1
                self._log(f"[{done}/{total}] {parsed.work_type} | {parsed.account.nickname or parsed.account.douyin_id}")
                ctx = (f"账号：{parsed.account.nickname or parsed.account.douyin_id}"
                       f"（@{parsed.account.douyin_id or '—'}）\n"
                       f"类型：{parsed.work_type}    发布时间：{parsed.publish_time}\n"
                       f"描述：{parsed.description[:120]}")
                dlg = RemarkDialog(self, context=ctx)
                if dlg.exec() != QDialog.Accepted:
                    self._log("  已取消（用户关闭备注框）")
                    continue
                remark = dlg.value()
                aweme_id = parsed.aweme_id
                # 同一作品（aweme_id）已下载过 -> 覆盖/增量/跳过
                exist_same = database.find_work_by_aweme(self.mw.cfg, aweme_id)
                if exist_same:
                    choice = self._ask_redownload(parsed)
                    if choice is None:
                        self._log("  已跳过（已存在同名作品）")
                        continue
                    res = tasks.save_and_download(
                        self.mw.cfg, client, parsed, remark=remark, force=True,
                        overwrite_path=str(Path(exist_same.local_path) / exist_same.file_name),
                        skip_existing=(choice == "incremental"),
                        progress=self._log,
                    )
                # 同账号已有其他作品、且非批量 -> 弹窗询问是否合并
                elif (not is_batch) and len(hist) >= 1:
                    choice = self._ask_merge()
                    if choice is None:
                        self._log("  已跳过（用户选择跳过）")
                        continue
                    res = tasks.save_and_download(
                        self.mw.cfg, client, parsed, remark=remark,
                        merge=(choice == "merge"), progress=self._log,
                    )
                # 批量同账号（直接建文件夹）或 首次作品（独立保存）
                else:
                    res = tasks.save_and_download(
                        self.mw.cfg, client, parsed, remark=remark,
                        merge=is_batch, progress=self._log,
                    )
                if res.get("skipped"):
                    self._log("  已跳过（已存在）")
                else:
                    self._log(f"  完成 -> {res.get('path')}")
        self._log("— 全部完成 —")
        self.mw.refresh_accounts()
        self.btn.setEnabled(True)

    def _ask_redownload(self, parsed=None) -> str | None:
        """同一作品重复下载：返回 'overwrite'（覆盖）/ 'incremental'（增量）/ None（跳过）。"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("已下载")
        if parsed is not None:
            detail = (f"账号：{parsed.account.nickname or parsed.account.douyin_id}"
                      f"（@{parsed.account.douyin_id or '—'}）\n"
                      f"类型：{parsed.work_type}    发布时间：{parsed.publish_time}\n"
                      f"描述：{parsed.description[:120]}")
            msg.setInformativeText(detail)
        msg.setText("下载目录中已存在同名作品文件，是否重新下载？")
        btn_overwrite = msg.addButton("覆盖重新下载", QMessageBox.AcceptRole)
        btn_incr = msg.addButton("增量保存", QMessageBox.AcceptRole)
        btn_skip = msg.addButton("跳过", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_overwrite)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked is btn_overwrite:
            return "overwrite"
        if clicked is btn_incr:
            return "incremental"
        return None

    def _ask_merge(self) -> str | None:
        """同账号已有其他作品：返回 'merge'（合并）/ 'no_merge'（不合并）/ None（跳过）。"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("已下载同账户作品")
        msg.setText("已下载过同账户作品，是否合并保存至同一文件夹？")
        btn_merge = msg.addButton("合并保存", QMessageBox.AcceptRole)
        btn_no = msg.addButton("不合并", QMessageBox.AcceptRole)
        btn_skip = msg.addButton("跳过", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_merge)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked is btn_merge:
            return "merge"
        if clicked is btn_no:
            return "no_merge"
        return None
