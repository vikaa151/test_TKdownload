"""移动端触摸布局适配：安卓下统一字号、点按区域、竖屏堆叠。

设计原则：
- 桌面端完全不受影响（所有改动仅在 _is_android() 为真时生效）。
- 通过 QApplication.setFont 设置全局基准字号，并叠加最小点按高度的样式表，
  让所有按钮 / 输入框在手指触摸下可达；通过 row_layout() 工厂把
  「工具栏 / 按钮组 / 标签+控件行」在窄屏上改为竖排堆叠。
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QBoxLayout
from PySide6.QtGui import QFont

from src.config import _is_android


ANDROID = _is_android()

# 触摸基准参数（px / pt）
FONT = 16          # 安卓全局字号
TAP_H = 48         # 按钮最小点按高度（Apple HIG ~44px，取整 48 更稳）
INPUT_H = 44       # 输入框最小高度

_ANDROID_STYLE = f"""
QPushButton {{ min-height: {TAP_H}px; padding: 8px 14px; }}
QLineEdit, QTextEdit, QSpinBox, QComboBox {{ min-height: {INPUT_H}px; }}
QTabBar::tab {{ min-height: 46px; min-width: 80px; font-weight: bold; }}
"""


def apply_mobile_style(app: QApplication) -> None:
    """在安卓下安装全局触摸样式与基准字号；桌面端原样返回。"""
    if not ANDROID:
        return
    font = QFont()
    font.setPointSize(FONT)
    app.setFont(font)
    app.setStyleSheet(_ANDROID_STYLE)


def row_layout() -> QBoxLayout:
    """安卓竖排堆叠、桌面横排的布局工厂。

    返回 QVBoxLayout / QHBoxLayout（均为 QBoxLayout 子类），
    可直接替换原 QHBoxLayout() 用于工具栏、按钮组、标签+控件行，
    调用方无需改动 addWidget / addStretch / addLayout 等用法。
    """
    return QVBoxLayout() if ANDROID else QHBoxLayout()
