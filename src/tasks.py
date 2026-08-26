"""任务编排：把「解析 → 备注 → 落库账号/作品 → 下载原画 → 记录」串成可复用、可单测的流程。

GUI 只负责交互（弹备注框、去重询问），业务逻辑集中在此，便于离线测试。
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from . import database
from .config import AppConfig
from .douyin_client import DouyinClient, ParsedWork
from .logger import get_logger
from .models import Account, Work
from .naming import build_filename, build_account_folder_name
from .constants import WORK_TYPE_IMAGE, WORK_TYPE_VIDEO


def resolve_account_dir(cfg: AppConfig, acc: Account) -> str:
    """账号下载目录：优先账号自定义，否则全局下载根目录。"""
    if acc.download_dir and Path(acc.download_dir).is_absolute():
        d = Path(acc.download_dir)
    elif acc.download_dir:
        d = Path(cfg.download_dir) / acc.download_dir
    else:
        d = Path(cfg.download_dir) / f"{acc.nickname or '未命名'}_{acc.douyin_id or acc.uid or 'na'}"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def derive_account_homepage(acc: Account) -> str:
    """根据账号唯一标识推导主页链接（用于「主页/分享链接」自动匹配补全）。

    sec_uid 最可靠（抖音网页用户主页固定为 /user/{sec_uid}）；
    缺失时依次退化为 douyin_id / uid，保证尽量能打开对应主页。
    """
    if getattr(acc, "sec_uid", ""):
        return f"https://www.douyin.com/user/{acc.sec_uid}"
    if getattr(acc, "douyin_id", ""):
        return f"https://www.douyin.com/user/{acc.douyin_id}"
    if getattr(acc, "uid", ""):
        return f"https://www.douyin.com/user/{acc.uid}"
    return ""


def upsert_account(cfg: AppConfig, parsed: ParsedWork) -> Account:
    """按抖音号查找已有账号，否则新建（自动解析账户）。"""
    a = parsed.account
    existing = None
    for cand in database.list_accounts(cfg):
        if (a.douyin_id and cand.douyin_id == a.douyin_id) or \
           (a.uid and cand.uid == a.uid):
            existing = cand
            break
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if existing:
        # 补全可能缺失的字段
        changed = False
        for fld, val in (("nickname", a.nickname), ("share_url", a.share_url),
                         ("homepage_url", a.homepage_url), ("uid", a.uid),
                         ("douyin_id", a.douyin_id), ("sec_uid", a.sec_uid)):
            if not getattr(existing, fld) and val:
                setattr(existing, fld, val)
                changed = True
        # 仍缺失主页/分享链接时，按 sec_uid/douyin_id/uid 推导补全（自动匹配）
        if not existing.share_url or not existing.homepage_url:
            hp = derive_account_homepage(existing)
            if hp:
                if not existing.share_url:
                    existing.share_url = hp
                if not existing.homepage_url:
                    existing.homepage_url = hp
                changed = True
        existing.last_update = now
        if changed:
            database.update_account(cfg, existing)
        return existing
    acc = Account(
        nickname=a.nickname, douyin_id=a.douyin_id, uid=a.uid, sec_uid=a.sec_uid,
        share_url=a.share_url, homepage_url=a.homepage_url,
        last_update=now, created_at=now, updated_at=now,
    )
    # 新建账号同样补全主页/分享链接（自动匹配）
    if not acc.share_url or not acc.homepage_url:
        hp = derive_account_homepage(acc)
        if hp:
            if not acc.share_url:
                acc.share_url = hp
            if not acc.homepage_url:
                acc.homepage_url = hp
    acc.id = database.add_account(cfg, acc)
    return acc


def _account_from_parsed(parsed: ParsedWork) -> Account:
    a = parsed.account
    return Account(
        nickname=a.nickname, douyin_id=a.douyin_id, uid=a.uid, sec_uid=a.sec_uid,
        share_url=a.share_url, homepage_url=a.homepage_url,
    )


def _identity_base(parsed: ParsedWork) -> str:
    """忽略备注的「作品身份」基础名：备注不同不影响同一作品判定。"""
    a = parsed.account
    return build_filename("", a.nickname, a.douyin_id, parsed.publish_time,
                          parsed.work_type, parsed.description)


def _work_dir_and_primary(cfg, parsed, base, acc_dir=None):
    """返回 (work_dir, primary_file)。

    多图集/合辑 -> 落到 work_dir = acc_dir/base 子文件夹；单视频 -> 直接落在 acc_dir。
    """
    if acc_dir is None:
        acc_dir = resolve_account_dir(cfg, _account_from_parsed(parsed))
    multi = len(parsed.media) > 1
    ext = parsed.media[0].ext if parsed.media else ""
    if multi:
        work_dir = Path(acc_dir) / base
        primary = work_dir / f"{base}_1{ext}"
    else:
        work_dir = Path(acc_dir)
        primary = work_dir / f"{base}{ext}"
    return str(work_dir), str(primary)


def save_and_download(
    cfg: AppConfig,
    client: DouyinClient,
    parsed: ParsedWork,
    remark: str = "",
    force: bool = False,
    cookie: str = "",
    progress: Optional[Callable[[str], None]] = None,
    overwrite_path: Optional[str] = None,
    skip_existing: bool = False,
    merge: bool = False,
) -> dict:
    """落库账号与作品、下载原画/原图、写记录。

    落盘规则（账户作品保存规则 1-5）：
    - 图集：独立建「昵称_抖音号_图片数量共x个」文件夹（x=图片数）。
    - 单视频：不建文件夹，直接放默认下载路径根目录。
    - merge=True（批量同账号多视频 / 跨时间合并保存）：下载后调用
      consolidate_account，把该账号所有作品归集到
      「昵称_抖音号_作品数量共x个」文件夹（x=作品总数）。

    overwrite_path：同一作品（aweme_id 已存在）重下时复用其原文件位置。
    skip_existing：仅下载磁盘上尚不存在的文件（增量保存，多用于图集）。
    """
    log = get_logger()
    aweme_id = parsed.aweme_id
    exist = database.find_work_by_aweme(cfg, aweme_id)
    if exist and not force:
        return {"skipped": True, "reason": "exists", "aweme_id": aweme_id}

    acc = upsert_account(cfg, parsed)
    base_dir = Path(cfg.download_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    # 自动补全账号下载目录（写入默认下载路径）
    if not acc.download_dir:
        acc.download_dir = str(base_dir)
        database.update_account(cfg, acc)

    is_image = parsed.work_type == WORK_TYPE_IMAGE
    pic_count = len(parsed.media) if is_image else 0

    # 本次落盘位置
    if overwrite_path:
        op = Path(overwrite_path)
        dest_dir = str(op.parent)
        base = op.stem
    else:
        base = build_filename(remark, acc.nickname, acc.douyin_id,
                              parsed.publish_time, parsed.work_type, parsed.description)
        if is_image:
            # 图集独立文件夹（命名规则3）
            dest_dir = str(base_dir / build_account_folder_name(
                acc.nickname, acc.douyin_id, "images", pic_count))
        else:
            # 单视频直接放根目录（命名规则4）；merge 时由 consolidate 归集
            dest_dir = str(base_dir)

    multi = len(parsed.media) > 1
    # 图集已在 dest_dir（图片文件夹）层，视频也在对应层；不再额外嵌套 base 子目录
    work_dir = str(Path(dest_dir))

    # 增量保存：仅下载尚不存在的文件
    media_to_dl = parsed.media
    if skip_existing and parsed.media:
        keep = []
        for item in parsed.media:
            suffix = f"_{item.index + 1}" if (multi and item.index >= 0) else ""
            p = Path(work_dir) / f"{base}{suffix}{item.ext}"
            if not p.exists():
                keep.append(item)
        media_to_dl = keep

    if progress:
        progress(f"下载：{base}")
    saved = client.download_media(media_to_dl, dest_dir, base, cookie=cookie) if media_to_dl \
        else []

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if exist:
        # 覆盖/增量：更新已有记录，避免唯一约束冲突
        exist.remark = remark
        exist.download_time = now
        exist.local_path = dest_dir
        exist.file_name = Path(saved[0]).name if saved else exist.file_name
        database.update_work(cfg, exist)
        log.info("重新下载 %s/%s -> %s", parsed.work_type, aweme_id, exist.file_name)
        return {"ok": True, "aweme_id": aweme_id, "path": saved[0] if saved else "",
                "account": acc.nickname, "overwritten": True}

    w = Work(
        account_id=acc.id, aweme_id=aweme_id, work_type=parsed.work_type,
        publish_time=parsed.publish_time, description=parsed.description,
        url=parsed.url, download_time=now, remark=remark,
        local_path=dest_dir,
        file_name=Path(saved[0]).name if saved else base,
        nickname=acc.nickname, douyin_id=acc.douyin_id,
        created_at=now,
    )
    database.add_work(cfg, w)
    log.info("已下载 %s/%s -> %s", parsed.work_type, aweme_id, w.file_name)

    # 合并归集（规则1/2）：同账号多作品 -> 作品数量共x个 文件夹
    if merge:
        consolidate_account(cfg, acc)

    return {"ok": True, "aweme_id": aweme_id, "path": saved[0] if saved else "",
            "account": acc.nickname, "merged": merge}


def dedupe_check(cfg: AppConfig, aweme_id: str) -> bool:
    """返回 True 表示已存在记录（需要询问是否重复下载）。"""
    return database.find_work_by_aweme(cfg, aweme_id) is not None


def monitor_download(cfg: AppConfig, client: DouyinClient, account: Account,
                     max_count: int = 20,
                     progress: Optional[Callable[[str], None]] = None) -> dict:
    """监控/一键下载：拉取账号作品，自动下载未记录的新作品。"""
    if not account.sec_uid:
        return {"ok": False, "reason": "no_sec_uid",
                "msg": f"账号 {account.nickname} 缺少 sec_uid，无法监控拉取"}
    works = client.get_user_works(account.sec_uid, max_count=max_count)
    new_count = 0
    for w in works:
        if database.find_work_by_aweme(cfg, w.aweme_id):
            continue
        res = save_and_download(cfg, client, w, force=False, progress=progress)
        if res.get("ok"):
            new_count += 1
    return {"ok": True, "total": len(works), "new": new_count}


def consolidate_account(cfg: AppConfig, acc: Account) -> Optional[str]:
    """把某账号所有已下载作品归集到「昵称_抖音号_作品数量共x个」文件夹。

    规则1/2：同账号多个作品合并保存。x = 该账号作品总数（含视频与图集）。
    单图集 / 单视频（不足 2 件）不归集，保持各自位置。
    返回最终文件夹路径；不足 2 件返回 None。
    """
    works = database.list_works(cfg, acc.id)
    total = len(works)
    if total < 2:
        return None
    base_dir = Path(cfg.download_dir)
    folder = base_dir / build_account_folder_name(
        acc.nickname, acc.douyin_id, "works", total)
    folder.mkdir(parents=True, exist_ok=True)
    old_dirs: set = set()
    for w in works:
        src_dir = Path(w.local_path)
        old_dirs.add(src_dir)
        if w.work_type == WORK_TYPE_IMAGE:
            # 图集：移动整个旧文件夹内容到统一文件夹
            if src_dir.is_dir():
                for f in src_dir.iterdir():
                    dst = folder / f.name
                    if f != dst and not dst.exists():
                        shutil.move(str(f), str(dst))
        else:
            src = src_dir / w.file_name
            dst = folder / w.file_name
            if src.exists() and src != dst and not dst.exists():
                shutil.move(str(src), str(dst))
        w.local_path = str(folder)
        database.update_work(cfg, w)
    # 清理空的旧目录（不删根目录与最终文件夹）
    for d in old_dirs:
        if d != base_dir and d != folder and d.is_dir():
            try:
                if not any(d.iterdir()):
                    d.rmdir()
            except OSError:
                pass
    return str(folder)
