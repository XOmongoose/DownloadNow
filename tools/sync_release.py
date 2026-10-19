"""Edit releases.json, then run this script for every release."""
from pathlib import Path
import html
import json
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
releases = json.loads((root / 'releases.json').read_text('utf-8'))['releases']
version = releases[0]['version']
if not re.fullmatch(r'\d+\.\d+\.\d+', version):
    raise ValueError('Use a major.minor.patch version.')

def replace_block(source, name, value):
    pattern = rf'<!-- {name}:start -->.*?<!-- {name}:end -->'
    updated, count = re.subn(pattern, lambda _: f'<!-- {name}:start -->{value}<!-- {name}:end -->', source, flags=re.S)
    if count != 1:
        raise ValueError(f'Expected one {name} block, found {count}')
    return updated

page = root / 'web' / 'index.html'
source = page.read_text('utf-8')
source = replace_block(source, 'version', html.escape('v' + version))
entries = []
for i, release in enumerate(releases):
    esc = html.escape
    badge = '<span class="release-current">Đang sử dụng</span>' if i == 0 else ''
    changes = ''.join(f'<li>{esc(change)}</li>' for change in release['changes'])
    entries.append(f'<article class="release-entry"><div class="release-meta"><strong>v{esc(release["version"])}</strong>{badge}<time datetime="{esc(release["date"])}">{esc(release["date"])}</time></div><h3>{esc(release["title"])}</h3><ul>{changes}</ul></article>')
source = replace_block(source, 'releases', ''.join(entries))
page.write_text(source, encoding='utf-8')
for browser in ('chromium', 'firefox'):
    manifest = root / 'extension' / browser / 'manifest.json'
    data = json.loads(manifest.read_text('utf-8'))
    data['version'] = version
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
popup = root / 'extension' / 'chromium' / 'popup.html'
popup.write_text(replace_block(popup.read_text('utf-8'), 'version', 'v' + version), encoding='utf-8')
subprocess.run([sys.executable, str(root / 'tools' / 'sync_extension.py')], check=True)
print('Release v' + version + ' synchronized.')
