#!/usr/bin/env python3
"""Build the crank charger showcase cut in FilmCraft (headless, filmcraft-cli).

Usage: python3 filmcraft_build.py 9x16 | 16x9 [--export]

Places act 1 + act 2 on V1, the Higgsfield narration on A1, a title card,
four lower thirds timed to the narration and an end card, with fades, then
exports H.264. Every line on screen is a design fact; no watts, volts or rpm
until the 25 Oct exit test has measured them (see COMMENTARY.md).
"""
import json, os, subprocess, sys

CLI = os.path.expanduser("~/.local/bin/filmcraft-cli")
HERE = os.path.dirname(os.path.abspath(__file__))
T = 254_016_000_000  # ticks per second
FPS = 30
WHITE, ORANGE, GREY = "#ffffff", "#ff8a3d", "#c9c9c9"
FONT = "Avenir Next"

ACT1_S = 25.666667  # length of the act 1 clip (both aspect ratios)

LAYOUT = {
    "9x16": dict(w=1080, h=1920, act1="crank_9x16_46s.mp4", act2="crank_elec9x16_46s.mp4",
                 head=92, sub=44, top=(330, 420), bottom=(1600, 1680), end=(300, 400, 470)),
    "16x9": dict(w=1920, h=1080, act1="crank_16x9_46s.mp4", act2="crank_elec16x9_46s.mp4",
                 head=84, sub=40, top=(420, 500), bottom=(930, 1000), end=(150, 240, 300),
                 top_x=1440, end_x=1480, end_head=72),
}


def titles(L):
    cx = L["w"] / 2
    tx, ex = L.get("top_x", cx), L.get("end_x", cx)
    t1, t2 = L["top"]
    b1, b2 = L["bottom"]
    e1, e2, e3 = L["end"]
    H, S = L["head"], L["sub"]
    # (start s, end s, [(text, y, size, colour, style)], x)
    return [
        (0.8, 5.3, [("HAND-CRANK\nPHONE CHARGER", t1, H, WHITE, "Bold"),
                    ("every plastic part 3D printed", t1 + H * 2.3, S, ORANGE, "Medium")], tx),
        (7.5, 12.0, [("PLANETARY STAGE", b1, H, WHITE, "Bold"),
                     ("17 · 37 · 91 teeth    5.35 : 1", b2, S, ORANGE, "Medium")]),
        (12.5, 18.5, [("STEPPER MOTOR\nAS GENERATOR", b1, H, WHITE, "Bold"),
                      ("three planets on steel pins, one sun on the shaft", b2, S, ORANGE, "Medium")]),
        (26.2, 31.5, [("EIGHT SCHOTTKY\nDIODES", b1, H, WHITE, "Bold"),
                      ("two bridges and one capacitor make DC", b2, S, ORANGE, "Medium")]),
        (32.0, 37.5, [("BUCK CONVERTER\nTO USB 5 V", b1, H, WHITE, "Bold"),
                      ("a plug-in meter shows what the phone gets", b2, S, ORANGE, "Medium")]),
        (43.5, 49.0, [("Designed by Paing", e1, L.get("end_head", H), WHITE, "Bold"),
                      ("paingheinhtet.com", e2, S, ORANGE, "Medium"),
                      ("Rendered from the CAD.\nMeasured results to follow.", e3, int(S * 0.8), GREY, "Regular")], ex),
    ]


def run(project, lines, save=True):
    args = [CLI, "--project", project, "--compact"] + (["--save"] if save else []) + ["run", "-"]
    p = subprocess.run(args, input="\n".join(json.dumps(l) for l in lines) + "\n",
                       capture_output=True, text=True)
    out = []
    for ln in p.stdout.splitlines():
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if not r.get("ok"):
            print("FAILED:", ln, file=sys.stderr)
            sys.exit(1)
        out.append(r)
    if p.returncode:
        print(p.stderr, file=sys.stderr)
        sys.exit(p.returncode)
    return out


def main():
    aspect = sys.argv[1]
    L = LAYOUT[aspect]
    project = os.path.join(HERE, f"showcase_{aspect}.fcproj")
    if os.path.exists(project):
        os.remove(project)

    # 1. project, sequence, media
    subprocess.run([CLI, "--save-as", project, "run", "-"], check=True, capture_output=True, text=True,
                   input=json.dumps({"id": "file.newProject", "params": {"name": f"Crank charger showcase {aspect}"}}) + "\n"
                   + json.dumps({"id": "file.newSequence", "params": {"name": f"Showcase {aspect}", "width": L["w"],
                                                                      "height": L["h"], "fps": FPS, "video": 4, "audio": 2}}) + "\n")
    imp = subprocess.run([CLI, "--project", project, "--save", "import",
                          os.path.join(HERE, L["act1"]), os.path.join(HERE, L["act2"]),
                          os.path.join(HERE, "commentary.wav")], capture_output=True, text=True, check=True)
    act1, act2, voice = json.loads(imp.stdout)["items"]

    # 2. picture and sound on the timeline
    r = run(project, [
        {"id": "timeline.place", "params": {"item": act1, "track": "V1", "seconds": 0, "audio": False}},
        {"id": "timeline.place", "params": {"item": act2, "track": "V1", "seconds": ACT1_S, "audio": False}},
        {"id": "timeline.place", "params": {"item": voice, "track": "A1", "seconds": 0}},
    ])
    c1, c2, ca = (x["result"]["clips"][0] for x in r)

    # 3. titles: one graphic clip per line (headline on V2, subs on V3)
    cx = L["w"] / 2
    create, meta = [], []
    for entry in titles(L):
        start, end, lines = entry[:3]
        x = entry[3] if len(entry) > 3 else cx
        for i, (text, y, size, colour, style) in enumerate(lines):
            n = text.count("\n")
            if n and y > L["h"] / 2:
                y = y - n * size * 1.2
            create.append({"id": "graphics.newText", "params": {
                "text": text, "position": [x, y], "size": size, "font": FONT, "fontStyle": style,
                "seconds": round(end - start, 3), "track": 2 + i, "time": int(start * T)}})
            meta.append((colour, x, y))
    r = run(project, create)
    clips = [x["result"]["clip"] for x in r]

    style = []
    for clip, (colour, x, y) in zip(clips, meta):
        for param, value in (("align", "Center"), ("position", [x, y]), ("fill_color", colour), ("tracking", 30),
                             ("shadow", True)):
            style.append({"id": "effects.setParam", "params": {"clip": clip, "effect": "graphic_text",
                                                               "param": param, "value": value}})
        for edge in ("in", "out"):
            style.append({"id": "sequence.applyVideoTransition",
                          "params": {"clip": clip, "effect": "cross_dissolve", "frames": 12, "edge": edge}})
    # 4. picture fades: in from black, dip to black at the act cut, out to black
    style += [
        {"id": "sequence.applyVideoTransition", "params": {"clip": c1, "effect": "dip_to_black", "frames": 20, "edge": "in"}},
        {"id": "sequence.applyVideoTransition", "params": {"clip": c2, "effect": "dip_to_black", "frames": 16, "edge": "in"}},
        {"id": "sequence.applyVideoTransition", "params": {"clip": c2, "effect": "dip_to_black", "frames": 30, "edge": "out"}},
        {"id": "sequence.applyAudioTransition", "params": {"clip": ca, "effect": "constant_power", "frames": 20, "edge": "out"}},
    ]
    run(project, style)
    print(f"built {project}: V1 clips {c1},{c2}; A1 {ca}; {len(clips)} title layers")

    if "--export" in sys.argv:
        out = os.path.join(HERE, f"crank_showcase_{aspect}_filmcraft.mp4")
        p = subprocess.run([CLI, "--project", project, "export", out, "--format", "h264",
                            "--settings", json.dumps({"bitrateMode": "crf", "crf": 18})],
                           capture_output=True, text=True)
        print(p.stdout[-600:], p.stderr[-600:])
        print("exported", out)


if __name__ == "__main__":
    main()
