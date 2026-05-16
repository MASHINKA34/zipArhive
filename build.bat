@echo off
rem Сборка Quick Zip в один исполняемый файл через PyInstaller.
setlocal

set NAME=QuickZip
set ICON_OPT=
if exist "assets\icons\app.ico" set ICON_OPT=--icon=assets\icons\app.ico

echo Сборка %NAME%.exe ...

pyinstaller --noconfirm --clean --onefile --windowed --name %NAME% %ICON_OPT% main.py

if errorlevel 1 (
    echo.
    echo Сборка завершилась с ошибкой.
    exit /b 1
)

echo.
echo Готово. Файл: dist\%NAME%.exe
endlocal
