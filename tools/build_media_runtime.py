"""Fetch pinned official video tools at build time; never fetch code at runtime."""
from pathlib import Path
import hashlib
import io
import json
import shutil
import subprocess
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ASSETS=[
 ('yt-dlp.exe','https://github.com/yt-dlp/yt-dlp/releases/download/2026.10.21/yt-dlp.exe','33121d192d706e62f684a06f80918e3f3a8ba52ac3a65213b6951c39c7d9f555',None),
 ('deno.exe','https://github.com/denoland/deno/releases/download/v2.9.8/deno-x86_64-pc-windows-msvc.zip','cba84b26e0df5ae7f74fc66b86a95b866872a86292ebd84fa1e959927edd93bf','deno.exe')]


def build():
    import imageio_ffmpeg
    target=ROOT/'build/media-runtime';target.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'build/media-cache';cache.mkdir(exist_ok=True)
    for name,url,checksum,member in ASSETS:
        archive=cache/checksum
        if not archive.exists():
            req=urllib.request.Request(url,headers={'User-Agent':'DownloadNow-build'})
            with urllib.request.urlopen(req,timeout=90) as response:body=response.read(180*1024*1024)
            if hashlib.sha256(body).hexdigest()!=checksum:raise ValueError('Media tool SHA-256 mismatch: '+name)
            archive.write_bytes(body)
        body=archive.read_bytes()
        if hashlib.sha256(body).hexdigest()!=checksum:raise ValueError('Invalid cached media tool: '+name)
        if member:
            with zipfile.ZipFile(io.BytesIO(body)) as package:body=package.read(member)
        (target/name).write_bytes(body)
    shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(),target/'ffmpeg.exe')
    for name,url in [
        ('yt-dlp-LICENSE.txt','https://raw.githubusercontent.com/yt-dlp/yt-dlp/2026.10.21/LICENSE'),
        ('yt-dlp-DEPENDENCIES.txt','https://raw.githubusercontent.com/yt-dlp/yt-dlp/2026.10.21/THIRD_PARTY_LICENSES.txt'),
        ('deno-LICENSE.txt','https://raw.githubusercontent.com/denoland/deno/v2.9.8/LICENSE.md'),
        ('GPL-3.0.txt','https://raw.githubusercontent.com/FFmpeg/FFmpeg/n7.1/COPYING.GPLv3')]:
        if not (target/name).exists():
            with urllib.request.urlopen(url,timeout=30) as response:(target/name).write_bytes(response.read(2*1024*1024))
    details=subprocess.run([str(target/'ffmpeg.exe'),'-L'],capture_output=True,encoding='utf-8',errors='replace')
    (target/'ffmpeg-LICENSE-BUILD.txt').write_text(details.stdout+details.stderr,encoding='utf-8')
    (target/'THIRD-PARTY.txt').write_text('''Bundled video tools:
yt-dlp 2026.10.21: https://github.com/yt-dlp/yt-dlp (Unlicense; bundled dependency licenses: https://github.com/yt-dlp/yt-dlp/blob/2026.10.21/THIRD_PARTY_LICENSES.txt)
Deno 2.9.8: https://github.com/denoland/deno (MIT)
FFmpeg 7.1 GPLv3 from imageio-ffmpeg 0.6.0 / Gyan: https://github.com/imageio/imageio-ffmpeg
FFmpeg source: https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz
Build provenance and dependency sources: https://www.gyan.dev/ffmpeg/builds/ and https://github.com/imageio/imageio-ffmpeg/tree/v0.6.0
Use ffmpeg.exe -L and -buildconf for the binary's license/build details.
''',encoding='utf-8')
    print('Pinned video runtime ready:',target)
    return target


if __name__=='__main__':build()
