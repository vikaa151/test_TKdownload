"""应用入口：桌面（Windows exe）与安卓（APK）共用。

p4a 的 qt bootstrap 约定从 source.dir 根目录的 main.py 启动；
桌面端 `python __main__.py` 同样走这里，保证两套环境启动逻辑一致。
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.config import AppConfig
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    from gui.mobile import apply_mobile_style
    apply_mobile_style(app)  # 安卓下启用触摸字号/点按区域适配，桌面端无副作用
    cfg = AppConfig()
    cfg.load()
    win = MainWindow(cfg)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
