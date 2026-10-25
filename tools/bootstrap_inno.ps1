$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$compiler=Join-Path $root '.tools/InnoSetup/ISCC.exe'
if(Test-Path -LiteralPath $compiler){Write-Output $compiler;exit 0}
$installer=Join-Path $root '.tools/innosetup-6.7.3.exe'
New-Item -ItemType Directory -Path (Split-Path $installer -Parent) -Force | Out-Null
if(-not (Test-Path -LiteralPath $installer)){
 Invoke-WebRequest 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' -OutFile $installer
}
$expected='9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732'
if((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw 'Inno Setup checksum mismatch'}
$signature=Get-AuthenticodeSignature -LiteralPath $installer
if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Pyrsys B.V.'){
 throw 'Inno Setup publisher signature is invalid'
}
$destination=Split-Path $compiler -Parent
$process=Start-Process -FilePath $installer -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /NOICONS /TASKS=`"`" /DIR=`"$destination`"" -WindowStyle Hidden -Wait -PassThru
if($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $compiler)){throw 'Cannot install Inno Setup compiler'}
Write-Output $compiler
