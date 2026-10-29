from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from functools import lru_cache

log = logging.getLogger("quickzip.shell")

_COINIT_APARTMENTTHREADED = 0x2
_RPC_E_CHANGED_MODE = -2147417850


def reveal_in_explorer(path: str) -> bool:
    target = os.path.normpath(os.path.abspath(path))
    started = time.perf_counter()
    if sys.platform != "win32":
        return _open_folder(os.path.dirname(target))
    if not os.path.exists(target):
        log.warning("Reveal target is missing, opening its folder: %s",
                    target)
        return _open_folder(os.path.dirname(target))
    try:
        _shell_select(target)
    except OSError as exc:
        log.warning(
            "SHOpenFolderAndSelectItems failed for %s: %s; "
            "falling back to explorer.exe /select", target, exc,
        )
        return _explorer_select(target)
    log.info("Revealed in Explorer: %s (%.0f ms)", target,
             (time.perf_counter() - started) * 1000)
    return True


@lru_cache(maxsize=1)
def _shell_api():
    import ctypes
    from ctypes import wintypes

    shell32 = ctypes.WinDLL("shell32")
    ole32 = ctypes.WinDLL("ole32")
    shell32.ILCreateFromPathW.argtypes = [wintypes.LPCWSTR]
    shell32.ILCreateFromPathW.restype = ctypes.c_void_p
    shell32.ILFree.argtypes = [ctypes.c_void_p]
    shell32.ILFree.restype = None
    shell32.SHOpenFolderAndSelectItems.argtypes = [
        ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, wintypes.DWORD,
    ]
    shell32.SHOpenFolderAndSelectItems.restype = ctypes.c_long
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    return shell32, ole32


def _hresult(value: int) -> str:
    return f"HRESULT 0x{value & 0xFFFFFFFF:08X}"


def _shell_select(path: str) -> None:
    shell32, ole32 = _shell_api()
    status = ole32.CoInitializeEx(None, _COINIT_APARTMENTTHREADED)
    if status < 0 and status != _RPC_E_CHANGED_MODE:
        raise OSError(f"CoInitializeEx failed: {_hresult(status)}")
    initialized = status >= 0
    try:
        pidl = shell32.ILCreateFromPathW(path)
        if not pidl:
            raise OSError(f"ILCreateFromPathW returned NULL for {path}")
        try:
            result = shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
            if result < 0:
                raise OSError(
                    f"SHOpenFolderAndSelectItems failed: {_hresult(result)}"
                )
        finally:
            shell32.ILFree(pidl)
    finally:
        if initialized:
            ole32.CoUninitialize()


def _explorer_select(path: str) -> bool:
    command = f'explorer.exe /select,"{path}"'
    try:
        subprocess.Popen(command)
    except OSError as exc:
        log.error("Cannot start %s: %s", command, exc)
        return False
    log.info("Started %s", command)
    return True


def _open_folder(folder: str) -> bool:
    try:
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])
    except OSError as exc:
        log.error("Cannot open folder %s: %s", folder, exc)
        return False
    log.info("Opened folder %s", folder)
    return True
