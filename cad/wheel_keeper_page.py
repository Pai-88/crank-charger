"""One page of pictures for the wheel keeper band, Avenir captions, from keeper_1..4.png."""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "stl", "spares")
AV = "/System/Library/Fonts/Avenir.ttc"
def font(px, idx=8):
    return ImageFont.truetype(AV, px, index=idx)
W, PW, PH, HEAD, CAP = 2000, 1000, 750, 110, 150
page = Image.new("RGB", (W, HEAD + 2 * (PH + CAP) + 40), (12, 12, 13))
dr = ImageDraw.Draw(page)
dr.text((40, 28), "Wheel keeper band: the hand wheel clicks onto the ring gear", font=font(44, 4), fill=(240, 240, 240))
dr.text((40, 80), "wheel_keeper_band.stl, one piece, 26 g PETG, about 40 min. No screws, no nut needed to hold the wheel.", font=font(24), fill=(170, 170, 175))
caps = [
    ("1. The band: six lips (top) for the wheel's face, three arms with barbs for the ring.", "Print it as it loads: lips on the bed, arms up."),
    ("2. On the machine: it hugs the outside of the wheel rim. The opening sits top left.", "Spread it there with both thumbs, slip it over the rim, let go."),
    ("3. A slice through one arm. Grey: wheel rim. Orange: ring gear. Blue: the band.", "Lip over the wheel's front face (bottom); barb under the ring's back edge (top)."),
    ("4. From behind: the arms run down the skirt into the gap before the wall,", "between the dogs and clear of the clip ring's lugs. The dogs still drive the ring."),
]
for i in range(4):
    im = Image.open(os.path.join(D, f"keeper_{i + 1}.png")).convert("RGB").resize((PW, PH), Image.LANCZOS)
    x, y = (i % 2) * PW, HEAD + (i // 2) * (PH + CAP)
    page.paste(im, (x, y))
    a, b = caps[i]
    dr.text((x + 24, y + PH + 18), a, font=font(26), fill=(235, 235, 235))
    dr.text((x + 24, y + PH + 58), b, font=font(24), fill=(165, 165, 170))
# labels on the slice
x3, y3 = 0, HEAD + PH + CAP
def label(text, at, xy):
    dr.line([xy, at], fill=(240, 240, 240), width=3)
    dr.ellipse([at[0] - 6, at[1] - 6, at[0] + 6, at[1] + 6], fill=(240, 240, 240))
    dr.text((xy[0] + 10, xy[1] - 16), text, font=font(26), fill=(255, 255, 255))
label("barb, under the ring's back edge", (x3 + 548, y3 + 190), (x3 + 640, y3 + 120))
label("band, 2 mm, 0.3 mm off the rim", (x3 + 565, y3 + 380), (x3 + 660, y3 + 380))
label("lip, over the wheel's front face", (x3 + 548, y3 + 585), (x3 + 640, y3 + 650))
label("wheel rim", (x3 + 400, y3 + 530), (x3 + 240, y3 + 600))
label("ring gear", (x3 + 480, y3 + 300), (x3 + 300, y3 + 250))
out = os.path.join(D, "keeper_page.png")
page.save(out)
print("wrote", out, page.size)
