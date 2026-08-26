# 安卓 APK 构建（完整步骤）

## 一、构建 APK 需要你提供什么？——答：不需要任何手机信息

很多同学误以为"出 APK 要填手机型号 / Android 版本"。**不是的**：
APK 是**通用安装包**，与具体手机无关。构建时只需指定**最低 Android 版本（minSdk，已设为 24 = Android 7.0）**和**目标 CPU 架构（默认 arm64-v8a，覆盖绝大多数现代手机）**，这两项已在 `build/buildozer.spec` 配好。

你**不需要**提供：手机型号、序列号、Android 版本、IMEI 等任何设备信息。
你**需要**提供的是：**一台能联网装工具的 Ubuntu 构建机**（云服务器或虚拟机均可），以及你自有的签名文件 `sign/abogus.js`。

---

## 二、构建环境（必须 Ubuntu，不能在 Windows/macOS 直构建）

- Ubuntu 20.04 / 22.04（推荐 22.04）
- Python 3.10+（建议 3.10，与 p4a 兼容性最佳）
- Java JDK 17（buildozer 依赖）
- 约 10 GB 磁盘（Android SDK/NDK/Qt 缓存）
- 能访问 Google 域名（下载 SDK/NDK；若你的网络受限，需自备代理/镜像）

> ⚠️ 当前开发沙箱为 Linux 但**无 Android SDK/NDK/Qt 且网络受限**，无法在此构建 APK。请在你自己的 Ubuntu 环境执行以下步骤。

---

## 三、构建步骤

```bash
# 1) 准备 Ubuntu 环境
sudo apt update
sudo apt install -y python3-pip python3-venv openjdk-17-jdk git unzip \
     build-essential ccache libncurses5-dev libffi-dev libssl-dev \
     libreadline-dev libbz2-dev libsqlite3-dev liblzma-dev zlib1g-dev

# 2) 拉取项目并建虚拟环境
git clone <你的仓库> douyin_downloader && cd douyin_downloader
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3) 签名（已内置，无需任何文件）
#    本项目 A_Bogus 为纯 Python 实现（src/abogus.py + src/signer.py，依赖 gmssl），
#    已写入 requirements.txt，安卓端直接复用，无需 a_bogus.js、无需 Node.js。

# 4) 安装 buildozer 并构建
pip install buildozer
cd build && buildozer android debug        # 首次会下载 SDK/NDK/Qt，耗时较长（数十分钟）
#    产物：bin/douyin_downloader-1.0.0-debug.apk
```

---

## 四、关键技术点（务必先读）

1. **A_Bogus 签名：纯 Python，安卓免 Node（已解决）**
   - 本项目 A_Bogus 已是纯 Python 实现（`src/abogus.py` + `src/signer.py` 的 `PyAbogusSigner`，依赖 `gmssl`），
     不依赖 Node.js、不含任何 JS 文件，安卓端直接复用，签名已无硬限制。
   - 依赖已在 `build/buildozer.spec` 的 `requirements` 中声明（含 `gmssl`）。
2. **存储权限（Android 11+ 分区存储）**
   - 默认下载目录指向应用私有外部存储 `/sdcard/Android/data/<pkg>/files/Downloads`，
     始终可写、无需任何存储权限，构建仅声明 `INTERNET` 即可。
   - 用户可在手机文件管理器「Android/data/<pkg>/files/Downloads」取回作品。
3. **技术路线：Qt-for-Android 复用现有桌面代码**
   - `build/buildozer.spec` 使用 `p4a.bootstrap = qt` + `pySide6`，
     直接把现有 PySide6 界面与 `src/` 业务逻辑打包为 APK，无需 Kivy 重写。
   - 入口为仓库根 `main.py`（p4a qt bootstrap 约定），桌面端 `__main__.py` 共用同一 `main()`。
4. **移动端触摸布局适配（v1 已做）**
   - `gui/mobile.py` 提供 `apply_mobile_style(app)` 与 `row_layout()` 两个适配器，**仅在安卓下生效、桌面端零副作用**：
     - `apply_mobile_style` 在安卓下调用 `QApplication.setFont(16pt)` 放大全局字号，并叠加样式表让按钮最小点按高度 ≥48px、输入框 ≥44px、标签页更易点按；
     - `row_layout()` 把工具栏 / 按钮组 /「标签+控件」行在窄屏上自动改为竖排堆叠，桌面端仍是横排。
   - 4 个标签页（下载 / 账号 / 设置 / 日志）与全部弹窗（备注 / 路径 / Cookie / 账号编辑 / 合并 / 重下）均已通过 `row_layout()` 适配；账号卡片在安卓下加高至 120px、标题字号放大，保障手指点按与竖屏可读性。

---

## 五、装到手机：你需要做的"手机端操作"只有一步

APK 是通用包，拷到任何兼容手机都能装。手机端**唯一**需要你点一下的是：

> **设置 → 安全 → 允许安装未知来源应用（对该文件管理器/浏览器授权）**

这是 **Android 系统对所有第三方 APK 的强制要求**，并非本应用额外增加的操作。授权后：
- 点击 APK → 安装 → 打开；
- 首次运行选下载路径、设置页填 Cookie、下载页粘贴链接——这些是使用功能，不是"额外配置"；
- **无需 root、无需 adb、无需开发者模式**（除非你选了方案一需要特殊配置）。

---

## 六、小结
- 构建 APK **不需要手机任何信息**，只需 Ubuntu 构建机 + 你的 `abogus.js`；
- 安卓端签名为纯 Python 实现，无需 Node、无需任何签名文件或 Secret；
- 沙箱无法代构建，请在本机 Ubuntu 执行；装到手机后仅需系统强制的一次性授权。
