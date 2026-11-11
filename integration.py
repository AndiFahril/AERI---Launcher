"""Current-user desktop/startup links. No administrator or registry writes."""
import os
from pathlib import Path
import subprocess
import sys
from PySide6.QtCore import QStandardPaths

def executable():
    if not getattr(sys,'frozen',False):
        raise ValueError('Pemasangan dan startup tersedia pada paket EXE.')
    return Path(sys.executable).resolve()

def startup_link():
    return Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/Startup/AERI.lnk'

def _link(path,target,arguments='',remove=False):
    env=os.environ.copy()
    env.update(FL_LINK_PATH=str(path),FL_LINK_TARGET=str(target),FL_LINK_ARGS=arguments)
    icon=Path(target).parent/'AERI.ico'
    env['FL_LINK_ICON']=str(icon if icon.is_file() else target)
    if remove:
        script="if(Test-Path -LiteralPath $env:FL_LINK_PATH){Remove-Item -LiteralPath $env:FL_LINK_PATH -ErrorAction Stop}"
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        script=("$ErrorActionPreference='Stop';$shell=New-Object -ComObject WScript.Shell;"
                "$link=$shell.CreateShortcut($env:FL_LINK_PATH);"
                "$link.TargetPath=$env:FL_LINK_TARGET;$link.Arguments=$env:FL_LINK_ARGS;"
                "$link.WorkingDirectory=[IO.Path]::GetDirectoryName($env:FL_LINK_TARGET);"
                "$link.IconLocation=$env:FL_LINK_ICON+',0';$link.Save()")
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
        env=env,capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise OSError('Tidak dapat memperbarui shortcut Windows: '+result.stderr.strip()[:300])

def set_autostart(enabled):
    _link(startup_link(),executable(),'--background',remove=not enabled)

def desktop_link(target=None):
    target=Path(target) if target else executable()
    path=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))/'AERI.lnk'
    _link(path,target)
    return path
