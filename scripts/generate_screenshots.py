import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
shots_dir = os.path.join(BASE_DIR, 'static', 'screenshots')
os.makedirs(shots_dir, exist_ok=True)

specs = [
    ('mobile-screenshot1.png', 375, 812, 'NESAKO AI\nMobile UI'),
    ('desktop-screenshot1.png', 1920, 1080, 'NESAKO AI\nDesktop UI'),
]

for name, w, h, label in specs:
    img = Image.new('RGBA', (w, h), '#ffffff')
    draw = ImageDraw.Draw(img)
    # Simple gradient background
    for y in range(h):
        ratio = y / max(1, h-1)
        r1, g1, b1 = (102, 126, 234)  # #667eea
        r2, g2, b2 = (118, 75, 162)   # #764ba2
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    # Label text
    try:
        font = ImageFont.truetype('arial.ttf', size=max(18, w // 18))
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.multiline_textbbox((0, 0), label, font=font, spacing=10, align='center')
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(((w - tw)//2, (h - th)//2), label, fill='#ffffff', font=font, align='center', spacing=10)
    out_path = os.path.join(shots_dir, name)
    img.convert('RGB').save(out_path, 'PNG')
    print('Generated:', out_path)

print('Screenshots generated.')
