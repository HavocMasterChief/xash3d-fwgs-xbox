# build_uwp.ps1 - build Xash3D FWGS + hlsdk-portable as a sideloadable
# UWP package for Xbox Series Dev Mode.
#
# Runs on a GitHub Actions windows-2022 runner (VS 2022 with the UWP workload).
# Output: artifacts/Xash3DXbox-x64.zip containing the signed .appx, the
# signing certificate and the VCLibs framework package it depends on.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Root      = (Get-Location).Path
$Work      = Join-Path $Root 'build-uwp'
$Pkg       = Join-Path $Work 'pkg'
$Artifacts = Join-Path $Root 'artifacts'

$SdlVersion  = if ($env:SDL_VERSION)  { $env:SDL_VERSION }  else { '2.32.10' }
$HlsdkRepo   = if ($env:HLSDK_REPO)   { $env:HLSDK_REPO }   else { 'https://github.com/HavocMasterChief/hlsdk-portable-xbox' }
$HlsdkBranch = if ($env:HLSDK_BRANCH) { $env:HLSDK_BRANCH } else { 'xbox' }
$Publisher   = 'CN=HavocMasterChief'
$RunNumber   = if ($env:GITHUB_RUN_NUMBER) { [int]$env:GITHUB_RUN_NUMBER } else { 0 }
$Version     = "0.1.$RunNumber.0"
$GameDir     = 'HalfLife' # base game folder, in LocalState and in the package

function Step($name) { Write-Host ""; Write-Host "==================== $name ====================" }

function Run {
	param([string]$Exe, [string[]]$ArgList)
	Write-Host "> $Exe $($ArgList -join ' ')"
	& $Exe @ArgList
	if ($LASTEXITCODE -ne 0) { throw "FAILED ($LASTEXITCODE): $Exe $($ArgList -join ' ')" }
}

New-Item -ItemType Directory -Force -Path $Work, $Artifacts | Out-Null

# ---------------------------------------------------------------------------
Step 'Locate toolchain'
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Visual Studio with C++ tools not found' }
$msbuild  = Join-Path $vs 'MSBuild\Current\Bin\MSBuild.exe'
$vcTools  = Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') | Sort-Object Name -Descending | Select-Object -First 1
$storeLib = Join-Path $vcTools.FullName 'lib\x64\store'
$dumpbin  = Join-Path $vcTools.FullName 'bin\Hostx64\x64\dumpbin.exe'
$sdkBin   = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Directory |
	Where-Object Name -match '^10\.' | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
$makeappx = Join-Path $sdkBin.FullName 'x64\makeappx.exe'
$signtool = Join-Path $sdkBin.FullName 'x64\signtool.exe'
Write-Host "VS:        $vs"
Write-Host "MSVC:      $($vcTools.Name)"
Write-Host "Store CRT: $storeLib (exists: $(Test-Path $storeLib))"
Write-Host "WinSDK:    $($sdkBin.Name)"
if (-not (Test-Path $storeLib)) { throw 'MSVC store (UWP) libraries missing - UWP workload not installed?' }

# ---------------------------------------------------------------------------
Step "SDL2 $SdlVersion for UWP"
$sdlSrc = Join-Path $Work 'SDL2'
if (-not (Test-Path $sdlSrc)) {
	Run git @('clone', '--depth', '1', '-b', "release-$SdlVersion", 'https://github.com/libsdl-org/SDL.git', $sdlSrc)
}
Run $msbuild @((Join-Path $sdlSrc 'VisualC-WinRT\SDL-UWP.vcxproj'), '/m', '/nologo', '/v:minimal',
	'/p:Configuration=Release', '/p:Platform=x64', '/p:PlatformToolset=v143')

$sdlDll = Get-ChildItem (Join-Path $sdlSrc 'VisualC-WinRT') -Recurse -Filter 'SDL2.dll' | Select-Object -First 1
$sdlLib = Get-ChildItem (Join-Path $sdlSrc 'VisualC-WinRT') -Recurse -Filter 'SDL2.lib' | Select-Object -First 1
if (-not $sdlDll -or -not $sdlLib) { throw 'SDL2 UWP build produced no SDL2.dll/SDL2.lib' }
Write-Host "SDL2.dll: $($sdlDll.FullName)"

# layout expected by waf's -s option: include/ and lib/x64/
$sdlSdk = Join-Path $Work 'SDL2_UWP'
New-Item -ItemType Directory -Force -Path (Join-Path $sdlSdk 'include'), (Join-Path $sdlSdk 'lib\x64') | Out-Null
Copy-Item (Join-Path $sdlSrc 'include\*') (Join-Path $sdlSdk 'include') -Recurse -Force
Copy-Item $sdlLib.FullName, $sdlDll.FullName (Join-Path $sdlSdk 'lib\x64') -Force

# ---------------------------------------------------------------------------
Step 'Engine (waf, --enable-uwp)'
# Xbox-only changes to submodules are kept as patches so the submodules stay pristine
foreach ($patch in Get-ChildItem (Join-Path $Root 'uwp\patches') -Filter '*.patch' -ErrorAction SilentlyContinue) {
	$sub = switch -Wildcard ($patch.Name) { 'mainui-*' { '3rdparty\mainui' } default { $null } }
	if (-not $sub) { throw "Don't know which submodule $($patch.Name) is for" }
	Run git @('-C', (Join-Path $Root $sub), 'apply', '--whitespace=nowarn', $patch.FullName)
	Write-Host "Applied $($patch.Name) to $sub"
}
$engineOut = Join-Path $Work 'engine-install'
try {
	Run "$Root\waf.bat" @('configure', '-s', $sdlSdk, '-T', 'release', '-8', '--enable-uwp',
		'--uwp-store-libpath', $storeLib, '--disable-werror', '--gamedir', $GameDir, '-o', (Join-Path $Work 'engine-build'))
} catch {
	Write-Host '---------- tail of waf config.log ----------'
	Get-Content (Join-Path $Work 'engine-build\config.log') -Tail 120 | ForEach-Object { Write-Host $_ }
	throw
}
Run "$Root\waf.bat" @('build', '-k')
Run "$Root\waf.bat" @('install', "--destdir=$engineOut")

# ---------------------------------------------------------------------------
Step "Game code ($HlsdkRepo @ $HlsdkBranch)"
$hlsdk = Join-Path $Work 'hlsdk'
if (-not (Test-Path $hlsdk)) {
	Run git @('clone', '--depth', '1', '--recurse-submodules', '--shallow-submodules', '-b', $HlsdkBranch, $HlsdkRepo, $hlsdk)
}
$hlsdkBuild = Join-Path $Work 'hlsdk-build'
Run cmake @('-S', $hlsdk, '-B', $hlsdkBuild, '-G', 'Visual Studio 17 2022', '-A', 'x64',
	'-DCMAKE_SYSTEM_NAME=WindowsStore', '-DCMAKE_SYSTEM_VERSION=10.0',
	'-D64BIT=ON', '-DGOLDSOURCE_SUPPORT=OFF')
Run cmake @('--build', $hlsdkBuild, '--config', 'Release', '--parallel')

# ---------------------------------------------------------------------------
Step 'UWP host executable'
$hostBuild = Join-Path $Work 'host-build'
Run cmake @('-S', (Join-Path $Root 'uwp\host'), '-B', $hostBuild, '-G', 'Visual Studio 17 2022', '-A', 'x64',
	'-DCMAKE_SYSTEM_NAME=WindowsStore', '-DCMAKE_SYSTEM_VERSION=10.0',
	"-DSDL2_SOURCE_DIR=$sdlSrc", "-DSDL2_LIBRARY=$($sdlLib.FullName)")
# only the .exe is used, packaging is done below with MakeAppx
Run cmake @('--build', $hostBuild, '--config', 'Release', '--',
	'/p:AppxPackageSigningEnabled=false', '/p:GenerateAppxPackageOnBuild=false')
$hostExe = Get-ChildItem $hostBuild -Recurse -Filter 'xash3d_uwp.exe' |
	Where-Object { $_.FullName -notmatch '\\AppX\\' } | Select-Object -First 1
if (-not $hostExe) { $hostExe = Get-ChildItem $hostBuild -Recurse -Filter 'xash3d_uwp.exe' | Select-Object -First 1 }
if (-not $hostExe) { throw 'host build produced no xash3d_uwp.exe' }

# ---------------------------------------------------------------------------
Step 'Package layout'
if (Test-Path $Pkg) { Remove-Item $Pkg -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Pkg | Out-Null

Copy-Item (Join-Path $Root 'uwp\package\Assets') $Pkg -Recurse
(Get-Content (Join-Path $Root 'uwp\package\AppxManifest.xml') -Raw).Replace('@VERSION@', $Version) |
	Set-Content (Join-Path $Pkg 'AppxManifest.xml') -Encoding UTF8

Copy-Item $hostExe.FullName $Pkg
Copy-Item $sdlDll.FullName $Pkg

# every DLL the engine install produced goes to the package root, where
# LoadPackagedLibrary looks for it; game data dirs (valve/extras.pk3) keep their layout
Get-ChildItem $engineOut -Recurse -File | ForEach-Object {
	if ($_.Extension -eq '.dll') {
		Copy-Item $_.FullName $Pkg -Force
	} elseif ($_.Extension -in '.pk3', '.cfg', '.txt', '.lst', '.rc', '.gam') {
		$rel = $_.FullName.Substring($engineOut.Length).TrimStart('\', '/')
		$dest = Join-Path $Pkg $rel
		New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
		Copy-Item $_.FullName $dest -Force
	}
}
# game libraries mirror the LocalState layout: <game>\dlls (server), <game>\cl_dlls (client)
New-Item -ItemType Directory -Force -Path (Join-Path $Pkg "$GameDir\dlls"), (Join-Path $Pkg "$GameDir\cl_dlls") | Out-Null
Get-ChildItem $hlsdkBuild -Recurse -Filter '*.dll' | Where-Object { $_.FullName -match '\\Release\\' } | ForEach-Object {
	$sub = if ($_.Name -like 'client*') { 'cl_dlls' } else { 'dlls' }
	Copy-Item $_.FullName (Join-Path $Pkg "$GameDir\$sub") -Force
}

Write-Host 'Package contents:'
Get-ChildItem $Pkg -Recurse -File | ForEach-Object { Write-Host "  $($_.FullName.Substring($Pkg.Length + 1))  ($($_.Length) bytes)" }

Step 'Imported DLLs (anything from user32/gdi32/etc. will not load on Xbox)'
Get-ChildItem $Pkg -File -Recurse | Where-Object { $_.Extension -in '.dll', '.exe' } | ForEach-Object {
	Write-Host "--- $($_.Name)"
	& $dumpbin /nologo /dependents $_.FullName | Where-Object { $_ -match '\.dll' } | ForEach-Object { Write-Host "     $($_.Trim())" }
}

# ---------------------------------------------------------------------------
Step 'Pack and sign'
$appx = Join-Path $Work 'Xash3DXbox-x64.appx'
Run $makeappx @('pack', '/d', $Pkg, '/p', $appx, '/o')

$pfx = Join-Path $Work 'Xash3DXbox.pfx'
$cer = Join-Path $Work 'Xash3DXbox.cer'
$pfxPass = ConvertTo-SecureString -String 'xash3d' -Force -AsPlainText
$cert = New-SelfSignedCertificate -Type Custom -Subject $Publisher -KeyUsage DigitalSignature `
	-FriendlyName 'Xash3D Xbox sideload' -CertStoreLocation 'Cert:\CurrentUser\My' `
	-TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3', '2.5.29.19={text}')
Export-PfxCertificate -Cert $cert -FilePath $pfx -Password $pfxPass | Out-Null
Export-Certificate -Cert $cert -FilePath $cer | Out-Null
Run $signtool @('sign', '/fd', 'SHA256', '/f', $pfx, '/p', 'xash3d', $appx)

# ---------------------------------------------------------------------------
Step 'Defender scan (diagnostic only, never fails the build)'
try {
	$mp = Get-ChildItem "$env:ProgramData\Microsoft\Windows Defender\Platform" -Directory -ErrorAction Stop |
		Sort-Object Name -Descending | Select-Object -First 1
	$mpcmd = if ($mp) { Join-Path $mp.FullName 'MpCmdRun.exe' } else { "$env:ProgramFiles\Windows Defender\MpCmdRun.exe" }
	Write-Host "MpCmdRun: $mpcmd"
	& $mpcmd -SignatureUpdate 2>&1 | Select-Object -Last 3 | ForEach-Object { Write-Host "  $_" }
	$targets = @(Get-ChildItem $Pkg -File -Recurse | Where-Object { $_.Extension -in '.dll', '.exe', '.pk3' }) + @(Get-Item $appx)
	foreach ($t in $targets) {
		$out = & $mpcmd -Scan -ScanType 3 -File $t.FullName -DisableRemediation 2>&1 | Out-String
		$threat = ($out -split "`n" | Where-Object { $_ -match 'Threat|found' }) -join ' | '
		Write-Host ("  {0,-40} exit {1}  {2}" -f $t.Name, $LASTEXITCODE, $threat.Trim())
	}
} catch {
	Write-Host "Defender scan unavailable on this runner: $_"
}
$global:LASTEXITCODE = 0

# ---------------------------------------------------------------------------
Step 'Bundle release zip'
$dist = Join-Path $Work 'dist'
New-Item -ItemType Directory -Force -Path $dist | Out-Null
Copy-Item $appx, $cer $dist
Copy-Item (Join-Path $Root 'uwp\README-XBOX.md') $dist

$vclibs = Get-ChildItem "${env:ProgramFiles(x86)}\Microsoft SDKs\Windows Kits\10\ExtensionSDKs\Microsoft.VCLibs\14.0\Appx\Retail\x64" `
	-Filter 'Microsoft.VCLibs.x64.14.00.appx' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($vclibs) { Copy-Item $vclibs.FullName $dist } else { Write-Warning 'VCLibs framework package not found on runner' }

Compress-Archive -Path (Join-Path $dist '*') -DestinationPath (Join-Path $Artifacts 'Xash3DXbox-x64.zip') -Force
Write-Host "Done: version $Version"
