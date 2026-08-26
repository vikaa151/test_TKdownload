"""SQLite 数据层：账号表(accounts) 与 作品表(works)。

使用标准库 sqlite3（同步，GUI 线程内调用简单、可单测）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .config import AppConfig
from .models import Account, Work


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(cfg: AppConfig) -> None:
    conn = _connect(cfg.db_path())
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL DEFAULT '',
                douyin_id TEXT NOT NULL DEFAULT '',
                uid TEXT NOT NULL DEFAULT '',
                sec_uid TEXT NOT NULL DEFAULT '',
                share_url TEXT NOT NULL DEFAULT '',
                homepage_url TEXT NOT NULL DEFAULT '',
                monitor INTEGER NOT NULL DEFAULT 0,
                auto_download INTEGER NOT NULL DEFAULT 0,
                download_dir TEXT NOT NULL DEFAULT '',
                remark TEXT NOT NULL DEFAULT '',
                cookie_slot INTEGER NOT NULL DEFAULT 0,
                last_update TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                aweme_id TEXT NOT NULL,
                work_type TEXT NOT NULL DEFAULT '',
                publish_time TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                download_time TEXT NOT NULL DEFAULT '',
                remark TEXT NOT NULL DEFAULT '',
                local_path TEXT NOT NULL DEFAULT '',
                file_name TEXT NOT NULL DEFAULT '',
                nickname TEXT NOT NULL DEFAULT '',
                douyin_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT '',
                UNIQUE(account_id, aweme_id)
            );
            CREATE INDEX IF NOT EXISTS idx_works_aweme ON works(aweme_id);
            CREATE INDEX IF NOT EXISTS idx_works_account ON works(account_id);
            """
        )
        conn.commit()
        # 兼容旧库：补齐缺失列
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(accounts)").fetchall()}
        if "sec_uid" not in cols:
            conn.execute("ALTER TABLE accounts ADD COLUMN sec_uid TEXT NOT NULL DEFAULT ''")
            conn.commit()
    finally:
        conn.close()


# ---------------- 账号 ----------------
def add_account(cfg: AppConfig, acc: Account) -> int:
    conn = _connect(cfg.db_path())
    try:
        cur = conn.execute(
            """INSERT INTO accounts
               (nickname,douyin_id,uid,sec_uid,share_url,homepage_url,monitor,auto_download,
                download_dir,remark,cookie_slot,last_update,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (acc.nickname, acc.douyin_id, acc.uid, acc.sec_uid, acc.share_url,
             acc.homepage_url, int(acc.monitor), int(acc.auto_download), acc.download_dir,
             acc.remark, acc.cookie_slot, acc.last_update, acc.created_at, acc.updated_at),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_account(cfg: AppConfig, account_id: int) -> Optional[Account]:
    conn = _connect(cfg.db_path())
    try:
        row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        return Account.from_dict(dict(row)) if row else None
    finally:
        conn.close()


def list_accounts(cfg: AppConfig) -> list[Account]:
    conn = _connect(cfg.db_path())
    try:
        rows = conn.execute("SELECT * FROM accounts ORDER BY id DESC").fetchall()
        return [Account.from_dict(dict(r)) for r in rows]
    finally:
        conn.close()


def update_account(cfg: AppConfig, acc: Account) -> None:
    conn = _connect(cfg.db_path())
    try:
        conn.execute(
            """UPDATE accounts SET
               nickname=?,douyin_id=?,uid=?,sec_uid=?,share_url=?,homepage_url=?,monitor=?,
               auto_download=?,download_dir=?,remark=?,cookie_slot=?,last_update=?,updated_at=?
               WHERE id=?""",
            (acc.nickname, acc.douyin_id, acc.uid, acc.sec_uid, acc.share_url,
             acc.homepage_url, int(acc.monitor), int(acc.auto_download), acc.download_dir,
             acc.remark, acc.cookie_slot, acc.last_update, acc.updated_at, acc.id),
        )
        conn.commit()
    finally:
        conn.close()


def update_work(cfg: AppConfig, w: Work) -> None:
    conn = _connect(cfg.db_path())
    try:
        conn.execute(
            """UPDATE works SET
               account_id=?, aweme_id=?, work_type=?, publish_time=?, description=?,
               url=?, download_time=?, remark=?, local_path=?, file_name=?,
               nickname=?, douyin_id=?, created_at=?
               WHERE id=?""",
            (w.account_id, w.aweme_id, w.work_type, w.publish_time, w.description,
             w.url, w.download_time, w.remark, w.local_path, w.file_name,
             w.nickname, w.douyin_id, w.created_at, w.id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_account(cfg: AppConfig, account_id: int, delete_files: bool = False) -> None:
    conn = _connect(cfg.db_path())
    try:
        conn.execute("DELETE FROM works WHERE account_id=?", (account_id,))
        conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------- 作品 ----------------
def add_work(cfg: AppConfig, w: Work) -> int:
    conn = _connect(cfg.db_path())
    try:
        conn.execute(
            """INSERT INTO works
               (account_id,aweme_id,work_type,publish_time,description,url,download_time,
                remark,local_path,file_name,nickname,douyin_id,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(account_id,aweme_id) DO UPDATE SET
                 work_type=excluded.work_type, publish_time=excluded.publish_time,
                 description=excluded.description, url=excluded.url,
                 download_time=excluded.download_time, remark=excluded.remark,
                 local_path=excluded.local_path, file_name=excluded.file_name,
                 nickname=excluded.nickname, douyin_id=excluded.douyin_id,
                 created_at=excluded.created_at""",
            (w.account_id, w.aweme_id, w.work_type, w.publish_time, w.description, w.url,
             w.download_time, w.remark, w.local_path, w.file_name, w.nickname, w.douyin_id,
             w.created_at),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM works WHERE account_id=? AND aweme_id=?",
            (w.account_id, w.aweme_id),
        ).fetchone()
        return int(row["id"]) if row else 0
    finally:
        conn.close()


def find_work_by_aweme(cfg: AppConfig, aweme_id: str) -> Optional[Work]:
    conn = _connect(cfg.db_path())
    try:
        row = conn.execute("SELECT * FROM works WHERE aweme_id=?", (aweme_id,)).fetchone()
        return Work.from_dict(dict(row)) if row else None
    finally:
        conn.close()


def list_works(cfg: AppConfig, account_id: Optional[int] = None) -> list[Work]:
    conn = _connect(cfg.db_path())
    try:
        if account_id is None:
            rows = conn.execute("SELECT * FROM works ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM works WHERE account_id=? ORDER BY id DESC", (account_id,)
            ).fetchall()
        return [Work.from_dict(dict(r)) for r in rows]
    finally:
        conn.close()


def delete_work(cfg: AppConfig, work_id: int, delete_file: bool = False) -> None:
    conn = _connect(cfg.db_path())
    try:
        conn.execute("DELETE FROM works WHERE id=?", (work_id,))
        conn.commit()
    finally:
        conn.close()
