from PIL import Image, ImageDraw
from pathlib import Path

size = 1024
mask = Image.new("L", (size, size), 0)
draw = ImageDraw.Draw(mask)

def line(points, width):
    draw.line(points, fill=255, width=width, joint="curve")
    radius = width // 2
    for x, y in (points[0], points[-1]):
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=255)

# Asterisk with an intentionally elongated vertical ray.
line([(512, 145), (512, 879)], 44)
line([(286, 512), (738, 512)], 30)
line([(354, 328), (670, 696)], 26)
line([(670, 328), (354, 696)], 26)

gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
pixels = gradient.load()
for x in range(size):
    t = x / (size - 1)
    start = (125, 211, 252)
    end = (37, 99, 235)
    color = tuple(round(start[i] * (1-t) + end[i] * t) for i in range(3))
    for y in range(size):
        pixels[x, y] = (*color, mask.getpixel((x, y)))
out = Path(__file__).resolve().parents[1] / "assets" / "aura-mark.png"
out.parent.mkdir(parents=True, exist_ok=True)
gradient.save(out, "PNG", optimize=True)
print(out)
