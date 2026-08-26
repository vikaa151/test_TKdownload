"""文件命名与非法字符清洗。

命名规则：
  备注（无备注则为空）-昵称-抖音号-作品发布时间-视频/图集/实况照片-详细文字描述
"""
from __future__ import annotations

import re

from .constants import MAX_FILENAME_LEN, DESC_MAX_LEN

# Windows / 各平台非法文件名字符
_ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n\t\x00-\x1f]')


def sanitize(text: str) -> str:
    """清洗单段文本，去掉/替换非法字符并压缩空白。"""
    if not text:
        return ""
    text = _ILLEGAL.sub("_", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def format_time(dt, with_colon: bool = False) -> str:
    """格式化时间。with_colon=False 用 '.' 代替 ':'（避免 Windows 文件名非法）。"""
    if dt is None:
        return ""
    sep = ":" if with_colon else "."
    return dt.strftime(f"%Y-%m-%d %H{sep}%M{sep}%S")


def build_filename(
    remark: str,
    nickname: str,
    douyin_id: str,
    publish_time: str,
    work_type: str,
    description: str,
    max_len: int = MAX_FILENAME_LEN,
) -> str:
    """
    生成作品文件名（不含扩展名）。
    规则：备注-昵称-抖音号-作品发布时间-类型-描述；空备注则省略前缀。
    """
    parts = [sanitize(remark), sanitize(nickname), sanitize(douyin_id),
             sanitize(publish_time), sanitize(work_type)]
    desc = sanitize(description)
    if len(desc) > DESC_MAX_LEN:
        desc = desc[:DESC_MAX_LEN].rstrip() + "…"
    parts.append(desc)
    # 仅保留非空段，避免多余连字符
    name = "-".join(p for p in parts if p)
    if len(name) > max_len:
        name = name[:max_len].rstrip("-_ ")
    return name or "未命名作品"


def build_account_folder_name(nickname: str, douyin_id: str, kind: str, count: int) -> str:
    """账号作品文件夹命名（账户作品保存规则 1-5）。

    kind:
      - "works"  -> 昵称_抖音号_作品数量共x个   （x=该账号作品总数）
      - "images" -> 昵称_抖音号_图片数量共x个   （x=该图集图片数）
    """
    nick = sanitize(nickname) or "未命名"
    did = sanitize(douyin_id) or "na"
    if kind == "images":
        label = f"图片数量共{count}个"
    else:
        label = f"作品数量共{count}个"
    return f"{nick}_{did}_{label}"
