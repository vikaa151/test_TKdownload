"""抖音请求签名（核心反爬）—— 纯 Python a_bogus 实现。

来源：github.com/JoeanAmier/TikTokDownloader 的 src/encrypt/aBogus.py
（GPLv3，原作者与许可证信息已在 src/abogus.py 中保留）。

设计：把签名抽象为可插拔的 Signer。开箱默认使用 PyAbogusSigner ——
直接复用上面那个开源纯 Python 实现（依赖 gmssl），无需安装 Node.js、
无需提供任何 JS 文件即可自动生成 a_bogus。
"""
from __future__ import annotations

from typing import Optional

from .config import AppConfig

try:
    from .abogus import ABogus
except Exception:  # pragma: no cover - 依赖缺失时由构造期报错
    ABogus = None


class SignerError(RuntimeError):
    pass


class PyAbogusSigner:
    """基于 TikTokDownloader 开源纯 Python 实现的 a_bogus 签名器。

    优点：无需 Node.js、无需提供任何 JS 文件，pip 装好 `gmssl` 即可用。
    """

    def __init__(self, user_agent: str):
        if ABogus is None:
            raise SignerError(
                "缺少依赖 gmssl，无法生成 a_bogus 签名。请先执行：pip install gmssl>=3.2.2"
            )
        try:
            self._ab = ABogus(user_agent=user_agent)
        except Exception as e:  # gmssl 未安装等
            raise SignerError(f"初始化 a_bogus 签名失败：{e}") from e

    def sign(self, params: dict, ua: str = "", method: str = "GET") -> str:
        """生成 a_bogus 签名串。

        params: 请求的查询参数字典（如 {"aweme_id": "...", "aid": "6383", ...}）。
        返回非空 a_bogus 字符串；若生成失败抛出 SignerError（不会静默用错签名）。
        """
        try:
            sig = self._ab.get_value(params=params, method=method)
        except Exception as e:
            raise SignerError(f"a_bogus 签名失败：{e}") from e
        if not sig or not isinstance(sig, str):
            raise SignerError("a_bogus 返回空签名，请检查 abogus.py 实现。")
        return sig


def create_signer(cfg: AppConfig) -> PyAbogusSigner:
    """创建签名器（纯 Python a_bogus，依赖 gmssl）。"""
    from src.constants import DEFAULT_UA
    return PyAbogusSigner(DEFAULT_UA)
