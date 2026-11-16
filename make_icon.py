"""Generate the EDBio application icon (PNG)."""

from PIL import Image, ImageDraw

SIZE = 256
DARK = (43, 43, 43, 255)        # ED dark grey
ORANGE = (255, 153, 0, 255)     # ED orange
WHITE = (240, 240, 240, 255)

img = Image.new("RGBA", (SIZE, SIZE), DARK)
draw = ImageDraw.Draw(img)

# Outer scan ring.
ring_w = 10
draw.ellipse([ring_w, ring_w, SIZE - ring_w, SIZE - ring_w],
             outline=ORANGE, width=ring_w)

# Inner planet / bio circle.
inner = 52
cx = cy = SIZE // 2
draw.ellipse([cx - inner, cy - inner, cx + inner, cy + inner],
             fill=ORANGE)

# Small white detail dot (biological signal).
dot = 14
draw.ellipse([cx - dot, cy - dot - 18, cx + dot, cy + dot - 18], fill=WHITE)

# Save multiple sizes embedded.
img.save("edbio/resources/icon.png")

# Also save an ICO for Windows (contains several sizes).
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save("edbio/resources/icon.ico", sizes=sizes)
print("icon saved")
