"""Install a private copy plus one desktop link; preserve existing user data."""
from pathlib import Path
import os
import shutil
import sys
from storage import app_directory,bundled_file
from integration import desktop_link,executable

def copy_install(source_exe,source_data,destination,resources=None):
    source_exe=Path(source_exe).resolve()
    source_data=Path(source_data).resolve()
    destination=Path(destination).resolve()
    resources=Path(resources or source_data).resolve()
    destination.mkdir(parents=True,exist_ok=True)
    target=destination/'AERI.exe'
    if target.resolve()!=source_exe:
        shutil.copy2(source_exe,target)
    icon=resources/'assets/app.ico'
    if icon.is_file() and icon.resolve()!=(destination/'AERI.ico').resolve():
        shutil.copy2(icon,destination/'AERI.ico')
    for name in ('apps.json','settings.json'):
        if not (destination/name).exists():
            source=source_data/name
            if not source.is_file():source=resources/name
            shutil.copy2(source,destination/name)
    for folder in (resources/'icons',source_data/'icons'):
        if folder.is_dir():
            for image in folder.iterdir():
                if image.is_file():
                    dest=destination/'icons'/image.name
                    dest.parent.mkdir(exist_ok=True)
                    if not dest.exists():shutil.copy2(image,dest)
    return target

def install_application(destination=None):
    destination=Path(destination) if destination else Path(os.environ['LOCALAPPDATA'])/'AERI'
    target=copy_install(executable(),app_directory(),destination,
                        Path(getattr(sys,'_MEIPASS',app_directory())))
    link=desktop_link(target)
    return target,link
