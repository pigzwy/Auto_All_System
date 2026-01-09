from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from PIL import Image
import os

def convert_svg_to_ico(svg_path, ico_path):
    try:
        # Convert SVG to Drawing
        drawing = svg2rlg(svg_path)
        
        # Convert Drawing to PNG in memory (or temp file)
        png_path = "temp_icon.png"
        renderPM.drawToFile(drawing, png_path, fmt="PNG")
        
        # Convert PNG to ICO using Pillow with multiple sizes for better Windows support
        img = Image.open(png_path)
        # Ensure base image is high res
        if img.width < 256 or img.height < 256:
             img = img.resize((256, 256), Image.Resampling.LANCZOS)
             
        img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        
        # Cleanup
        if os.path.exists(png_path):
            os.remove(png_path)
            
        print(f"Successfully converted {svg_path} to {ico_path}")
        return True
    except Exception as e:
        print(f"Failed to convert: {e}")
        return False

if __name__ == "__main__":
    convert_svg_to_ico("beta-1.svg", "app_icon.ico")
