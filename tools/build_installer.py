"""Compile a self-contained per-user Windows installer from the clean package."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def main():
    version=json.loads((ROOT/'releases.json').read_text('utf-8'))['releases'][0]['version']
    package=ROOT/'dist'/f'DownloadNow-{version}-Windows-x64'
    if not (package/'DownloadNow.exe').is_file():
        raise SystemExit('Build tools/build_windows.py first.')
    if (package/'data').exists():
        raise SystemExit('Refusing to include user data in installer.')
    for entry in (package/'SHA256SUMS.txt').read_text('utf-8').splitlines():
        digest,name=entry.split('  ',1)
        path=(package/name).resolve()
        if not path.is_relative_to(package.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise SystemExit('Package checksum mismatch: '+name)
    target=ROOT/'dist'/f'DownloadNow-Setup-{version}-Windows-x64.exe'
    if target.exists():
        raise SystemExit('Installer exists; use a new version.')
    compiler=ROOT/'.tools/InnoSetup/ISCC.exe'
    if not compiler.is_file():
        raise SystemExit('Run tools/bootstrap_inno.ps1 first.')
    subprocess.run([str(compiler),f'/DAppVersion={version}',f'/DPackageDir={package}',
                    f'/DOutputFolder={ROOT/"dist"}',str(ROOT/'tools/windows_installer.iss')],check=True)
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.exe.sha256').write_text(digest+'  '+target.name+'\n',encoding='utf-8')
    print('Installer: '+str(target))

if __name__=='__main__':main()
