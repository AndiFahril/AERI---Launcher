from __future__ import annotations
import os, re, subprocess,sys,ctypes,json,uuid,time,ntpath
from ctypes import wintypes
from pathlib import Path
from urllib.parse import urlparse
from PySide6.QtCore import QUrl,QTimer,QCoreApplication
from PySide6.QtGui import QDesktopServices
from storage import expand_path, resolve_executable, resolve_local_path

# Reuse belongs to the launch layer, so mouse clicks and local hotkeys share it.
_LINK_CACHE={}
_WINDOW_BINDINGS={}
_STARTING={}

def _path_key(value):
    value=ntpath.normcase(ntpath.normpath(expand_path(str(value))))
    if ntpath.basename(value) in ('chrome_proxy.exe','msedge_proxy.exe'):
        value=ntpath.join(ntpath.dirname(value),ntpath.basename(value).replace('_proxy',''))
    return value

def _item_key(item):
    path=expand_path(item['path']);revision=0
    if item['type']=='app' and Path(path).suffix.casefold()=='.lnk':
        try:revision=Path(resolve_executable(path) or path).stat().st_mtime_ns
        except OSError:pass
    return (item['type'],_path_key(path),tuple(item.get('args',[])),revision)

def _shell_json(script,env=None):
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
            "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);$ErrorActionPreference='Stop';"+script],
            env=env,capture_output=True,text=True,encoding='utf-8-sig',timeout=4,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return json.loads(result.stdout) if result.returncode==0 else None
    except (OSError,ValueError,subprocess.TimeoutExpired):return None

def _split_command(command):
    if not command:return []
    shell=ctypes.WinDLL('shell32');kernel=ctypes.WinDLL('kernel32')
    shell.CommandLineToArgvW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype=ctypes.POINTER(wintypes.LPWSTR)
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    count=ctypes.c_int();pointer=shell.CommandLineToArgvW(command,ctypes.byref(count))
    if not pointer:return []
    try:return [pointer[i] for i in range(count.value)]
    finally:kernel.LocalFree(pointer)

def _link_details(path):
    try:key=(str(path),Path(path).stat().st_mtime_ns)
    except OSError:return {}
    if key in _LINK_CACHE:return _LINK_CACHE[key]
    env=os.environ.copy();env['AERI_LINK']=str(path)
    value=_shell_json("$w=New-Object -ComObject WScript.Shell;$l=$w.CreateShortcut($env:AERI_LINK);"
        "$s=New-Object -ComObject Shell.Application;$p=[IO.Path]::GetDirectoryName($env:AERI_LINK);"
        "$f=$s.Namespace($p).ParseName([IO.Path]::GetFileName($env:AERI_LINK));"
        "@{target=$l.TargetPath;arguments=$l.Arguments;aumid=$f.ExtendedProperty('System.AppUserModel.ID')}|ConvertTo-Json -Compress",env)
    value=value if isinstance(value,dict) else {}
    if len(_LINK_CACHE)>128:_LINK_CACHE.clear()
    _LINK_CACHE[key]=value;return value

def _associated_executable(scheme):
    try:
        api=ctypes.WinDLL('shlwapi')
        api.AssocQueryStringW.argtypes=[wintypes.DWORD,ctypes.c_int,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        api.AssocQueryStringW.restype=ctypes.c_long
        output=ctypes.create_unicode_buffer(32768);length=wintypes.DWORD(len(output))
        if api.AssocQueryStringW(0x1000,2,scheme,None,output,ctypes.byref(length))>=0:return output.value
    except (OSError,AttributeError,ctypes.ArgumentError):pass
    return ''

class _GUID(ctypes.Structure):
    _fields_=[('a',wintypes.DWORD),('b',wintypes.WORD),('c',wintypes.WORD),('d',ctypes.c_ubyte*8)]
class _PROPERTYKEY(ctypes.Structure):
    _fields_=[('fmtid',_GUID),('pid',wintypes.DWORD)]
class _PVVALUE(ctypes.Union):
    _fields_=[('pointer',ctypes.c_void_p),('storage',ctypes.c_ubyte*(16 if ctypes.sizeof(ctypes.c_void_p)==8 else 8))]
class _PROPVARIANT(ctypes.Structure):
    _fields_=[('vt',wintypes.WORD),('r1',wintypes.WORD),('r2',wintypes.WORD),('r3',wintypes.WORD),('value',_PVVALUE)]

def _window_properties(hwnd):
    """Read identity/relaunch metadata, never infer a Chrome profile from its PID."""
    result={};store=ctypes.c_void_p();release=None;initialized=False
    ole=ctypes.WinDLL('ole32')
    try:
        ole.CoInitializeEx.argtypes=[ctypes.c_void_p,wintypes.DWORD];ole.CoInitializeEx.restype=ctypes.c_long
        initialized=ole.CoInitializeEx(None,2)>=0
        shell=ctypes.WinDLL('shell32')
        shell.SHGetPropertyStoreForWindow.argtypes=[wintypes.HWND,ctypes.POINTER(_GUID),ctypes.POINTER(ctypes.c_void_p)]
        shell.SHGetPropertyStoreForWindow.restype=ctypes.c_long
        iid=_GUID.from_buffer_copy(uuid.UUID('886d8eeb-8cf2-4446-8d02-cdba1dbdcf99').bytes_le)
        if shell.SHGetPropertyStoreForWindow(hwnd,ctypes.byref(iid),ctypes.byref(store))<0:return result
        table=ctypes.cast(store,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        release=ctypes.WINFUNCTYPE(wintypes.ULONG,ctypes.c_void_p)(table[2])
        get=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,ctypes.POINTER(_PROPERTYKEY),ctypes.POINTER(_PROPVARIANT))(table[5])
        ole.PropVariantClear.argtypes=[ctypes.POINTER(_PROPVARIANT)]
        fmtid=_GUID.from_buffer_copy(uuid.UUID('9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3').bytes_le)
        for name,pid in (('aumid',5),('command',2)):
            key=_PROPERTYKEY(fmtid,pid);value=_PROPVARIANT()
            try:
                if get(store,ctypes.byref(key),ctypes.byref(value))>=0 and value.vt in (8,31) and value.value.pointer:
                    result[name]=ctypes.wstring_at(value.value.pointer)
            finally:ole.PropVariantClear(ctypes.byref(value))
    except (OSError,AttributeError,ValueError,ctypes.ArgumentError):pass
    finally:
        if release is not None:release(store)
        if initialized:ole.CoUninitialize()
    return result

def _windows():
    if sys.platform!='win32':return []
    user=ctypes.WinDLL('user32');kernel=ctypes.WinDLL('kernel32');dwm=ctypes.WinDLL('dwmapi')
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    user.IsWindowVisible.argtypes=[wintypes.HWND];user.GetWindow.argtypes=[wintypes.HWND,wintypes.UINT];user.GetWindow.restype=wintypes.HWND
    user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    user.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    get_style=getattr(user,'GetWindowLongPtrW',user.GetWindowLongW)
    get_style.argtypes=[wintypes.HWND,ctypes.c_int];get_style.restype=ctypes.c_ssize_t
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    dwm.DwmGetWindowAttribute.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
    output=[];processes={}
    def visit(hwnd,param):
        try:
            if not user.IsWindowVisible(hwnd) or user.GetWindow(hwnd,4) or get_style(hwnd,-20)&(0x80|0x08000000):return True
            title=ctypes.create_unicode_buffer(2048);cls=ctypes.create_unicode_buffer(128)
            user.GetWindowTextW(hwnd,title,len(title));user.GetClassNameW(hwnd,cls,len(cls))
            if not title.value or cls.value in ('Progman','WorkerW','Shell_TrayWnd','Shell_SecondaryTrayWnd'):return True
            cloaked=wintypes.DWORD()
            if dwm.DwmGetWindowAttribute(hwnd,14,ctypes.byref(cloaked),ctypes.sizeof(cloaked))>=0 and cloaked.value:return True
            pid=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if pid.value not in processes:
                handle=kernel.OpenProcess(0x1000,False,pid.value);image=''
                if handle:
                    try:
                        buffer=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(buffer))
                        if kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(size)):image=buffer.value
                    finally:kernel.CloseHandle(handle)
                processes[pid.value]=image
            output.append(dict(hwnd=int(hwnd),pid=pid.value,exe=processes[pid.value],title=title.value,
                window_class=cls.value,**_window_properties(hwnd)))
        except (OSError,ValueError,AttributeError,ctypes.ArgumentError):pass
        return True
    callback=callback_type(visit);user.EnumWindows(callback,0)
    return output

def _activate_window(hwnd):
    user=ctypes.WinDLL('user32')
    user.GetLastActivePopup.argtypes=[wintypes.HWND];user.GetLastActivePopup.restype=wintypes.HWND
    user.IsWindowVisible.argtypes=[wintypes.HWND];user.IsIconic.argtypes=[wintypes.HWND]
    user.ShowWindowAsync.argtypes=[wintypes.HWND,ctypes.c_int]
    user.SetForegroundWindow.argtypes=[wintypes.HWND];user.SetForegroundWindow.restype=wintypes.BOOL
    user.GetForegroundWindow.restype=wintypes.HWND
    popup=user.GetLastActivePopup(hwnd)
    if popup and user.IsWindowVisible(popup):hwnd=popup
    if user.IsIconic(hwnd):user.ShowWindowAsync(hwnd,9)
    return bool(user.SetForegroundWindow(hwnd) or user.GetForegroundWindow()==hwnd)

def _switch(args,name):
    prefix=name+'='
    for index,arg in enumerate(args):
        if arg.startswith(prefix):return arg[len(prefix):]
        if arg==name and index+1<len(args):return args[index+1]
    return ''

def _target(item):
    kind=item['type'];path=item['path'];args=list(item.get('args',[]));aumid=''
    if kind=='folder':return dict(kind='folder',path=str(resolve_local_path(path)))
    if kind=='website':return dict(kind='website',url=path,name=item['name'],exe=_associated_executable(urlparse(path).scheme))
    if path.endswith(':'):return dict(kind='protocol',scheme=path[:-1],exe=_associated_executable(path[:-1]))
    path=resolve_executable(path) or expand_path(path)
    if Path(path).suffix.casefold()=='.lnk':
        details=_link_details(path);path=details.get('target') or '';aumid=details.get('aumid') or ''
        args=_split_command('aeri '+(details.get('arguments') or ''))[1:]
    if Path(path).suffix.casefold()=='.url':return dict(kind='unknown')
    if '!' in aumid:return dict(kind='store',aumid=aumid)
    if args and args[0].casefold().startswith('shell:appsfolder\\'):
        return dict(kind='store',aumid=args[0].split('\\',1)[1])
    return dict(kind='app',exe=path,args=args,aumid=aumid)

def _browser_match(window,target):
    args=target['args'];identity=window.get('aumid','').casefold()
    relaunch=_split_command(window.get('command',''))[1:]
    profile=_switch(args,'--profile-directory');data=_switch(args,'--user-data-dir')
    app_id=_switch(args,'--app-id');url=_switch(args,'--app')
    private_flags={'--incognito','--inprivate','-private-window'}
    if bool(set(args)&private_flags)!=bool(set(relaunch)&private_flags):return False
    other=[];skip=False
    flags=('--profile-directory','--app-id','--app','--user-data-dir')
    for arg in args:
        if skip:skip=False;continue
        if arg in flags:skip=True;continue
        if not any(arg.startswith(flag+'=') for flag in flags):other.append(arg)
    if other:return bool(relaunch and relaunch==args)
    if relaunch:
        if profile and (_switch(relaunch,'--profile-directory') or 'Default').casefold()!=profile.casefold():return False
        if data and _path_key(_switch(relaunch,'--user-data-dir'))!=_path_key(data):return False
        if app_id and _switch(relaunch,'--app-id'):return _switch(relaunch,'--app-id')==app_id
        if url:return _switch(relaunch,'--app')==url
        if not app_id:
            if _switch(relaunch,'--app-id') or _switch(relaunch,'--app'):return False
            if not profile and not data:return True
    if not identity:return False
    if data:return False  # Never confuse two custom user-data directories with the same basename.
    default_data=not data
    suffix=''
    if data or profile and profile.casefold()!='default':
        suffix='.'+re.sub(r'[^A-Za-z0-9.]','',ntpath.basename(data or 'User Data')+'.'+(profile or 'Default')).casefold()
    if suffix and not identity.endswith(suffix):return False
    browser_id=identity[:-len(suffix)] if suffix else identity
    if not profile and not data:browser_id=re.sub(r'\.userdata\.[^.]+$','',browser_id)
    if profile.casefold()=='default' and default_data and re.search(r'\.userdata\.[^.]+$',identity):return False
    if app_id:return browser_id.endswith('._crx_'+app_id.casefold())
    if url:
        # Exact URL metadata or an observed launch is required, especially for account-specific Drive URLs.
        return False
    return bool(re.fullmatch(r'(chrome(?:beta|dev|canary)?|chromium|msedge)(?:\.[a-z0-9]{8,})?',browser_id))

def _folder_windows():
    value=_shell_json("$s=New-Object -ComObject Shell.Application;"
        "$r=@(foreach($w in $s.Windows()){try{@{hwnd=[long]$w.HWND;path=$w.Document.Folder.Self.Path}}catch{}});"
        "ConvertTo-Json -InputObject $r -Compress")
    if isinstance(value,dict):return [value]
    return value if isinstance(value,list) else []

def _matches(window,target):
    kind=target['kind'];identity=window.get('aumid','').casefold()
    if kind=='store':return identity==target['aumid'].casefold()
    if kind=='protocol':
        exe=target.get('exe','')
        if exe and ntpath.basename(exe).casefold() not in ('rundll32.exe','explorer.exe','applicationframehost.exe'):
            return _path_key(window.get('exe',''))==_path_key(exe)
        scheme=re.escape(target['scheme'].casefold())
        return bool(re.search(r'(?:^|[._!])'+scheme+r'(?:desktop)?(?:[._!]|$)',identity))
    if kind=='website':
        parsed=urlparse(target['url'])
        if re.search(r'/u/\d+(?:/|$)',parsed.path) or 'authuser=' in parsed.query:return False
        if not target.get('exe') or _path_key(window.get('exe',''))!=_path_key(target['exe']):return False
        name=re.sub(r'\W','',target.get('name','').casefold())
        return len(name)>=4 and name in re.sub(r'\W','',window.get('title','').casefold())
    if kind!='app':return False
    if target.get('aumid') and identity!=target['aumid'].casefold():return False
    if not target.get('exe') or _path_key(window.get('exe',''))!=_path_key(target['exe']):return False
    if ntpath.basename(target['exe']).casefold() in ('chrome.exe','chrome_proxy.exe','msedge.exe','msedge_proxy.exe','chromium.exe'):
        return _browser_match(window,target)
    args=target.get('args',[])
    return not args or _split_command(window.get('command',''))[1:]==args

def _bound_window(key,windows):
    previous=_WINDOW_BINDINGS.get(key)
    if previous:
        for window in windows:
            if all(window.get(field)==previous.get(field) for field in ('hwnd','pid','exe','aumid')):return window
        _WINDOW_BINDINGS.pop(key,None)
    return None

def activate_existing(item,windows=None):
    if windows is None:windows=_windows()
    if not windows:return False
    key=_item_key(item);target=_target(item);match=None
    # Folder locations and ordinary browser tabs can change within the same HWND.
    if target['kind'] not in ('folder','website'):match=_bound_window(key,windows)
    if match is None and target['kind']=='folder':
        handles={row.get('hwnd') for row in _folder_windows() if _path_key(row.get('path',''))==_path_key(target['path'])}
        match=next((w for w in windows if w['hwnd'] in handles),None)
    if match is None:match=next((w for w in windows if _matches(w,target)),None)
    if match is None:return False
    if not _activate_window(match['hwnd']):
        raise OSError('Aplikasi sudah terbuka, tetapi Windows belum mengizinkan pemindahan fokus. Pilih jendelanya melalui taskbar.')
    _STARTING.pop(key,None);return True

def _schedule_reuse_capture(item,before):
    if sys.platform!='win32' or QCoreApplication.instance() is None:return
    key=_item_key(item);token=time.monotonic()+5;_STARTING[key]=token
    def capture():
        if _STARTING.get(key)!=token:return
        windows=_windows();target=_target(item)
        candidates=[w for w in windows if _matches(w,target)]
        if not candidates and target.get('exe') and target['kind']=='app':
            candidates=[w for w in windows if w['hwnd'] not in before and _path_key(w.get('exe',''))==_path_key(target['exe'])]
        ready=len(candidates)==1 and target['kind'] not in ('website','folder')
        if ready and ntpath.basename(target.get('exe','')).casefold() in ('chrome.exe','chrome_proxy.exe','msedge.exe','msedge_proxy.exe','chromium.exe'):
            ready=bool(candidates[0].get('aumid') or candidates[0].get('command'))
        if ready:
            _WINDOW_BINDINGS[key]=candidates[0];_STARTING.pop(key,None)
        elif time.monotonic()>=token:_STARTING.pop(key,None)
    for delay in (250,750,1500,3000,5100):QTimer.singleShot(delay,capture)

def open_shortcut(item):
    kind, path = item['type'], item['path']
    if kind == 'website':
        parsed = urlparse(path)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise ValueError('URL website tidak valid.')
    elif kind == 'folder':
        folder = resolve_local_path(path)
        if not folder.is_dir():
            raise FileNotFoundError(str(folder))
    elif kind=='app' and path.endswith(':'):
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9+.-]{1,}:', path):
            raise ValueError('Protokol aplikasi tidak valid.')
    elif kind=='app':
        target = resolve_executable(path)
        if not target:
            raise FileNotFoundError(expand_path(path))
        args = item.get('args', [])
        if Path(target).suffix.lower() in {'.lnk', '.url'}:
            if args:
                raise ValueError('Argumen tambahan tidak didukung pada .lnk / .url.')
    else:raise ValueError('Jenis shortcut tidak didukung.')

    windows=_windows() if sys.platform=='win32' else []
    if activate_existing(item,windows):return
    key=_item_key(item)
    if _STARTING.get(key,0)>time.monotonic():return
    _STARTING.pop(key,None)
    if kind=='website':
        if not QDesktopServices.openUrl(QUrl(path)):raise OSError('Browser tidak dapat dibuka.')
    elif kind=='folder':os.startfile(str(folder))
    elif path.endswith(':'):os.startfile(path)
    elif Path(target).suffix.lower() in {'.lnk','.url'}:os.startfile(target)
    else:subprocess.Popen([target,*args],shell=False)
    _schedule_reuse_capture(item,{window['hwnd'] for window in windows})
