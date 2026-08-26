"""数据模型：账号(Account) 与 作品(Work) 的字段定义与序列化。"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Account:
    id: Optional[int] = None
    nickname: str = ""
    douyin_id: str = ""          # 抖音号（unique_id）
    uid: str = ""                # 数字 UID
    sec_uid: str = ""            # 加密 UID（用于监控拉取作品）
    share_url: str = ""          # 分享链接/网页链接（手机 APP 可跳转打开抖音）
    homepage_url: str = ""       # 主页链接
    monitor: bool = False        # 是否监控
    auto_download: bool = False  # 监控到新作品是否自动下载
    download_dir: str = ""       # 该账号下载目录（空则用全局）
    remark: str = ""             # 备注
    cookie_slot: int = 0         # 使用的 Cookie 槽位
    last_update: str = ""        # 最近更新时间
    created_at: str = ""         # 创建时间
    updated_at: str = ""         # 更新时间

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Account":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class Work:
    id: Optional[int] = None
    account_id: Optional[int] = None
    aweme_id: str = ""           # 作品 ID（去重主键）
    work_type: str = ""          # 视频/图集/实况照片
    publish_time: str = ""       # 作品发布时间（格式化字符串）
    description: str = ""        # 详细文字描述
    url: str = ""                # 作品链接
    download_time: str = ""      # 下载时间
    remark: str = ""             # 备注
    local_path: str = ""         # 本地路径
    file_name: str = ""          # 文件名
    nickname: str = ""           # 冗余昵称（导出方便）
    douyin_id: str = ""          # 冗余抖音号
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Work":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})
