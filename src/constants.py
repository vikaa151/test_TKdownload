"""
抖音批量下载器 —— 常量与字段定义
统一规范（依据用户 2026-08-21~08-26 IMA 对话整理 + 本次 12 条需求）：
- 作品类型：视频 / 图集 / 实况照片
- 账号字段、作品字段见 models.py
- 文件命名：备注（无则为空）-昵称-抖音号-作品发布时间-视频/图集/实况照片-详细文字描述
"""
from __future__ import annotations

# 作品类型
WORK_TYPE_VIDEO = "视频"
WORK_TYPE_IMAGE = "图集"
WORK_TYPE_LIVE = "实况照片"
WORK_TYPES = (WORK_TYPE_VIDEO, WORK_TYPE_IMAGE, WORK_TYPE_LIVE)

# 账号管理导出列（顺序即 Excel 列顺序）
ACCOUNT_EXPORT_FIELDS = [
    ("nickname", "昵称"),
    ("douyin_id", "抖音号"),
    ("uid", "UID"),
    ("share_url", "分享链接/网页链接"),
    ("homepage_url", "主页链接"),
    ("monitor", "是否监控"),
    ("auto_download", "自动下载"),
    ("download_dir", "下载目录"),
    ("remark", "备注"),
    ("last_update", "最近更新时间"),
    ("created_at", "创建时间"),
]

# 作品导出列
WORK_EXPORT_FIELDS = [
    ("remark", "备注"),
    ("nickname", "昵称"),
    ("douyin_id", "抖音号"),
    ("publish_time", "作品发布时间"),
    ("work_type", "作品类型"),
    ("description", "详细文字描述"),
    ("url", "作品链接"),
    ("download_time", "下载时间"),
    ("local_path", "本地路径"),
    ("file_name", "文件名"),
]

# 配置导入模板（Excel 批量导入账号）列
ACCOUNT_IMPORT_FIELDS = [
    ("nickname", "昵称"),
    ("douyin_id", "抖音号"),
    ("share_url", "分享链接/主页链接"),
    ("remark", "备注"),
    ("monitor", "是否监控"),
    ("auto_download", "自动下载"),
]

# 默认请求头 UA（桌面端，避免风控更友好）
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# 抖音 Web API 端点
API_AWEME_DETAIL = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
API_USER_POST = "https://www.douyin.com/aweme/v1/web/aweme/post/"
API_USER_PROFILE = "https://www.douyin.com/aweme/v1/web/user/profile/other/"

# 单条文件名最大长度（防路径超长）
MAX_FILENAME_LEN = 180
# 描述截断长度
DESC_MAX_LEN = 60
