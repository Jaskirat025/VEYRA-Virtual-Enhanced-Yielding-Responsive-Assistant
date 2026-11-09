"""System tools: applications, volume, brightness, screenshots, clipboard."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Literal

from backend.paths import app_data_dir
from backend.tools.registry import Category, Risk, ToolError, tool


def _require_windows(feature: str) -> None:
    if os.name != "nt":
        raise ToolError(f"{feature} is available on Windows only.")


def _import(module: str, hint: str):
    try:
        return __import__(module, fromlist=["*"])
    except ImportError as exc:
        raise ToolError(hint) from exc


@tool(category=Category.SYSTEM, risk=Risk.SAFE)
def apri_app(nome: str) -> str:
    """Open an application or a file by name or path.

    Use when the user asks to start a program. The name is resolved through
    PATH first, then handed to the Windows shell.

    Args:
        nome: executable name such as "notepad" or an absolute path.
    """
    _require_windows("Opening applications")
    target = nome.strip().strip('"')
    if not target:
        raise ToolError("The application name is empty.")

    executable = shutil.which(target)
    try:
        if executable:
            subprocess.Popen([executable], close_fds=True)
            return f"Started {Path(executable).name}."
        os.startfile(target)  # type: ignore[attr-defined]
        return f"Opened {target}."
    except OSError as exc:
        raise ToolError(f"Could not open {target}: {exc}") from exc


@tool(category=Category.SYSTEM, risk=Risk.CONFIRM)
def chiudi_app(nome: str) -> str:
    """Close a running application by process or window name.

    Use only when the user explicitly asks to close a program. Closing an app
    can lose unsaved work, which is why this tool requires confirmation.

    Args:
        nome: process name fragment such as "notepad".
    """
    psutil = _import("psutil", "psutil is not installed.")
    fragment = nome.strip().lower()
    if len(fragment) < 2:
        raise ToolError("Provide at least two characters of the process name.")

    closed: list[str] = []
    for process in psutil.process_iter(["name"]):
        try:
            name = (process.info.get("name") or "").lower()
            if fragment in name and name not in {"explorer.exe", "svchost.exe"}:
                process.terminate()
                closed.append(process.info.get("name") or name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not closed:
        raise ToolError(f"No running process matched '{nome}'.")
    time.sleep(0.3)
    return "Closed: " + ", ".join(sorted(set(closed)))


@tool(category=Category.SYSTEM, risk=Risk.SAFE)
def volume(azione: Literal["su", "giu", "muto", "imposta"], valore: int = 10) -> str:
    """Control the system output volume.

    Use for requests about volume or mute. Percent values are 0-100.

    Args:
        azione: one of "su", "giu", "muto", "imposta".
        valore: step for "su"/"giu" or target percent for "imposta".
    """
    _require_windows("Volume control")
    _import("comtypes", "comtypes is not installed.")
    pycaw = _import("pycaw.pycaw", "pycaw is not installed.")
    from ctypes import POINTER, cast

    from comtypes import CLSCTX_ALL

    interface = pycaw.AudioUtilities.GetSpeakers().Activate(
        pycaw.IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    )
    endpoint = cast(interface, POINTER(pycaw.IAudioEndpointVolume))
    current = endpoint.GetMasterVolumeLevelScalar()

    if azione == "muto":
        muted = bool(endpoint.GetMute())
        endpoint.SetMute(not muted, None)
        return "Muted." if not muted else "Unmuted."

    step = max(0, min(100, valore)) / 100
    if azione == "imposta":
        target = step
    elif azione == "su":
        target = min(1.0, current + step)
    else:
        target = max(0.0, current - step)
    endpoint.SetMasterVolumeLevelScalar(target, None)
    return f"Volume set to {round(target * 100)}%."


@tool(category=Category.SYSTEM, risk=Risk.SAFE)
def luminosita(valore: int) -> str:
    """Set the display brightness as a percentage.

    Use when the user asks to change screen brightness.

    Args:
        valore: brightness percentage from 0 to 100.
    """
    _require_windows("Brightness control")
    percent = max(0, min(100, int(valore)))
    script = (
        "$monitors = Get-CimInstance -Namespace root/wmi "
        "-ClassName WmiMonitorBrightnessMethods; "
        "$monitors | Invoke-CimMethod -MethodName WmiSetBrightness "
        f"-Arguments @{{Timeout = 1; Brightness = {percent}}} | Out-Null"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if completed.returncode != 0:
        raise ToolError("Brightness control is not supported on this display.")
    return f"Brightness set to {percent}%."


@tool(category=Category.SYSTEM, risk=Risk.SAFE)
def screenshot(percorso: str = "") -> str:
    """Capture the full screen and save it as a PNG.

    Use when the user asks for a screenshot. Leave the path empty to save in
    the Veyra data folder.

    Args:
        percorso: optional destination path ending in .png.
    """
    mss = _import("mss", "mss is not installed.")
    if percorso.strip():
        destination = Path(percorso).expanduser()
    else:
        folder = app_data_dir() / "screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / time.strftime("screen-%Y%m%d-%H%M%S.png")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with mss.mss() as capture:
            capture.shot(output=str(destination))
    except Exception as exc:
        raise ToolError(f"Screenshot failed: {exc}") from exc
    return f"Screenshot saved to {destination}."


@tool(category=Category.SYSTEM, risk=Risk.SAFE)
def stato_pc() -> str:
    """Report CPU, memory, disk and battery status.

    Use when the user asks how the computer is doing.
    """
    psutil = _import("psutil", "psutil is not installed.")
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home()))
    parts = [
        f"CPU {psutil.cpu_percent(interval=0.2):.0f}%",
        f"RAM {memory.used / 1024**3:.1f}/{memory.total / 1024**3:.1f} GB ({memory.percent:.0f}%)",
        f"disk {disk.used / 1024**3:.1f}/{disk.total / 1024**3:.1f} GB free",
    ]
    battery = getattr(psutil, "sensors_battery", lambda: None)()
    if battery is not None:
        parts.append(f"battery {battery.percent:.0f}%")
    return ", ".join(parts)


@tool(category=Category.SYSTEM, risk=Risk.SAFE)
def appunti(azione: Literal["leggi", "scrivi"], testo: str = "") -> str:
    """Read or write the Windows clipboard.

    Use when the user asks what is copied or wants text placed on the clipboard.

    Args:
        azione: "leggi" to read, "scrivi" to write.
        testo: text to copy when azione is "scrivi".
    """
    pyperclip = _import("pyperclip", "pyperclip is not installed.")
    if azione == "leggi":
        content = pyperclip.paste()
        if not content:
            return "The clipboard is empty."
        return content[:2000]
    if not testo:
        raise ToolError("No text was provided to copy.")
    pyperclip.copy(testo)
    return "Copied to the clipboard."


@tool(category=Category.SYSTEM, risk=Risk.SAFE)
def finestre() -> str:
    """List open windows with their titles.

    Use when the user asks which programs or windows are open.
    """
    _require_windows("Window listing")
    pywinauto = _import("pywinauto", "pywinauto is not installed.")
    try:
        desktop = pywinauto.Desktop(backend="uia")
        titles = [window.window_text() for window in desktop.windows() if window.window_text()]
    except Exception as exc:
        raise ToolError(f"Could not list windows: {exc}") from exc
    if not titles:
        return "No visible windows."
    return "; ".join(titles[:20])
