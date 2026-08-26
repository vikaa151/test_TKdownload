Unicode true
!include "MUI2.nsh"

Name "抖音作品批量下载器"
OutFile "DouyinDownloader_Setup.exe"
InstallDir "$LOCALAPPDATA\抖音作品批量下载器"
RequestExecutionLevel user

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "SimpChinese"

Section "Install"
    SetOutPath "$INSTDIR"
    File "dist\抖音作品批量下载器.exe"

    ; 释放 sign/ 目录（run_abogus.js + README；用户需自备 abogus.js 放入此目录）
    SetOutPath "$INSTDIR\sign"
    File "sign\run_abogus.js"
    File "sign\README.txt"

    ; 桌面快捷方式
    CreateShortCut "$DESKTOP\抖音作品批量下载器.lnk" "$INSTDIR\抖音作品批量下载器.exe"

    ; 卸载程序
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$DESKTOP\抖音作品批量下载器.lnk"
    Delete "$INSTDIR\uninstall.exe"
    Delete "$INSTDIR\抖音作品批量下载器.exe"
    RMDir /r "$INSTDIR\sign"
    RMDir "$INSTDIR"
SectionEnd
