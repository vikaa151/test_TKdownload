"""抖音客户端：解析作品/账号、选择原画去水印媒体、下载、Cookie 容灾。

设计要点：
- 解析字段提取、媒体选择（原画/原图、去水印）做成纯函数，便于离线单测（喂样例 JSON）。
- 网络方法仅在真实请求时调用；签名依赖 signer（A_Bogus）。
- 多 Cookie 容灾：空结果/被拦截时按槽位轮换（前期故障：空列表未抛错导致轮换失效）。
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from .config import AppConfig
from .constants import (
    API_AWEME_DETAIL, API_USER_PROFILE, DEFAULT_UA, WORK_TYPE_IMAGE,
    WORK_TYPE_LIVE, WORK_TYPE_VIDEO,
)
from .naming import format_time
from .signer import PyAbogusSigner, SignerError


class DouyinAPIError(RuntimeError):
    pass


# 抖音域名（用于从分享文案中识别链接）
_URL_TOKEN_RE = re.compile(
    r"https?://[^\s，。、）)】\]]+"
    r"|v\.douyin\.com/[^\s，。、）)】\]]+"
    r"|www\.douyin\.com/[^\s，。、）)】\]]+"
)


def extract_douyin_urls(text: str) -> list[str]:
    """从任意粘贴文本（含抖音「外发词」分享文案）中提取抖音链接。

    分享文案示例：
      ``7.99 :6pm 07/08 Wzt:/ X@m.Qx # 就问谁能驯服这只声控鸡
        https://v.douyin.com/1-taoTWw64c/ 复制此链接，打开Dou音搜索...``
    会提取出 ``https://v.douyin.com/1-taoTWw64c/``。
    """
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for m in _URL_TOKEN_RE.finditer(text):
        u = m.group(0).strip().rstrip(".,;。，")
        if not u.startswith("http"):
            u = "https://" + u
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


@dataclass
class MediaItem:
    url: str
    ext: str
    index: int = 0          # 图集序号（视频/实况为 0）
    is_cover: bool = False


@dataclass
class ParsedAccount:
    nickname: str = ""
    douyin_id: str = ""
    uid: str = ""
    sec_uid: str = ""
    share_url: str = ""
    homepage_url: str = ""


@dataclass
class ParsedWork:
    aweme_id: str = ""
    work_type: str = ""
    publish_time: str = ""
    publish_ts: int = 0
    description: str = ""
    url: str = ""
    media: list = field(default_factory=list)   # List[MediaItem]
    account: ParsedAccount = field(default_factory=ParsedAccount)


# ---------------- 纯函数：字段提取（可单测） ----------------
def _pick_best(urls: list) -> str:
    if not urls:
        return ""
    # 抖音 url_list 通常末尾为最高清，取第一个有效即可
    for u in urls:
        if u:
            return u
    return urls[0]


def build_media(aweme: dict) -> list[MediaItem]:
    """从 aweme 详情选择「原画/原图、去水印」媒体列表。

    图集判定以 ``images`` 是否存在为准（实况照片优先）。真实图集常会附带一个
    仅含 BGM 的 ``video`` 字段，不能因此误判为视频而下载到「只有音频」的文件。
    """
    media: list[MediaItem] = []
    images = aweme.get("images") or []
    video = aweme.get("video") or {}

    if _is_live_photo(aweme):
        # 实况照片：一律以视频（mp4）形式下载，保留动态，不拆成静态图
        url = _best_video_url(video)
        if url:
            media.append(MediaItem(url=url, ext=".mp4", index=0))
        return media

    if images:
        # 图集：逐张取原图
        for i, img in enumerate(images):
            url = _pick_best(img.get("url_list", []))
            if url:
                media.append(MediaItem(url=url, ext=".jpg", index=i))
        return media

    # 视频：选择最高码率（原画）去水印地址，避开带水印的 download_addr
    url = _best_video_url(video)
    if url:
        media.append(MediaItem(url=url, ext=".mp4", index=0))
    return media


def _best_video_url(video: dict) -> str:
    bit_rates = video.get("bit_rate") or []
    if bit_rates:
        bit_rates = sorted(bit_rates, key=lambda b: b.get("bit_rate", 0) or 0, reverse=True)
        for br in bit_rates:
            pa = (br.get("play_addr") or {}).get("url_list") or []
            u = _pick_best(pa)
            if u:
                return u
    # 兜底：video.play_addr
    pa = (video.get("play_addr") or {}).get("url_list") or []
    return _pick_best(pa)


def _is_live_photo(aweme: dict) -> bool:
    """是否实况照片（带动态）。统一判定，detect/build 共用，避免两处不一致。"""
    return bool(
        aweme.get("live_photo")
        or aweme.get("live_photo_status") == 1
        or (aweme.get("aweme_type") == 0 and aweme.get("live_photo"))
    )


def detect_work_type(aweme: dict) -> str:
    images = aweme.get("images") or []
    # 实况照片优先（一律以视频 mp4 形式下载，保留动态）；其次图集
    # （images 存在即视为图集，即便响应里附带仅含 BGM 的 video 字段）。
    if _is_live_photo(aweme):
        return WORK_TYPE_LIVE
    if images:
        return WORK_TYPE_IMAGE
    return WORK_TYPE_VIDEO


def parse_work_from_detail(detail: dict, url: str = "") -> ParsedWork:
    aweme = detail.get("aweme_detail") or detail.get("aweme") or detail
    if not aweme or not aweme.get("aweme_id"):
        raise DouyinAPIError("接口未返回作品数据（可能 Cookie 失效或签名错误）")
    aweme_id = str(aweme.get("aweme_id", ""))
    desc = aweme.get("desc", "") or ""
    ts = int(aweme.get("create_time", 0) or 0)
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone() if ts else None
    author = aweme.get("author", {}) or {}
    share = author.get("share_info", {}) or {}
    acc = ParsedAccount(
        nickname=author.get("nickname", "") or "",
        douyin_id=author.get("unique_id", "") or "",
        uid=str(author.get("uid", "") or author.get("sec_uid", "") or ""),
        sec_uid=author.get("sec_uid", "") or "",
        share_url=share.get("share_url", "") or author.get("share_url", "") or "",
        homepage_url=share.get("share_url", "") or author.get("share_url", "") or "",
    )
    wtype = detect_work_type(aweme)
    media = build_media(aweme)
    return ParsedWork(
        aweme_id=aweme_id,
        work_type=wtype,
        publish_time=format_time(dt),
        publish_ts=ts,
        description=desc,
        url=url or (acc.share_url and f"https://www.douyin.com/video/{aweme_id}") or "",
        media=media,
        account=acc,
    )


# ---------------- 网络客户端 ----------------
class DouyinClient:
    def __init__(self, cfg: AppConfig, signer: Optional[PyAbogusSigner] = None):
        self.cfg = cfg
        self.ua = DEFAULT_UA
        self.proxy = cfg.proxy or None
        self.signer = signer
        self.timeout = 20.0

    def _headers(self, cookie: str) -> dict:
        return {
            "User-Agent": self.ua,
            "Referer": "https://www.douyin.com/",
            "Cookie": cookie,
            "Accept": "application/json, text/plain, */*",
        }

    @staticmethod
    def _common_params() -> dict:
        return {
            "aid": "6383",
            "version_code": "270800",
            "version_name": "27.8.0",
            "device_platform": "webapp",
            "os": "windows",
            "browser_language": "zh-CN",
            "browser_platform": "Win32",
            "browser_name": "Chrome",
            "browser_version": "122.0.0.0",
            "cookie_enabled": "true",
            "channel": "website",
            "os_version": "10",
            "platform": "PC",
            "resolution": "1920*1080",
        }

    def _signed_params(self, params: dict) -> dict:
        if self.signer is None:
            raise SignerError("未初始化签名器")
        sig = self.signer.sign(params, self.ua)
        params = dict(params)
        params["a_bogus"] = sig
        return params

    @staticmethod
    def _is_blocked(data: dict) -> bool:
        if not isinstance(data, dict):
            return True
        sc = data.get("status_code")
        if sc not in (0, None):
            return True
        # 空列表 = 被拉黑/拦截（前期故障：空响应未触发容灾）
        if "aweme_detail" in data and not data.get("aweme_detail"):
            return True
        if "aweme_list" in data and not data.get("aweme_list"):
            return True
        return False

    def _resolve_aweme_id(self, url: str) -> str:
        m = re.search(r"/(?:video|note)/(\d+)", url)
        if m:
            return m.group(1)
        # 用户主页/作品页带参数：?modal_id= / &modal_id= / vid=
        m = re.search(r"[?&](?:modal_id|vid)=(\d+)", url)
        if m:
            return m.group(1)
        if "v.douyin.com" in url:
            try:
                with httpx.Client(timeout=self.timeout, proxy=self.proxy,
                                  headers={"User-Agent": self.ua}, follow_redirects=True) as c:
                    r = c.get(url)
                    final = str(r.url)
                m = re.search(r"/(?:video|note)/(\d+)", final)
                if m:
                    return m.group(1)
                m = re.search(r"modal_id=(\d+)", final)
                if m:
                    return m.group(1)
            except Exception as e:
                raise DouyinAPIError(f"短链解析失败：{e}")
        raise DouyinAPIError(f"无法从链接中提取作品 ID：{url}")

    def parse_work(self, url: str) -> ParsedWork:
        aweme_id = self._resolve_aweme_id(url)
        cookies = self.cfg.cookie_values()
        if not cookies:
            raise DouyinAPIError("未配置 Cookie，请在设置中填入抖音网页版 Cookie。")
        last_err = None
        for ci, cookie in enumerate(cookies):
            try:
                params = self._common_params()
                params["aweme_id"] = aweme_id
                signed = self._signed_params(params)
                with httpx.Client(timeout=self.timeout, proxy=self.proxy,
                                  headers=self._headers(cookie)) as c:
                    r = c.get(API_AWEME_DETAIL, params=signed)
                    data = r.json()
                if self._is_blocked(data):
                    last_err = f"Cookie#{ci} 返回空/被拦截"
                    continue
                return parse_work_from_detail(data, url)
            except DouyinAPIError as e:
                raise
            except Exception as e:
                last_err = f"Cookie#{ci} 请求异常：{e}"
                continue
        raise DouyinAPIError(f"全部 Cookie 均失败：{last_err}")

    def parse_account_by_homepage(self, homepage_url: str) -> ParsedAccount:
        """从主页链接解析账号（抓取 HTML 中的 sec_uid 再查资料接口）。"""
        try:
            with httpx.Client(timeout=self.timeout, proxy=self.proxy,
                              headers={"User-Agent": self.ua, "Referer": "https://www.douyin.com/"}) as c:
                r = c.get(homepage_url, follow_redirects=True)
                html = r.text
            m = re.search(r"sec_uid[=: \"']+([^&\"']+)", html)
            sec_uid = m.group(1) if m else ""
            if not sec_uid:
                raise DouyinAPIError("主页中未找到 sec_uid")
            cookies = self.cfg.cookie_values()
            cookie = cookies[0] if cookies else ""
            params = self._common_params()
            params["sec_user_id"] = sec_uid
            signed = self._signed_params(params)
            with httpx.Client(timeout=self.timeout, proxy=self.proxy,
                              headers=self._headers(cookie)) as c:
                r = c.get(API_USER_PROFILE, params=signed)
                data = r.json()
            if self._is_blocked(data):
                raise DouyinAPIError("账号资料接口返回空（Cookie 失效或签名错误）")
            u = (data.get("user") or {})
            share = u.get("share_info", {}) or {}
            return ParsedAccount(
                nickname=u.get("nickname", ""),
                douyin_id=u.get("unique_id", ""),
                uid=str(u.get("uid", "") or sec_uid),
                sec_uid=sec_uid,
                share_url=share.get("share_url", "") or homepage_url,
                homepage_url=share.get("share_url", "") or homepage_url,
            )
        except DouyinAPIError:
            raise
        except Exception as e:
            raise DouyinAPIError(f"账号主页解析失败：{e}")

    # ---------------- 监控拉取作品 ----------------
    def get_user_works(self, sec_user_id: str, max_count: int = 20) -> list[ParsedWork]:
        """拉取某账号的作品列表（用于监控一键下载）。"""
        cookies = self.cfg.cookie_values()
        if not cookies:
            raise DouyinAPIError("未配置 Cookie，请在设置中填入抖音网页版 Cookie。")
        out: list[ParsedWork] = []
        has_more = True
        cursor = 0
        last_err = None
        for ci, cookie in enumerate(cookies):
            try:
                while has_more and len(out) < max_count:
                    params = self._common_params()
                    params.update({
                        "sec_user_id": sec_user_id, "max_cursor": cursor,
                        "count": 20, "publish_video": 0,
                    })
                    signed = self._signed_params(params)
                    with httpx.Client(timeout=self.timeout, proxy=self.proxy,
                                      headers=self._headers(cookie)) as c:
                        r = c.get(API_USER_POST, params=signed)
                        data = r.json()
                    if self._is_blocked(data):
                        last_err = f"Cookie#{ci} 返回空/被拦截"
                        break
                    for a in (data.get("aweme_list") or []):
                        try:
                            out.append(parse_work_from_detail({"aweme_detail": a}, ""))
                        except DouyinAPIError:
                            continue
                    has_more = bool(data.get("has_more"))
                    cursor = data.get("max_cursor") or (cursor + 1)
                return out[:max_count]
            except DouyinAPIError:
                raise
            except Exception as e:
                last_err = f"Cookie#{ci} 异常：{e}"
                continue
        raise DouyinAPIError(f"全部 Cookie 均失败：{last_err}")

    # ---------------- 下载 ----------------
    def download_media(self, media: list[MediaItem], dest_dir: str,
                       filename_base: str, cookie: str = "") -> list[str]:
        """下载媒体到 dest_dir，返回已保存文件绝对路径列表（原画/原图）。"""
        from pathlib import Path
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        saved: list[str] = []
        cookies = self.cfg.cookie_values()
        cookie = cookie or (cookies[0] if cookies else "")
        multi = len(media) > 1
        for item in media:
            suffix = f"_{item.index + 1}" if (multi and item.index >= 0) else ""
            fname = f"{filename_base}{suffix}{item.ext}"
            path = Path(dest_dir) / fname
            with httpx.Client(timeout=60.0, proxy=self.proxy,
                              headers=self._headers(cookie), follow_redirects=True) as c:
                with c.stream("GET", item.url) as resp:
                    resp.raise_for_status()
                    with open(path, "wb") as f:
                        for chunk in resp.iter_bytes(65536):
                            f.write(chunk)
            saved.append(str(path))
        return saved
