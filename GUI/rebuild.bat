@echo off
chcp 65001 >nul
echo ========================================
echo 清理并重新打包程序
echo ========================================
echo.

echo [1/3] 彻底清理旧文件...
if exist build rmdir /s /q build
if exist dist_final rmdir /s /q dist_final
if exist __pycache__ rmdir /s /q __pycache__

:: 清理所有 __pycache__ 目录
echo 清理所有缓存文件...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"

echo.
echo [2/3] 开始重新打包...
pyinstaller arm_control_app.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
echo [3/3] 检查结果...
if exist "dist_final\机械臂控制系统.exe" (
    echo [成功] 重新打包完成！
    echo.
    dir "dist_final\机械臂控制系统.exe" | findstr "机械臂控制系统.exe"
) else (
    echo [错误] 未找到可执行文件！
    pause
    exit /b 1
)

echo.
echo ========================================
echo 重新打包完成！
echo ========================================
echo.
pause
