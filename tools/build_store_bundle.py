"""Bundle existing store submission ZIPs and the listing/privacy drafts."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
version=json.loads((ROOT/'releases.json').read_text('utf-8'))['releases'][0]['version']
name=f'DownloadNow-Store-Submission-{version}'
folder=ROOT/'dist'/name
if folder.exists():raise SystemExit('Store bundle already exists')
shutil.copytree(ROOT/'store',folder)
source=ROOT/'dist'/f'DownloadNow-Browser-Extensions-{version}'
for browser in ('Chrome','Edge','Firefox'):
    suffix='-unsigned' if browser=='Firefox' else ''
    asset=f'DownloadNow-{browser}-{version}{suffix}.zip'
    shutil.copy2(source/asset,folder/asset)
archive=folder.parent/(name+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
    for item in sorted(folder.rglob('*')):
        if item.is_file():package.write(item,item.relative_to(folder))
Path(str(archive)+'.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n',encoding='utf-8')
print(archive)
