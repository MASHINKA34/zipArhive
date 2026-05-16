@echo off
setlocal

set NAME=QuickZip
set ICON_OPT=
set DATA_OPT=
if exist "assets\icons\app.ico" set ICON_OPT=--icon "assets\icons\app.ico"
if exist "assets\icons\app.ico" set DATA_OPT=--add-data "assets\icons\app.ico;assets\icons"

echo Сборка %NAME%.exe ...

pyinstaller --noconfirm --clean --onefile --windowed --name %NAME% %ICON_OPT% %DATA_OPT% main.py

if errorlevel 1 (
    echo.
    echo Сборка завершилась с ошибкой.
    exit /b 1
)

echo.
echo Готово. Файл: dist\%NAME%.exe
endlocal
