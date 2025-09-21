from PIL import Image, ImageDraw
import os

# Create icons directory if it doesn't exist
os.makedirs('static/icons', exist_ok=True)

# Sizes for different icons
sizes = [192, 512, 144]

for size in sizes:
    # Create a simple placeholder icon
    img = Image.new('RGB', (size, size), color='blue')
    draw = ImageDraw.Draw(img)
    
    # Add some text to identify the icon
    if size >= 144:
        # Only add text to larger icons
        text = f"{size}x{size}"
        # Very simple text placement
        text_position = (size//2 - len(text)*3, size//2 - 10)
        draw.text(text_position, text, fill='white')
    
    # Save the icon
    img.save(f'static/icons/icon-{size}x{size}.png')
    print(f"Created static/icons/icon-{size}x{size}.png")

print("Icons created successfully!")
