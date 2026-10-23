"""Keep identical browser extension resources in both package folders."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1] / 'extension'
for name in ('background.js', 'facebook-feed.js', 'facebook-probe.js', 'content.js', 'connect.js', 'updates.js', 'popup.js', 'popup.html'):
    shutil.copyfile(root / 'chromium' / name, root / 'firefox' / name)
