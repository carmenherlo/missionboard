import random, subprocess, sys, os
from PIL import Image
out, root = sys.argv[1], sys.argv[2]
W, H = 1920, 1080
def rgb(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
def mix(a, b, t):
    x, y = rgb(a), rgb(b)
    return "#%02x%02x%02x" % tuple(round(x[i] + (y[i] - x[i]) * t) for i in range(3))
# Each moment: the same sky and light as winter's (the sun or moon in the same place)
MOMENTS = {
 "manana": dict(sky=["#6f8fd6", "#c9b6e4", "#ffc9b0", "#ffe6c4"], tint="#ffbfa0", amount=.28, win="#ffe3a0", glow=.15, disc=(330, 640, 74, "#fff0c4", "#ffd9a0"), stars=.12, part=.8, clouds=.55, cloud="#ffe6dc"),
 "dia":    dict(sky=["#3f93e6", "#74b5ef", "#a9d4f6", "#d6ecfb"], tint="#ffffff", amount=0, win="#8fc3e8", glow=0, disc=(1000, 170, 66, "#fff6c9", "#ffe98f"), stars=0, part=1, clouds=.95, cloud="#ffffff"),
 "tarde":  dict(sky=["#59509c", "#b4608e", "#f0875f", "#ffc36e"], tint="#c9604f", amount=.36, win="#ffd27a", glow=.25, disc=(1590, 660, 84, "#ffdf8a", "#ff9f50"), stars=.05, part=.8, clouds=.5, cloud="#ffc6a0"),
 "noche":  dict(sky=["#0b1236", "#141c4c", "#232a66", "#3a3f82"], tint="#111a4c", amount=.74, win="#ffd76e", glow=.75, disc=(1560, 190, 62, "#f6f2d8", "#dfe3f6"), stars=1, part=.5, clouds=.1, cloud="#6a74b0"),
}
SEASONS = {
 "primavera": dict(far="#b9dfa8", mid="#a4d68e", near="#8fcb78", shade="#74b663", leaf=["#f8bcd2", "#f49dbd", "#fbd3e0"], trunk="#8a6248", roof="#d9694f", wood="#b98a62", part="#fbc3d6", kind="petal", n=70, ground=["#fff4a8", "#ffffff", "#f6a8c6"], nground=70, clouds=True),
 "verano":    dict(far="#a3d36f", mid="#86c557", near="#6db544", shade="#57a036", leaf=["#3f9d4f", "#55b25c", "#2f8a45"], trunk="#7c5a40", roof="#d4583f", wood="#c29a6e", part="#fff27a", kind="fly", n=26, ground=["#ffe066", "#ffffff", "#ff8fa3"], nground=46, clouds=True),
 "otono":     dict(far="#d9b777", mid="#cfa35c", near="#bf8b45", shade="#a87637", leaf=["#e8892b", "#d4562f", "#f0b23a"], trunk="#6c4a36", roof="#a84a35", wood="#a9794f", part="#e8892b", kind="leaf", n=60, ground=["#d4562f", "#f0b23a", "#e8892b"], nground=60, clouds=False),
}
def tree(x, y, s, cols, tr):
    o = f'<rect x="{x-s*.06}" y="{y-s*.5}" width="{s*.12}" height="{s*.52}" rx="{s*.03}" fill="{tr}"/>'
    for dx, dy, r, c in [(0,-.72,.34,0),(-.24,-.52,.25,1),(.24,-.52,.25,2),(-.13,-.92,.2,1),(.15,-.9,.2,2)]:
        o += f'<circle cx="{x+dx*s}" cy="{y+dy*s}" r="{r*s}" fill="{cols[c]}"/>'
    return o
def cloud(x, y, s, c, a):
    return f'<g fill="{c}" opacity="{a}"><ellipse cx="{x}" cy="{y}" rx="{s}" ry="{s*.34}"/><circle cx="{x-s*.38}" cy="{y-s*.16}" r="{s*.3}"/><circle cx="{x+.1*s}" cy="{y-s*.3}" r="{s*.4}"/><circle cx="{x+s*.48}" cy="{y-s*.1}" r="{s*.26}"/></g>'
def svg(season, moment):
    p, m = SEASONS[season], MOMENTS[moment]
    t = lambda c: mix(c, m["tint"], m["amount"])
    random.seed(11)
    stars = [(random.randint(0, W), random.randint(0, 560), random.choice([1.5, 2, 2.5, 3])) for _ in range(150)]
    s0, s1, s2, s3 = m["sky"]; cx, cy, r, c1, c2 = m["disc"]; win = m["win"]
    leaf = [t(c) for c in p["leaf"]]; tr = t(p["trunk"])
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs><linearGradient id="s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{s0}"/><stop offset=".45" stop-color="{s1}"/><stop offset=".75" stop-color="{s2}"/><stop offset="1" stop-color="{s3}"/></linearGradient><radialGradient id="g"><stop offset="0" stop-color="{c1}" stop-opacity=".75"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></radialGradient><radialGradient id="w"><stop offset="0" stop-color="{win}" stop-opacity=".55"/><stop offset="1" stop-color="{win}" stop-opacity="0"/></radialGradient></defs><rect width="{W}" height="{H}" fill="url(#s)"/>']
    if m["stars"]: o += [f'<circle cx="{x}" cy="{y}" r="{r2}" fill="#fff" opacity="{m["stars"]*.85}"/>' for x, y, r2 in stars]
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r*3.4}" fill="url(#g)"/><circle cx="{cx}" cy="{cy}" r="{r}" fill="{c2}"/><circle cx="{cx}" cy="{cy}" r="{r*.8}" fill="{c1}"/>')
    if p["clouds"]:
        for x, y, s in [(330,190,120),(1420,300,100),(760,330,75)]: o.append(cloud(x, y, s, m["cloud"], m["clouds"]))
    o.append(f'<path d="M0 700 C 240 610, 470 640, 720 690 S 1240 620, 1500 650 S 1800 690, 1920 640 V1080 H0Z" fill="{t(p["far"])}"/>')
    for x, y, s in [(120,705,125),(205,708,95),(1730,695,125),(1820,695,100)]: o.append(tree(x, y, s, leaf, tr))
    o.append(f'<path d="M0 800 C 300 730, 640 780, 960 810 S 1560 730, 1920 780 V1080 H0Z" fill="{t(p["mid"])}"/>')
    hx, hy = 250, 800
    o.append(f'<rect x="{hx}" y="{hy-110}" width="170" height="120" fill="{t(p["wood"])}"/><polygon points="{hx-22},{hy-105} {hx+85},{hy-190} {hx+192},{hy-105}" fill="{t(p["roof"])}"/><rect x="{hx+25}" y="{hy-82}" width="42" height="42" rx="4" fill="{win}"/><rect x="{hx+103}" y="{hy-82}" width="42" height="42" rx="4" fill="{win}"/>')
    if m["glow"]: o.append(f'<circle cx="{hx+85}" cy="{hy-60}" r="170" fill="url(#w)" opacity="{m["glow"]}"/>')
    rx, ry = 1560, 815; rocket, fin = t("#ffffff"), t("#e0483f")
    o.append(f'<polygon points="{rx-32},{ry-40} {rx-62},{ry+6} {rx-32},{ry-2}" fill="{fin}"/><polygon points="{rx+32},{ry-40} {rx+62},{ry+6} {rx+32},{ry-2}" fill="{fin}"/><path d="M{rx} {ry-210} C {rx+48} {ry-150}, {rx+40} {ry-50}, {rx+32} {ry} H{rx-32} C {rx-40} {ry-50}, {rx-48} {ry-150}, {rx} {ry-210}Z" fill="{rocket}"/><path d="M{rx} {ry-210} C {rx+24} {ry-182}, {rx+34} {ry-160}, {rx+37} {ry-145} H{rx-37} C {rx-34} {ry-160}, {rx-24} {ry-182}, {rx} {ry-210}Z" fill="{fin}"/><circle cx="{rx}" cy="{ry-105}" r="19" fill="{win}" stroke="{fin}" stroke-width="6"/>')
    o.append(f'<path d="M0 930 C 380 860, 760 900, 1080 940 S 1640 880, 1920 920 V1080 H0Z" fill="{t(p["near"])}"/><path d="M0 1010 C 500 970, 1100 1030, 1920 980 V1080 H0Z" fill="{t(p["shade"])}" opacity=".55"/>')
    # On the ground, at the front: flowers, or fallen leaves (never in the middle's way: low and small)
    random.seed(23)
    for _ in range(p["nground"]):
        x, y, c = random.randint(0, W), random.randint(945, 1072), t(random.choice(p["ground"]))
        if p["kind"] == "leaf": o.append(f'<ellipse cx="{x}" cy="{y}" rx="9" ry="4" fill="{c}" transform="rotate({random.randint(0,180)} {x} {y})"/>')
        else: o.append(f'<circle cx="{x}" cy="{y}" r="{random.choice([3,4,5])}" fill="{c}"/>')
    for x, y, s in [(60,955,195),(1860,945,215)]: o.append(tree(x, y, s, leaf, tr))
    # In the air
    random.seed(31)
    for _ in range(p["n"]):
        x, y = random.randint(0, W), random.randint(0, H)
        if p["kind"] == "fly":  # fireflies at night; by day, hardly anything
            if moment == "noche": o.append(f'<circle cx="{x}" cy="{random.randint(620, 1050)}" r="3.5" fill="{p["part"]}" opacity=".9"/>')
            continue
        c = t(random.choice(p["leaf"])) if moment != "noche" else t(p["part"])
        o.append(f'<ellipse cx="{x}" cy="{y}" rx="{7 if p["kind"]=="leaf" else 5}" ry="3" fill="{c}" opacity="{m["part"]}" transform="rotate({random.randint(0,180)} {x} {y})"/>')
    o.append("</svg>")
    return "".join(o)
order = ["manana", "dia", "tarde", "noche"]
sheet = Image.new("RGB", (4 * 480, 3 * 270))
for row, season in enumerate(SEASONS):
    dest = f"{root}/{season}"; os.makedirs(dest, exist_ok=True)
    sizes = []
    for col, moment in enumerate(order):
        f = f"{out}/{season}-{moment}.svg"; open(f, "w").write(svg(season, moment))
        png = f"{out}/{season}-{moment}.png"
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={out}/chrome", f"--window-size={W},{H}", "--force-device-scale-factor=1", f"--screenshot={png}", f"file://{f}"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=60)
        im = Image.open(png).convert("RGB")
        im.save(f"{dest}/{moment}.webp", "WEBP", quality=82, method=6)
        sizes.append(os.path.getsize(f"{dest}/{moment}.webp") // 1024)
        sheet.paste(im.resize((480, 270)), (col * 480, row * 270))
    print(season, sizes, "KB")
sheet.save(f"{out}/seasons.png")
