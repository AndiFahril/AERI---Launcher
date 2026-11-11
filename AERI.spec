# Windows x64 one-file package. Qt Widgets only; no WebEngine.
a = Analysis(['bootstrap.py'], pathex=[], binaries=[],
             datas=[('apps.json', '.'), ('settings.json', '.'), ('icons', 'icons'), ('assets', 'assets')],
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                       'PySide6.QtQml', 'PySide6.QtQuick', 'tkinter', 'numpy'],
             noarchive=False, optimize=0)
# Qt uses Windows' ICU API. Unrelated ICU DLLs on PATH (for example Poppler)
# export different symbols and must not shadow the Windows system libraries.
a.binaries = [entry for entry in a.binaries
              if entry[0].replace('\\', '/').split('/')[-1].lower()
              not in {'icuuc.dll', 'icuin.dll', 'icudt.dll'}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='AERI',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False, icon='assets/app.ico', version='version_info.txt')
