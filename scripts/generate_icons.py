import os
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
icons_dir = os.path.join(BASE_DIR, 'static', 'icons')
source_icon = os.path.join(icons_dir, 'icon-512x512.png')

SIZES = [72, 96, 128, 144, 152, 192, 256, 384, 512]

os.makedirs(icons_dir, exist_ok=True)

if not os.path.exists(source_icon):
    raise SystemExit(f"Source icon not found: {source_icon}")

img = Image.open(source_icon).convert('RGBA')

for size in SIZES:
    out_path = os.path.join(icons_dir, f'icon-{size}x{size}.png')
    resized = img.resize((size, size), Image.LANCZOS)
    resized.save(out_path, format='PNG')
    print(f"Generated: {out_path}")

print('All icons generated successfully.')
