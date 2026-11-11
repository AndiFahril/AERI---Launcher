"""Read local Windows shortcuts and Store app identities; never installs software."""
import json,os,re,subprocess,sys
from pathlib import Path
from PySide6.QtCore import QThread,Signal

STORE_SCRIPT=r'''
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference='SilentlyContinue'
$packages=@{}
Get-AppxPackage | ForEach-Object {$packages[$_.PackageFamilyName]=$_.InstallLocation}
$shell=New-Object -ComObject Shell.Application
$identities=@{}
foreach($item in $shell.Namespace('shell:AppsFolder').Items()) {
  if($item.Path -match '^[A-Za-z0-9._-]+![A-Za-z0-9._-]+$'){$identities[$item.Path]=@{id=$item.Path;name=$item.Name}}
}
Get-StartApps | ForEach-Object {
  if($_.AppID -match '^[A-Za-z0-9._-]+![A-Za-z0-9._-]+$'){$identities[$_.AppID]=@{id=$_.AppID;name=$_.Name}}
}
$output=@(foreach($item in $identities.Values) {
  $id=$item.id
  if($id -notmatch '^[A-Za-z0-9._-]+![A-Za-z0-9._-]+$'){continue}
  $family,$appId=$id.Split('!',2);$icon='';$root=$packages[$family]
  if($root){
    try {
      [xml]$manifest=Get-Content -LiteralPath (Join-Path $root 'AppxManifest.xml') -Raw
      $node=$manifest.SelectNodes("//*[local-name()='Application']") | Where-Object {$_.Id -eq $appId} | Select-Object -First 1
      $visual=$node.SelectSingleNode("*[local-name()='VisualElements']")
      $relative=$visual.GetAttribute('Square44x44Logo')
      if($relative -and $relative -notlike 'ms-resource:*'){
        $candidate=Join-Path $root $relative
        if(Test-Path -LiteralPath $candidate){$icon=$candidate}
        else {
          $dir=[IO.Path]::GetDirectoryName($candidate);$stem=[IO.Path]::GetFileNameWithoutExtension($candidate)
          $file=Get-ChildItem -LiteralPath $dir -Filter ($stem+'*.png') | Sort-Object Length -Descending | Select-Object -First 1
          if($file){$icon=$file.FullName}
        }
      }
    }catch{}
  }
  @{name=$item.name;id=$id;icon_path=$icon}
})
ConvertTo-Json -InputObject $output -Compress -Depth 4
'''

def default_roots():
    result=[]
    for key in ('APPDATA','PROGRAMDATA'):
        if os.environ.get(key):result.append(Path(os.environ[key])/'Microsoft/Windows/Start Menu/Programs')
    from PySide6.QtCore import QStandardPaths
    result.append(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)))
    return result

def store_entries(rows):
    result=[]
    if isinstance(rows,dict):rows=[rows]
    if not isinstance(rows,list):return result
    for row in rows:
        if not isinstance(row,dict):continue
        identity=row.get('id','');name=row.get('name','')
        if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9._-]+![A-Za-z0-9._-]+',identity):continue
        if not isinstance(name,str) or not name.strip():continue
        icon=row.get('icon_path','')
        result.append({'name':name.strip(),'type':'app','path':str(Path(os.environ.get('WINDIR','C:/Windows'))/'explorer.exe'),
            'args':['shell:AppsFolder\\'+identity],'category':'Aplikasi','icon':'auto' if icon else 'initial',
            'icon_path':icon if isinstance(icon,str) else '', 'source':'Aplikasi Windows'})
    return result

def discover_apps(roots=None,include_store=True,interrupted=lambda:False):
    entries=[];seen=set()
    for root in default_roots() if roots is None else roots:
        if interrupted():return entries
        root=Path(root)
        if not root.is_dir():continue
        for directory,folders,files in os.walk(root,followlinks=False):
            if interrupted():return entries
            for name in files:
                path=Path(directory)/name
                if path.suffix.casefold() not in ('.lnk','.url'):continue
                identity=str(path).casefold()
                if identity in seen:continue
                seen.add(identity)
                web=any('chrome apps' in p.casefold() for p in path.parts)
                entries.append({'name':path.stem,'type':'app','path':str(path),
                    'args':[],'category':'Aplikasi web' if web else 'Aplikasi','icon':'auto',
                    'source':'Web Chrome' if web else 'Shortcut Windows'})
    if include_store and sys.platform=='win32' and not interrupted():
        try:
            response=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',STORE_SCRIPT],
                capture_output=True,text=True,encoding='utf-8-sig',timeout=10,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if response.returncode==0:entries.extend(store_entries(json.loads(response.stdout)))
        except (OSError,subprocess.TimeoutExpired,ValueError):pass
    return sorted(entries,key=lambda item:(item['name'].casefold(),item['path'].casefold()))

class DiscoveryWorker(QThread):
    found=Signal(list)
    def run(self):
        try:values=discover_apps(interrupted=self.isInterruptionRequested)
        except Exception:values=[]
        if not self.isInterruptionRequested():self.found.emit(values)
    def shutdown(self):self.requestInterruption();self.wait(12000)
