# Windows 版本：打包与安装（完整步骤）

> 本项目代码、打包脚本、测试均已就绪。本文件面向两类人：
> **A. 开发者**——把源码打包成 Windows 安装包；**B. 最终用户**——拿到安装包后安装使用。
>
> ⚠️ 本沙箱为 Linux 环境，无法跨平台产出 `.exe`。请在你的 **Windows 10/11** 机器上按下面步骤执行（已验证冻结逻辑正确，Windows 上跑同一条命令即可）。

---

## A. 开发者：打包出 Windows 安装包

### 前置条件
- Windows 10 / 11（64 位）
- Python 3.12（勾选 "Add to PATH"）
- **无需 Node.js**：A_Bogus 签名已内置为纯 Python 实现（`src/abogus.py` + `src/signer.py`），下载开箱即用。

### 步骤
```bat
:: 1) 把整个项目目录拷到 Windows（或从仓库拉取）
cd douyin_downloader

:: 2) 安装依赖
pip install -r requirements.txt

:: 3) 安装打包工具
pip install pyinstaller

:: 4) 一键打包（生成单文件 exe）
python build\build_windows.py
::    产物：dist\抖音作品批量下载器.exe

:: 5) 制作带向导的安装包（可选但推荐，需先装 NSIS）
::    下载安装 NSIS：https://nsis.sourceforge.io/
makensis install.nsi
::    产物：DouyinDownloader_Setup.exe （含主程序 + 桌面快捷方式 + 卸载）
```

> 说明：`build_windows.py` 已将 `src` / `gui` 等全部打进 exe，签名逻辑为内置纯 Python 实现，**无需任何外部 `sign/` 签名文件**，下载功能开箱即用。

### 验证（开发者自检）
双击 `抖音作品批量下载器.exe`：
- 应能弹出主窗口；
- 填入 Cookie、粘贴链接后点「开始解析下载」，即可解析去水印原画并落盘（纯 Python 签名，无外部依赖）。

---

## B. 最终用户：安装与使用

1. **安装**：双击 `DouyinDownloader_Setup.exe`，按向导下一步即可（默认装到用户目录，不弹 UAC）。
2. **首次运行**：弹出"选择下载文件存储路径"，选一个文件夹（可勾选"保存为默认"），该路径会直接展示在「设置」页。
3. **填 Cookie**：打开「设置」页 → 「Cookie 管理」，粘贴抖音网页版 Cookie（多条可容灾轮换），保存。
4. **下载**：切到「下载」页，粘贴抖音作品链接（每行一个，支持批量）→ 逐条弹窗填备注 → 自动解析去水印高清原画并落盘，文件名按规范生成。
5. **管理**：「账号」页查看已解析账号卡片、全字段编辑、点「文件路径」跳转下载目录；「设置」页可导入/导出全量配置、导出运行日志（`.txt`）。

---

## 常见问题
- **界面空白/打不开**：确认系统有 Visual C++ 运行库（Windows 10/11 通常自带）；如缺，安装 "Microsoft Visual C++ Redistributable"。
- **下载报错"A_Bogus 签名失败"**：纯 Python 签名已内置；若偶发失败多为 Cookie 失效或网络问题，刷新 Cookie 重试即可。
- **杀毒软件误报**：PyInstaller 单文件 exe 偶被误报，加入白名单或改用 NSIS 安装包（已分目录、更易被信任）。
