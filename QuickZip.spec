# -*- mode: python ; coding: utf-8 -*-

EXCLUDE_MODULES = [
    'tkinter', 'unittest', 'pydoc', 'doctest', 'pdb', 'email', 'http',
    'html', 'xmlrpc', 'ftplib', 'lib2to3', 'distutils', 'setuptools',
    'pip', 'numpy', 'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtQuick3D',
    'PyQt6.QtWebEngineCore', 'PyQt6.QtMultimedia', 'PyQt6.QtOpenGL',
    'PyQt6.QtPrintSupport', 'PyQt6.QtSql', 'PyQt6.QtTest', 'PyQt6.QtDBus',
    'PyQt6.QtPdf', 'PyQt6.QtDesigner', 'PyQt6.QtCharts', 'PyQt6.QtBluetooth',
    'PyQt6.QtNfc', 'PyQt6.QtPositioning', 'PyQt6.QtSensors',
    'PyQt6.QtSerialPort', 'PyQt6.QtWebSockets', 'PyQt6.QtTextToSpeech',
]

DROP_BINARIES = (
    'opengl32sw.dll', 'd3dcompiler_47.dll', 'qt6quick', 'qt6qml',
    'qt6designer', 'qt6pdf', 'qt6shadertools', 'qt6multimedia', 'qt6sql',
    'qt6test', 'qt6charts', 'qt6bluetooth', 'qt6nfc', 'qt6positioning',
    'qt6sensors', 'qt6serialport', 'qt6websockets', 'qt6texttospeech',
    'qt6spatialaudio', 'qt6labs', 'avcodec-', 'avformat-', 'avutil-',
    'swresample-', 'swscale-', 'qt6webengine', 'qt63d', 'qt6datavisualization',
)

DROP_DATA_DIRS = (
    'pyqt6\\qt6\\qml', 'pyqt6/qt6/qml',
    'pyqt6\\qt6\\plugins\\multimedia', 'pyqt6/qt6/plugins/multimedia',
    'pyqt6\\qt6\\plugins\\sqldrivers', 'pyqt6/qt6/plugins/sqldrivers',
    'pyqt6\\qt6\\plugins\\designer', 'pyqt6/qt6/plugins/designer',
    'pyqt6\\qt6\\plugins\\assetimporters', 'pyqt6/qt6/plugins/assetimporters',
    'pyqt6\\qt6\\plugins\\renderers', 'pyqt6/qt6/plugins/renderers',
)

KEEP_TRANSLATIONS = ('qtbase_ru', 'qt_ru', 'qtbase_en', 'qt_en')


def keep_binary(entry):
    name = entry[0].lower()
    return not any(part in name for part in DROP_BINARIES)


def keep_data(entry):
    name = entry[0].lower().replace('/', '\\')
    if any(name.startswith(folder.replace('/', '\\'))
           for folder in DROP_DATA_DIRS):
        return False
    if 'translations' in name and name.endswith('.qm'):
        return any(keep in name for keep in KEEP_TRANSLATIONS)
    return True


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets\\icons\\app.ico', 'assets\\icons')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDE_MODULES,
    noarchive=False,
    optimize=2,
)

a.binaries = [entry for entry in a.binaries if keep_binary(entry)]
a.datas = [entry for entry in a.datas if keep_data(entry)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='QuickZip',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icons\\app.ico'],
)
