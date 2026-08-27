[app]
title = 抖音作品批量下载器
package.name = douyin_downloader
# 调试阶段用 com.example 占位；上架前请改为你自己的反写域名（如 com.yourname.douyin）
package.domain = com.example.douyin
version = 1.0.0
# 本 spec 位于 build/ 下，故 source.dir 指向仓库根（含 main.py / src / gui）
source.dir = ..
source.include_exts = py,png,jpg,kv,atlas,txt,json
# 不把构建/测试/CI/运行产物打进 APK
source.exclude_dirs = build,.buildozer,bin,tests,.github,logs,__pycache__
source.exclude_patterns = *.pyc,*.db,config.json,backup_*

# ===== 以下 android.* 必须放在 [app] 段（buildozer 源码从 [app] 读取，[android] 段会被整体忽略）=====
# 仅 INTERNET 必需；下载默认写入应用私有外部存储（/sdcard/Android/data/<pkg>/files/Downloads），
# 规避 Android 11+ 分区存储，无需申请 WRITE/READ_EXTERNAL_STORAGE 权限。
android.permissions = INTERNET
android.api = 33
android.minapi = 24
# NDK 用 p4a 推荐版本（buildozer 1.6.0 + 当前 p4a 推荐 r28c），避免与 Qt-for-Android 不兼容
android.ndk = 28c
android.accept_sdk_license = True

# 入口：p4a qt bootstrap 约定从 source.dir 下的 main.py 启动（见仓库根 main.py）。
# A_Bogus 签名：纯 Python 实现（src/abogus.py + src/signer.py），依赖 gmssl，
# 已在 requirements 中声明，无需 Node.js、无需任何 JS 文件。
orientation = portrait
osx.kivy_name = 抖音作品批量下载器

[buildozer]
log_level = 2
warn_on_root = 1

[p4a]
p4a.bootstrap = qt
p4a.apk_cmd = debug

[deploy]
deploy.json = ./deploy.json
