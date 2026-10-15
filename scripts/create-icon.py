"""Code-drawn terminal icon for the Windows executable and installer."""
from pathlib import Path
from PIL import Image, ImageDraw

image = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((10, 10, 246, 246), radius=48, fill='#171717', outline='#dcb74e', width=6)
draw.line([(57, 83), (106, 128), (57, 173)], fill='#e3bf58', width=16, joint='curve')
draw.rounded_rectangle((125, 160, 198, 176), radius=3, fill='#e3bf58')
output = Path(__file__).resolve().parents[1] / 'desktop' / 'icon.ico'
image.save(output, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(output)
