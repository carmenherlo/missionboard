import random, subprocess, sys, os, shutil
from PIL import Image
out, dest = sys.argv[1], sys.argv[2]
W, H = 1920, 1080
random.seed(7)
stars = [(random.randint(0, W), random.randint(0, 560), random.choice([1.5, 2, 2.5, 3])) for _ in range(150)]
flakes = [(random.randint(0, W), random.randint(0, H), random.choice([2, 3, 4])) for _ in range(90)]
M = {
 "manana": dict(sky=["#6f8fd6", "#c9b6e4", "#ffc9b0", "#ffe6c4"], far="#c3c6e6", mid="#dcdcf2", near="#f4eef2", shade="#c7c4e4", tree="#4f6a8c", wood="#9c7a78", roof="#e4dff0", win="#ffe3a0", glow=0.15, disc=(330, 640, 74, "#fff0c4", "#ffd9a0"), stars=0.12, flake=0.7, rocket="#f6f0f2", fin="#d9607a"),
 "dia":    dict(sky=["#3f93e6", "#74b5ef", "#a9d4f6", "#d6ecfb"], far="#bcd6ec", mid="#d9e9f6", near="#f7fbff", shade="#c4d8ec", tree="#2f7a68", wood="#9a6a4c", roof="#ffffff", win="#8fc3e8", glow=0, disc=(1000, 170, 66, "#fff6c9", "#ffe98f"), stars=0, flake=0.9, rocket="#ffffff", fin="#e0483f"),
 "tarde":  dict(sky=["#59509c", "#b4608e", "#f0875f", "#ffc36e"], far="#b08aa8", mid="#d4a6ae", near="#f6d9c6", shade="#c99aa6", tree="#47405f", wood="#7b5048", roof="#f2cfc0", win="#ffd27a", glow=0.25, disc=(1590, 660, 84, "#ffdf8a", "#ff9f50"), stars=0.05, flake=0.6, rocket="#f6dccb", fin="#c8434f"),
 "noche":  dict(sky=["#0b1236", "#141c4c", "#232a66", "#3a3f82"], far="#2c3468", mid="#3b4580", near="#6470a8", shade="#333c74", tree="#141c3e", wood="#2c2a4c", roof="#7f8bc0", win="#ffd76e", glow=0.75, disc=(1560, 190, 62, "#f6f2d8", "#dfe3f6"), stars=1, flake=0.45, rocket="#9aa6d4", fin="#7a4a7e"),
}
def pine(x, y, s, c):
    return "".join(f'<polygon points="{x},{y-s*k} {x-s*(0.42-0.1*i)},{y-s*(k-0.48)} {x+s*(0.42-0.1*i)},{y-s*(k-0.48)}" fill="{c}"/>' for i, k in enumerate((0.6, 0.85, 1.1))) + f'<rect x="{x-s*.05}" y="{y-s*.14}" width="{s*.1}" height="{s*.16}" fill="{c}"/>'
def snowcap(x, y, s, c):
    return f'<polygon points="{x},{y-s*1.1} {x-s*.13},{y-s*.88} {x+s*.13},{y-s*.88}" fill="{c}"/>'
def svg(p):
    s0, s1, s2, s3 = p["sky"]; cx, cy, r, c1, c2 = p["disc"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs><linearGradient id="s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{s0}"/><stop offset=".45" stop-color="{s1}"/><stop offset=".75" stop-color="{s2}"/><stop offset="1" stop-color="{s3}"/></linearGradient><radialGradient id="g"><stop offset="0" stop-color="{c1}" stop-opacity=".75"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></radialGradient><radialGradient id="w"><stop offset="0" stop-color="{p["win"]}" stop-opacity=".55"/><stop offset="1" stop-color="{p["win"]}" stop-opacity="0"/></radialGradient></defs><rect width="{W}" height="{H}" fill="url(#s)"/>']
    if p["stars"]: o += [f'<circle cx="{x}" cy="{y}" r="{r2}" fill="#fff" opacity="{p["stars"]*.85}"/>' for x, y, r2 in stars]
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r*3.4}" fill="url(#g)"/><circle cx="{cx}" cy="{cy}" r="{r}" fill="{c2}"/><circle cx="{cx}" cy="{cy}" r="{r*.8}" fill="{c1}"/>')
    o.append(f'<path d="M0 700 C 240 610, 470 640, 720 690 S 1240 620, 1500 650 S 1800 690, 1920 640 V1080 H0Z" fill="{p["far"]}"/>')
    for x, y, s in [(120,700,120),(205,705,90),(1730,690,120),(1820,690,95)]: o.append(pine(x,y,s,p["tree"])); o.append(snowcap(x,y,s,p["mid"]))
    o.append(f'<path d="M0 800 C 300 730, 640 780, 960 810 S 1560 730, 1920 780 V1080 H0Z" fill="{p["mid"]}"/>')
    # the house, left
    hx, hy = 250, 800
    o.append(f'<rect x="{hx}" y="{hy-110}" width="170" height="120" fill="{p["wood"]}"/><polygon points="{hx-22},{hy-105} {hx+85},{hy-190} {hx+192},{hy-105}" fill="{p["roof"]}"/><rect x="{hx+25}" y="{hy-82}" width="42" height="42" rx="4" fill="{p["win"]}"/><rect x="{hx+103}" y="{hy-82}" width="42" height="42" rx="4" fill="{p["win"]}"/>')
    if p["glow"]: o.append(f'<circle cx="{hx+85}" cy="{hy-60}" r="170" fill="url(#w)" opacity="{p["glow"]}"/>')
    # the rocket, right
    rx, ry = 1560, 815
    o.append(f'<polygon points="{rx-32},{ry-40} {rx-62},{ry+6} {rx-32},{ry-2}" fill="{p["fin"]}"/><polygon points="{rx+32},{ry-40} {rx+62},{ry+6} {rx+32},{ry-2}" fill="{p["fin"]}"/><path d="M{rx} {ry-210} C {rx+48} {ry-150}, {rx+40} {ry-50}, {rx+32} {ry} H{rx-32} C {rx-40} {ry-50}, {rx-48} {ry-150}, {rx} {ry-210}Z" fill="{p["rocket"]}"/><path d="M{rx} {ry-210} C {rx+24} {ry-182}, {rx+34} {ry-160}, {rx+37} {ry-145} H{rx-37} C {rx-34} {ry-160}, {rx-24} {ry-182}, {rx} {ry-210}Z" fill="{p["fin"]}"/><circle cx="{rx}" cy="{ry-105}" r="19" fill="{p["win"]}" stroke="{p["fin"]}" stroke-width="6"/>')
    o.append(f'<path d="M0 930 C 380 860, 760 900, 1080 940 S 1640 880, 1920 920 V1080 H0Z" fill="{p["near"]}"/><path d="M0 1010 C 500 970, 1100 1030, 1920 980 V1080 H0Z" fill="{p["shade"]}" opacity=".45"/>')
    for x, y, s in [(60,950,190),(1860,940,210)]: o.append(pine(x,y,s,p["tree"])); o.append(snowcap(x,y,s,p["near"]))
    o += [f'<circle cx="{x}" cy="{y}" r="{r2}" fill="#fff" opacity="{p["flake"]}"/>' for x, y, r2 in flakes]
    o.append("</svg>")
    return "".join(o)
os.makedirs(dest, exist_ok=True)
sheet = Image.new("RGB", (W, H))
for i, (name, p) in enumerate(M.items()):
    f = f"{out}/{name}.svg"; open(f, "w").write(svg(p))
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={out}/chrome", f"--window-size={W},{H}", "--force-device-scale-factor=1", f"--screenshot={out}/{name}.png", f"file://{f}"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=60)
    im = Image.open(f"{out}/{name}.png").convert("RGB")
    print(name, im.size)
    im.save(f"{dest}/{name}.webp", "WEBP", quality=82, method=6)
    print(" ", os.path.getsize(f"{dest}/{name}.webp") // 1024, "KB")
    sheet.paste(im.resize((W // 2, H // 2)), ((i % 2) * W // 2, (i // 2) * H // 2))
sheet.resize((1400, 788)).save(f"{out}/sheet.png")
