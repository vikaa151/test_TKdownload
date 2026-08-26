"""打包 Windows exe（PyInstaller）。运行：python build/build_windows.py"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build():
    datas = []

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "抖音作品批量下载器",
        "--windowed",
        "--onefile",
        "--paths", str(ROOT),
        "--hidden-import", "src",
        "--hidden-import", "gui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
    ]
    for d in datas:
        cmd += ["--add-data", d]
    cmd.append(str(ROOT / "__main__.py"))
    print("执行：", " ".join(cmd))
    subprocess.check_call(cmd)


if __name__ == "__main__":
    build()
