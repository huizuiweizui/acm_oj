@echo off
setlocal
if "%~1"=="" (
    echo Usage: with-msvc.cmd command [arguments] 1>&2
    exit /b 2
)

if /i "%VSCMD_ARG_TGT_ARCH%"=="x64" goto run
set "vswhere=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%vswhere%" goto missing
set "vs_install="
for /f "usebackq delims=" %%I in (`"%vswhere%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "vs_install=%%I"
if not defined vs_install goto missing
call "%vs_install%\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1

:run
set "JUDGE_WINDOWS_USE_MSVC=True"
%*
exit /b %errorlevel%

:missing
echo Visual Studio C++ x64 build tools were not found. 1>&2
exit /b 1
