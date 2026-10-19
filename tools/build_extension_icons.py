"""Code-native brand icons, deterministic PNG output with no dependencies."""
import math
from pathlib import Path
import struct
import zlib

ROOT=Path(__file__).resolve().parents[1]


def png(size):
    segments=[(128,62,128,156),(92,124,128,160),(128,160,164,124),(70,170,70,195),(70,195,186,195),(186,170,186,195)]
    def distance(x,y,line):
        ax,ay,bx,by=line
        t=max(0,min(1,((x-ax)*(bx-ax)+(y-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2)))
        return math.hypot(x-ax-t*(bx-ax),y-ay-t*(by-ay))
    rows=bytearray()
    for row in range(size):
        rows.append(0)
        for col in range(size):
            x,y=(col+.5)*256/size,(row+.5)*256/size
            edge=math.hypot(max(24-x,0,x-231),max(24-y,0,y-231))
            alpha=round(255*min(1,max(0,(24.5-edge)*size/256)))
            blend=min(1,max(0,(10-min(distance(x,y,line) for line in segments))*size/256))
            rows.extend((*[round(a*(1-blend)+b*blend) for a,b in zip((241,175,0),(48,38,0))],alpha))
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b'')


if __name__=='__main__':
    for browser in ('chromium','firefox'):
        folder=ROOT/'extension'/browser/'icons'
        folder.mkdir(exist_ok=True)
        for size in (16,32,48,128):
            (folder/f'{size}.png').write_bytes(png(size))
