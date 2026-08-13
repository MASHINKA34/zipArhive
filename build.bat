@echo off
setlocal
chcp 65001 >nul

set NAME=QuickZip

echo Сборка %NAME%.exe ...

pyinstaller --noconfirm --clean QuickZip.spec

if errorlevel 1 (
    echo.
    echo Сборка завершилась с ошибкой.
    exit /b 1
)

echo.
echo Готово. Файл: dist\%NAME%.exe
endlocal
