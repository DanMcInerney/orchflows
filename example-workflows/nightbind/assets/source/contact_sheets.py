"""Arrange unmodified actual model renders at delivery size and 48px UI size."""
from PIL import Image,ImageDraw
from pathlib import Path
import json
P=Path(__file__).resolve().parents[2]; assets=json.loads((P/'public/models/manifest.json').read_text())['assets']
portraits=[a for a in assets if 'portrait' in a]
for a in portraits:
    path=P/'public'/a['portrait'].lstrip('/'); im=Image.open(path).convert('RGBA'); im.save(path,optimize=True,compress_level=9)
for size in (192,48):
    cell=max(100,size+20); height=size+36; out=Image.new('RGB',(cell*5,height*3),'#101C23'); draw=ImageDraw.Draw(out)
    for i,a in enumerate(portraits):
        im=Image.open(P/'public'/a['portrait'].lstrip('/')).convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)
        x=(i%5)*cell+(cell-size)//2; y=(i//5)*height
        out.paste(im,(x,y),im); draw.text(((i%5)*cell+8,y+size+6),a['id'],fill='#D9D3B8')
    out.save(P/f'evidence/assets/portraits-{size}.png')

for group,ids in [('bases',['keeper','ember','thorn','volt','mire','fang','moth']),('evolved',['pyre','storm','dusk','solar','world','eclipse','boss'])]:
    out=Image.new('RGB',(640,7*135),'#101C23'); draw=ImageDraw.Draw(out)
    for row,name in enumerate(ids):
        for col,yaw in enumerate((0,90,180,270)):
            file=P/f'evidence/assets/{name}-runtime-yaw{yaw}.png'
            if not file.exists(): continue
            im=Image.open(file).crop((560,260,720,380)); out.paste(im,(col*160,row*135))
            draw.text((col*160+4,row*135+120),f'{name} {yaw}',fill='#D9D3B8')
    out.save(P/f'evidence/assets/{group}-runtime-four-facings.png')
