"""Pictures for the click-on frame (Blender, headless):

    /Applications/Blender.app/Contents/MacOS/Blender --background --python cad/frame_click_pictures.py
    .venv/bin/python cad/frame_click_pictures.py --page          (the labelled page, from the pictures)

Writes cad/stl/spares/click_1..4.png and click_anchors.json (where the labelled points land in each
picture), then --page lays out cad/stl/spares/click_page.png with captions and labels.
The frame's body is graphite and everything added to it is teal: both are the real solids from
cad/frame_click.py. The cover is the mesh the cover's own pictures use, in its real place.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "assembly", "_build", "frame_click")
OUT = os.path.join(HERE, "stl", "spares")
ANCH = os.path.join(OUT, "click_anchors.json")
W, H = 1400, 1050

# model points (mm) that the page labels, per picture
POINTS = {
    "click_1": {"front lip": (98.0, 14.0, -33.0), "rear lip": (104.2, 14.0, -66.0), "spring blade": (107.6, 9.0, -86.0),
                "hook": (104.6, 9.0, -103.0), "peg groove": (72.0, 8.0, -88.0), "corner web": (22.0, 11.0, -11.0)},
    "click_2": {"cover": (0.0, 150.0, -151.0), "arrow0": (0.0, 4.0, -290.0), "arrow1": (0.0, 4.0, -175.0),
                "peg groove": (72.0, 8.0, -88.0)},
    "click_3": {"hook": (104.6, 10.0, -102.6), "spring blade": (108.2, 12.0, -86.0), "rear lip": (104.0, 15.2, -66.0),
                "foot": (92.0, 12.0, -88.0), "tip": (108.2, 15.2, -105.0)},
    "click_4": {"text": (0.0, 8.0, 0.0)},
}


def render():
    import glob
    import math
    import subprocess

    import bpy
    import bpy_extras
    from mathutils import Vector

    S = 0.001
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 96
    if hasattr(sc.eevee, "use_raytracing"):
        sc.eevee.use_raytracing = True
    sc.render.resolution_x, sc.render.resolution_y = W, H
    im = sc.render.image_settings
    if hasattr(im, "media_type"):
        im.media_type = "IMAGE"
    im.file_format, im.color_mode = "PNG", "RGBA"
    sc.render.use_file_extension = False
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    wn = world.node_tree
    bg = wn.nodes["Background"]
    hits = glob.glob(os.path.join(os.path.dirname(bpy.app.binary_path), "..", "Resources", "*", "datafiles", "studiolights", "world", "studio.exr"))
    if hits:
        env = wn.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hits[0])
        sep = wn.nodes.new("ShaderNodeSeparateXYZ")
        wn.links.new(wn.nodes.new("ShaderNodeTexCoord").outputs["Generated"], sep.inputs[0])
        sky = wn.nodes.new("ShaderNodeMapRange")
        sky.interpolation_type, sky.clamp = "SMOOTHSTEP", True
        sky.inputs["From Min"].default_value, sky.inputs["From Max"].default_value = 0.12, 0.45
        wn.links.new(sep.outputs["Z"], sky.inputs["Value"])
        gate = wn.nodes.new("ShaderNodeMix")
        gate.data_type, gate.blend_type = "RGBA", "MULTIPLY"
        gate.inputs["Factor"].default_value = 1.0
        wn.links.new(env.outputs["Color"], gate.inputs[6])
        wn.links.new(sky.outputs["Result"], gate.inputs[7])
        wn.links.new(gate.outputs[2], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 1.15
    sc.world = world

    def material(name, base, metallic, rough, coat=0.0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*base, 1.0)
        b.inputs["Metallic"].default_value = metallic
        b.inputs["Roughness"].default_value = rough
        if coat and "Coat Weight" in b.inputs:
            b.inputs["Coat Weight"].default_value = coat
        return m

    MAT = dict(body=material("graphite", (0.085, 0.09, 0.095), 0.0, 0.36, 0.35), new=material("new", (0.10, 0.62, 0.72), 0.0, 0.38, 0.3),
               cover=material("cover", (0.20, 0.21, 0.23), 0.0, 0.45, 0.2), gear=material("orange", (0.86, 0.30, 0.035), 0.0, 0.4, 0.25),
               motor=material("motor", (0.03, 0.03, 0.032), 0.55, 0.38))
    rig = bpy.data.objects.new("rig", None)
    rig.rotation_euler = (math.pi / 2, 0.0, 0.0)
    sc.collection.objects.link(rig)

    def load(path, name, mat):
        bpy.ops.wm.stl_import(filepath=path, global_scale=S)
        ob = bpy.context.selected_objects[0]
        ob.name = name
        ob.data.materials.clear()
        ob.data.materials.append(MAT[mat])
        try:
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30.0))
        except Exception:
            pass
        ob.parent = rig
        return ob

    stl = os.path.join(HERE, "stl")
    objs = {"body": load(os.path.join(BUILD, "body_view.stl"), "body", "body"),
            "new": load(os.path.join(BUILD, "new_view.stl"), "new", "new"),
            "cover": load(os.path.join(stl, "cover", "_view_NOT_FOR_PRINTING", "shell.stl"), "cover", "cover"),
            "motor": load(os.path.join(stl, "_view_motor.stl"), "motor", "motor"),
            "wheel": load(os.path.join(ROOT, "assembly", "_build", "keeper", "wheel_bayonet_view.stl"), "wheel", "body")}
    for n in ("ring", "sun", "planet1", "planet2", "planet3", "spider"):
        objs[n] = load(os.path.join(stl, f"_view_{n}.stl"), n, "gear")

    floor_me = bpy.data.meshes.new("floor")
    floor_me.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    fb = fm.node_tree.nodes["Principled BSDF"]
    fb.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1)
    fb.inputs["Roughness"].default_value = 0.33
    floor_me.materials.append(fm)
    floor = bpy.data.objects.new("floor", floor_me)
    floor.scale = (5, 5, 1)
    sc.collection.objects.link(floor)

    pivot = bpy.data.objects.new("pivot", None)
    sc.collection.objects.link(pivot)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens, cam_data.sensor_width, cam_data.sensor_fit = 50.0, 36.0, "HORIZONTAL"
    cam_data.clip_start, cam_data.clip_end = 0.01, 50.0
    cam = bpy.data.objects.new("cam", cam_data)
    cam.parent = pivot
    sc.collection.objects.link(cam)
    sc.camera = cam
    con = cam.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"

    def light(name, loc, size, power, specular=0.6):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size = power, size
        if hasattr(ld, "specular_factor"):
            ld.specular_factor = specular
        lo = bpy.data.objects.new(name, ld)
        lo.parent = pivot
        lo.location = loc
        sc.collection.objects.link(lo)
        c = lo.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"

    light("key", (-1.3, -1.1, 1.5), 1.2, 62.0)
    light("rim", (1.0, 1.5, 1.6), 1.2, 60.0, 0.2)
    light("fill", (0.3, -1.7, 0.7), 1.6, 36.0, 0.3)

    def to_world(p):
        return Vector((p[0] * S, -p[2] * S, p[1] * S))

    anchors = json.load(open(ANCH)) if os.path.exists(ANCH) else {}
    only = [a for a in sys.argv[sys.argv.index('--') + 1:]] if '--' in sys.argv else []
    lights = {}

    def shot(name, target, phi, elev, dist, show, cover_back=0.0, fill=36.0):
        if only and name not in only:
            return
        bpy.data.lights['fill'].energy = fill
        for n, ob in objs.items():
            ob.hide_render = n not in show
        objs["cover"].location = Vector((0.0, 0.0, -cover_back * S))           # rig space = the model's axes
        pivot.location = to_world(target)
        pivot.rotation_euler = (0.0, 0.0, math.radians(phi))
        el = math.radians(elev)
        cam.location = (0.0, -dist * math.cos(el), dist * math.sin(el))
        bpy.context.view_layer.update()
        anchors[name] = {}
        for key, p in POINTS[name].items():
            uv = bpy_extras.object_utils.world_to_camera_view(sc, cam, to_world(p))
            anchors[name][key] = [round(uv.x, 4), round(1.0 - uv.y, 4)]         # from the left, from the TOP
        path = os.path.join(OUT, name)
        sc.render.filepath = path + ".rgba.png"
        bpy.ops.render.render(write_still=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path + ".rgba.png", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}",
                        "-filter_complex", "[1:v][0:v]overlay=shortest=1,format=rgb24", "-frames:v", "1", path + ".png"], check=True)
        os.remove(path + ".rgba.png")
        print("wrote", path + ".png")

    frame_only = ("body", "new", "motor")
    gears = ("ring", "sun", "planet1", "planet2", "planet3", "spider")
    # 1: the new frame from behind, the +X side toward the camera: lips, grooves, blades, hooks, corner web
    shot("click_1", (0, 28, -55), -215, 36, 0.50, frame_only + gears)
    # 2: the cover on its way in, 55 mm from home, flat on the base
    shot("click_2", (10, 60, -75), -215, 26, 0.74, frame_only + gears + ("cover",), cover_back=55.0)
    # 3: home: close on the +X rear corner: the foot under the rear lip, the hook behind it
    shot("click_3", (97, 9, -94), -200, 44, 0.20, frame_only + ("cover",))
    # 4: from the front, low: the lettering under the wheel
    shot("click_4", (0, 30, 0), -20, 16, 0.33, ("body", "new"), fill=110.0)
    json.dump(anchors, open(ANCH, "w"), indent=1)


def page():
    from PIL import Image, ImageDraw, ImageFont
    AV = "/System/Library/Fonts/Avenir.ttc"
    font = lambda px, idx=8: ImageFont.truetype(AV, px, index=idx)
    PW, PH, HEAD, CAP = 1000, 750, 118, 138
    anchors = json.load(open(ANCH))
    pg = Image.new("RGB", (2 * PW, HEAD + 2 * (PH + CAP) + 30), (12, 12, 13))
    dr = ImageDraw.Draw(pg)
    dr.text((40, 26), "New stand: the electronics cover clicks on", font=font(46, 4), fill=(240, 240, 240))
    dr.text((40, 82), "frame_click.stl. Print it like the old stand: front face on the bed, PETG, no supports. Blue = what is new.",
            font=font(24), fill=(170, 170, 175))
    caps = {
        "click_1": ("1. The new stand from behind. Same wall, motor seat and pins as before.", "Blue: four lips, two spring blades with hooks, two peg grooves, a corner web."),
        "click_2": ("2. Set the cover on the base behind the wall, flat. Push it forward.", "Its two pegs ride in the grooves. No lifting, no screws."),
        "click_3": ("3. Click, both sides. The foot is under the lip, the hook is behind it.", "To take it off: pull the cover straight back, or thumb the two blade tips apart."),
        "click_4": ("4. The front (wheel and gears off for the picture): your line, sunk in.", "The G-clamps still hold the base to the table, on the cover's feet as before."),
    }
    # label text, anchor key, where the text starts (panel pixels)
    labels = {
        "click_1": [("front lip", "front lip", (30, 392)), ("rear lip", "rear lip", (30, 462)), ("spring blade", "spring blade", (30, 560)),
                    ("hook", "hook", (110, 668)), ("peg groove", "peg groove", (420, 668)), ("corner web", "corner web", (640, 430))],
        "click_2": [("cover", "cover", (120, 120)), ("pegs ride in the grooves", "peg groove", (40, 680))],
        "click_3": [("hook, behind the foot", "hook", (560, 600)), ("spring blade", "spring blade", (60, 420)), ("rear lip, over the foot", "rear lip", (60, 150)),
                    ("the cover's foot", "foot", (640, 440)), ("thumb here to release", "tip", (60, 640))],
        "click_4": [("Designed With Love By Paing, 0.6 mm deep", "text", (300, 640))],
    }
    for i, name in enumerate(("click_1", "click_2", "click_3", "click_4")):
        im = Image.open(os.path.join(OUT, name + ".png")).convert("RGB").resize((PW, PH), Image.LANCZOS)
        x0, y0 = (i % 2) * PW, HEAD + (i // 2) * (PH + CAP)
        pg.paste(im, (x0, y0))
        a, b = caps[name]
        dr.text((x0 + 24, y0 + PH + 16), a, font=font(26), fill=(235, 235, 235))
        dr.text((x0 + 24, y0 + PH + 56), b, font=font(24), fill=(165, 165, 170))
        for text, key, (lx, ly) in labels[name]:
            u, v = anchors[name][key]
            ax, ay = x0 + u * PW, y0 + v * PH
            f = font(26)
            tw = dr.textlength(text, font=f)
            tx, ty = x0 + lx, y0 + ly
            end = (tx + tw + 8, ty + 16) if tx + tw / 2 < ax else (tx - 8, ty + 16)
            dr.line([end, (ax, ay)], fill=(245, 245, 245), width=3)
            dr.ellipse([ax - 6, ay - 6, ax + 6, ay + 6], fill=(245, 245, 245))
            dr.rectangle([tx - 6, ty - 4, tx + tw + 6, ty + 34], fill=(0, 0, 0))
            dr.text((tx, ty), text, font=f, fill=(255, 255, 255))
        if name == "click_2":                                           # the push arrow
            (u0, v0), (u1, v1) = anchors[name]["arrow0"], anchors[name]["arrow1"]
            p0, p1 = (x0 + u0 * PW, y0 + v0 * PH), (x0 + u1 * PW, y0 + v1 * PH)
            dr.line([p0, p1], fill=(255, 190, 60), width=10)
            import math
            ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
            head = [(p1[0] + 26 * math.cos(ang), p1[1] + 26 * math.sin(ang)),
                    (p1[0] + 20 * math.cos(ang + 2.4), p1[1] + 20 * math.sin(ang + 2.4)),
                    (p1[0] + 20 * math.cos(ang - 2.4), p1[1] + 20 * math.sin(ang - 2.4))]
            dr.polygon(head, fill=(255, 190, 60))
            f = font(30, 4)
            tw = dr.textlength("push until it clicks", font=f)
            dr.text((min(p0[0] - tw / 2, x0 + PW - tw - 24), p0[1] + 12), "push until it clicks", font=f, fill=(255, 190, 60))
    out = os.path.join(OUT, "click_page.png")
    pg.save(out)
    print("wrote", out, pg.size)


if __name__ == "__main__":
    if "--page" in sys.argv:
        page()
    else:
        render()
