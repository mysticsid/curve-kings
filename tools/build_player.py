# Builds assets/player.glb from the CC0 Quaternius packs in downloads/.
# Run from the game folder:  .\blender.exe -b --factory-startup -P tools\build_player.py -- [--render]
#
# What it does:
#   1. imports the Superhero_Male base body and a buzzed hairstyle
#   2. splits the body into kit regions (Shirt, Shorts, Socks, Boots, Hands, Skin) so the game can recolour them
#   3. copies the useful clips from Universal Animation Library 1/2 (idle, jog, sprint, jump, celebrations)
#   4. authors the football clips the packs don't have: Kick, Keeper_Dive (ready -> full stretch), Wall_Jump
#   5. shrinks textures and exports a single GLB
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.normpath(os.path.join(HERE, '..'))
DL = os.path.join(GAME, 'downloads')
CHAR = os.path.join(DL, 'base-characters', 'Universal Base Characters[Standard]', 'Base Characters', 'Godot - UE', 'Superhero_Male_FullBody.gltf')
HAIR = os.path.join(DL, 'base-characters', 'Universal Base Characters[Standard]', 'Hairstyles', 'Rigged to Head Bone', 'glTF (Godot -Unreal)', 'Hair_Buzzed.gltf')
UAL1 = os.path.join(DL, 'animation-library-1', 'Universal Animation Library[Standard]', 'Unreal-Godot', 'UAL1_Standard.glb')
UAL2 = os.path.join(DL, 'animation-library-2', 'Universal Animation Library 2[Standard]', 'Unreal-Godot', 'UAL2_Standard.glb')
# Exported as GLB to downloads/, then tools/glb_to_json.js turns it into assets/player.gltf.json
# (the artifact host serves .json but not .glb).
OUT = os.path.join(DL, 'player.glb')
RENDER = '--render' in sys.argv
RENDER_DIR = os.path.join(GAME, 'tools', 'renders')

KEEP_CLIPS = {  # pack name -> name used in the game
    'Idle_Loop': 'Idle', 'Jog_Fwd_Loop': 'Jog', 'Sprint_Loop': 'Sprint',
    'Dance_Loop': 'Celebrate', 'Yes': 'Yes', 'Idle_No_Loop': 'No',
}

def log(*a): print('[build]', *a, flush=True)

# ---------------------------------------------------------------- import
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30

bpy.ops.import_scene.gltf(filepath=CHAR)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.name = 'Player'
body = bpy.data.objects['SuperHero_Male']
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'):
        bpy.data.objects.remove(o)

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=HAIR)
new = set(bpy.data.objects) - before
log('hair import', [(o.name, o.type, tuple(round(c, 2) for c in o.matrix_world.translation)) for o in new])
for o in list(new):
    if o.name.startswith('Icosphere'):
        new.discard(o); bpy.data.objects.remove(o)
for o in new:
    if o.type == 'MESH':
        mw = o.matrix_world.copy()
        o.parent = arm
        o.matrix_world = mw
        for m in [m for m in o.modifiers if m.type == 'ARMATURE']: o.modifiers.remove(m)
        mod = o.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
        if 'Head' not in o.vertex_groups:  # bind every vertex to the head bone
            vg = o.vertex_groups.new(name='Head'); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
        o.name = 'Hair'
for o in new:
    if o.type != 'MESH':
        for child in o.children: child.parent = arm
        bpy.data.objects.remove(o)

# ---------------------------------------------------------------- kit regions
# Limbs are decided by bone, but hem lines by height so the kit edges are straight.
WAIST, SHORTS_HEM, SOCK_TOP, BOOT_TOP = 0.99, 0.6, 0.47, 0.11
COLLAR, SLEEVE_END = 1.5, 0.27  # collar height; sleeve trim within this distance (m) of the elbow
def region_for(bone, z, elbow_dist=9):
    if bone.startswith(('hand_', 'index_', 'middle_', 'ring_', 'pinky_', 'thumb_')): return 'Hands'
    if bone.startswith(('lowerarm_', 'neck_', 'Head')) or bone == 'head': return 'Skin'
    if bone.startswith(('upperarm_', 'clavicle_')): return 'Trim' if elbow_dist < SLEEVE_END - 0.2 else 'Shirt'
    if z > WAIST:
        if not bone.startswith(('spine_', 'pelvis')): return 'Skin'
        return 'Trim' if z > COLLAR else 'Shirt'
    if z > SHORTS_HEM: return 'Trim' if z < SHORTS_HEM + 0.035 else 'Shorts'
    if z > SOCK_TOP: return 'Skin'
    if z > BOOT_TOP and not bone.startswith(('foot_', 'ball_')): return 'Trim' if z > SOCK_TOP - 0.03 else 'Socks'
    return 'Boots'

skin_mat = body.data.materials[0]
skin_mat.name = 'Skin'
normal_img = None
for n in skin_mat.node_tree.nodes:
    if n.type == 'TEX_IMAGE' and 'Normal' in n.image.name: normal_img = n.image

def fabric(name, rgb, rough):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)  # colour in the preview renders
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*rgb, 1)
    bsdf.inputs['Roughness'].default_value = rough
    if normal_img:  # keep the body's muscle detail under the kit
        tex = m.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = normal_img
        nm = m.node_tree.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.6
        uv = m.node_tree.nodes.new('ShaderNodeUVMap')
        m.node_tree.links.new(uv.outputs[0], tex.inputs[0])
        m.node_tree.links.new(tex.outputs['Color'], nm.inputs['Color'])
        m.node_tree.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return m

skin_mat.diffuse_color = (0.55, 0.38, 0.28, 1)
mats = {'Skin': skin_mat,
        'Shirt': fabric('Shirt', (0.1, 0.3, 0.85), 0.75),
        'Shorts': fabric('Shorts', (0.95, 0.95, 0.95), 0.7),
        'Socks': fabric('Socks', (0.1, 0.3, 0.85), 0.85),
        'Boots': fabric('Boots', (0.03, 0.03, 0.035), 0.35),
        'Trim': fabric('Trim', (0.95, 0.95, 0.95), 0.7),
        'Hands': fabric('Hands', (0.55, 0.38, 0.28), 0.6)}
order = list(mats)
body.data.materials.clear()
for k in order: body.data.materials.append(mats[k])

groups = {g.index: g.name for g in body.vertex_groups}
mesh = body.data
vbone = []
for v in mesh.vertices:
    best = max(v.groups, key=lambda g: g.weight, default=None)
    vbone.append(groups.get(best.group, '') if best else '')
elbows = [arm.matrix_world @ arm.data.bones[n].head_local for n in ('lowerarm_l', 'lowerarm_r')]
counts = {}
for p in mesh.polygons:
    tally = {}
    for vi in p.vertices: tally[vbone[vi]] = tally.get(vbone[vi], 0) + 1
    c = body.matrix_world @ p.center
    r = region_for(max(tally, key=tally.get), c.z, min((c - e).length for e in elbows))
    p.material_index = order.index(r)
    counts[r] = counts.get(r, 0) + 1
log('kit faces', counts)

# ---------------------------------------------------------------- animation clips from the packs
def import_clips(path):
    before_obj, before_act = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    for o in set(bpy.data.objects) - before_obj: bpy.data.objects.remove(o)
    for a in set(bpy.data.actions) - before_act:
        if a.name in KEEP_CLIPS:
            a.name = KEEP_CLIPS[a.name]; a.use_fake_user = True
        else:
            bpy.data.actions.remove(a)
import_clips(UAL1)
import_clips(UAL2)
log('clips', [a.name for a in bpy.data.actions])

if arm.animation_data is None: arm.animation_data_create()
def use_action(act):
    arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot') and act.slots:
        arm.animation_data.action_slot = act.slots[0]

# ---------------------------------------------------------------- authored football clips
pb = arm.pose.bones
for b in pb: b.rotation_mode = 'QUATERNION'

use_action(bpy.data.actions['Idle'])
scene.frame_set(0)
BASE = {b.name: (b.rotation_quaternion.copy(), b.location.copy()) for b in pb}
arm.animation_data.action = None

def set_base():
    for b in pb:
        b.rotation_quaternion, b.location = BASE[b.name][0].copy(), BASE[b.name][1].copy()
    bpy.context.view_layer.update()

# Armature space: +Z up, the player faces -Y, +X is the player's left.
# Arms: rotating about Y swings a hanging arm sideways; negative degrees take the LEFT arm outward, positive the right.
def rot(bone, axis, deg):
    b = pb[bone]; m = b.matrix.copy(); h = m.translation.copy()
    b.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ m
    bpy.context.view_layer.update()
def move(bone, off):
    b = pb[bone]; m = b.matrix.copy(); m.translation += Vector(off); b.matrix = m
    bpy.context.view_layer.update()

def make_clip(name, keys):
    act = bpy.data.actions.new(name); act.use_fake_user = True
    use_action(act)
    for frame, spec in keys:
        set_base()
        for step in spec:
            (move if step[0] == 'move' else rot)(*step[1:])
        for b in pb:
            b.keyframe_insert('rotation_quaternion', frame=frame, group=b.name)
            b.keyframe_insert('location', frame=frame, group=b.name)
    arm.animation_data.action = None
    return act

ARMS_DOWN = [('rot', 'upperarm_l', 'Y', 0), ('rot', 'upperarm_r', 'Y', 0)]

# Kick: plant, wind back, strike (frame 12), follow through, recover. 30 fps.
make_clip('Kick', [
    (0,  [('rot', 'thigh_r', 'X', 8), ('rot', 'calf_r', 'X', 20)]),
    (6,  [('rot', 'spine_01', 'X', -6), ('rot', 'thigh_r', 'X', 45), ('rot', 'calf_r', 'X', 85),
          ('rot', 'upperarm_l', 'Y', -50), ('rot', 'upperarm_r', 'Y', 35), ('rot', 'thigh_l', 'X', -10), ('rot', 'calf_l', 'X', 20)]),
    (12, [('rot', 'spine_01', 'X', 8), ('rot', 'thigh_r', 'X', -35), ('rot', 'calf_r', 'X', 15),
          ('rot', 'upperarm_l', 'Y', -70), ('rot', 'upperarm_r', 'Y', 45), ('rot', 'thigh_l', 'X', -12), ('rot', 'calf_l', 'X', 25)]),
    (18, [('rot', 'spine_01', 'X', 12), ('rot', 'thigh_r', 'X', -75), ('rot', 'calf_r', 'X', 5),
          ('rot', 'upperarm_l', 'Y', -55), ('rot', 'upperarm_r', 'Y', 30), ('rot', 'calf_l', 'X', 15)]),
    (28, [('rot', 'thigh_r', 'X', -15), ('rot', 'calf_r', 'X', 25)]),
])

# Keeper: frame 0 = set position (crouched, gloves forward), frame 10 = full stretch (arms overhead, body straight).
# The game rotates the whole player sideways for the dive and scrubs this clip with the dive progress.
make_clip('Keeper_Dive', [
    (0,  [('move', 'pelvis', (0, 0, -0.16)), ('rot', 'spine_01', 'X', -18),
          ('rot', 'thigh_l', 'X', -35), ('rot', 'calf_l', 'X', 60), ('rot', 'thigh_r', 'X', -35), ('rot', 'calf_r', 'X', 60),
          ('rot', 'thigh_l', 'Y', -8), ('rot', 'thigh_r', 'Y', 8),
          ('rot', 'upperarm_l', 'X', -55), ('rot', 'upperarm_r', 'X', -55),
          ('rot', 'upperarm_l', 'Y', -20), ('rot', 'upperarm_r', 'Y', 20),
          ('rot', 'lowerarm_l', 'X', -35), ('rot', 'lowerarm_r', 'X', -35)]),
    (10, [('rot', 'upperarm_l', 'Y', -160), ('rot', 'upperarm_r', 'Y', 160),
          ('rot', 'thigh_l', 'Y', 6), ('rot', 'thigh_r', 'Y', -6), ('rot', 'thigh_r', 'X', -20), ('rot', 'calf_r', 'X', 30)]),
])

# Wall: frame 0 = standing guard (hands crossed low), frame 10 = jump with arms up.
make_clip('Wall_Jump', [
    (0,  [('rot', 'upperarm_l', 'X', -30), ('rot', 'upperarm_r', 'X', -30), ('rot', 'upperarm_l', 'Y', 25), ('rot', 'upperarm_r', 'Y', -25),
          ('rot', 'lowerarm_l', 'Z', -40), ('rot', 'lowerarm_r', 'Z', 40)]),
    (10, [('rot', 'upperarm_l', 'Y', -150), ('rot', 'upperarm_r', 'Y', 150),
          ('rot', 'thigh_l', 'X', 10), ('rot', 'calf_l', 'X', 30), ('rot', 'thigh_r', 'X', 10), ('rot', 'calf_r', 'X', 30)]),
])

# ---------------------------------------------------------------- motion capture (CMU database, BVH)
# Retargeting: each mapped bone copies the source bone's world-space rotation *relative to the source T-pose*
# (frame 1 of every CMU file) onto our bone's rest pose (also a T-pose). Hips height is scaled to our player.
CMU = os.path.join(DL, 'cmu')
MAP = {
    'pelvis': 'Hips', 'spine_01': 'LowerBack', 'spine_02': 'Spine', 'spine_03': 'Spine1', 'neck_01': 'Neck', 'Head': 'Head',
    'clavicle_l': 'LeftShoulder', 'upperarm_l': 'LeftArm', 'lowerarm_l': 'LeftForeArm', 'hand_l': 'LeftHand',
    'clavicle_r': 'RightShoulder', 'upperarm_r': 'RightArm', 'lowerarm_r': 'RightForeArm', 'hand_r': 'RightHand',
    'thigh_l': 'LeftUpLeg', 'calf_l': 'LeftLeg', 'foot_l': 'LeftFoot', 'ball_l': 'LeftToeBase',
    'thigh_r': 'RightUpLeg', 'calf_r': 'RightLeg', 'foot_r': 'RightFoot', 'ball_r': 'RightToeBase',
}
from mathutils import Quaternion
ab = arm.data.bones
log('target rest upperarm_l dir', tuple(round(c, 2) for c in (ab['upperarm_l'].tail_local - ab['upperarm_l'].head_local).normalized()))

def facing_yaw(src, f):
    scene.frame_set(f)
    l = src.matrix_world @ src.pose.bones['LeftUpLeg'].head
    r = src.matrix_world @ src.pose.bones['RightUpLeg'].head
    lat = l - r                      # points to the character's left
    fwd = lat.cross(Vector((0, 0, 1)))  # left x up = forward
    return math.atan2(fwd.y, fwd.x)

def retarget(bvh, name, window=None, kick=False, inplace=True, loop_trim=0):
    before = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(filepath=os.path.join(CMU, bvh), global_scale=1.0, frame_start=1, use_fps_scale=False,
                            update_scene_fps=False, update_scene_duration=False, rotate_mode='NATIVE', axis_forward='-Z', axis_up='Y')
    src = next(o for o in set(bpy.data.objects) - before if o.type == 'ARMATURE')
    sact = src.animation_data.action
    f_end = int(sact.frame_range[1])
    sw = src.matrix_world
    sp = src.pose.bones
    # reference T-pose (frame 1)
    scene.frame_set(1)
    ref = {s: (sw @ sp[s].matrix).to_quaternion() for s in MAP.values()}
    hips_ref = sw @ sp['Hips'].head
    ratio = (arm.matrix_world @ ab['pelvis'].head_local).z / max(hips_ref.z, 1e-3)
    # choose the frame range (source runs at 120 fps; we sample at 30 fps)
    contact = None
    if kick:  # strike frame = fastest foot movement
        best, prevp = 0, {}
        for f in range(2, f_end + 1):
            scene.frame_set(f)
            for s in ('LeftFoot', 'RightFoot'):
                p = sw @ sp[s].head
                if s in prevp:
                    v = (p - prevp[s]).length
                    if v > best: best, contact = v, f
                prevp[s] = p
        start, end = max(2, contact - int(0.55 * 120)), min(f_end, contact + int(0.65 * 120))
    elif window:
        start, end = max(2, int(window[0] * 120)), min(f_end, int(window[1] * 120))
    else:
        start, end = 2, f_end - loop_trim
    # A turns the source T-pose to face our -Y so bone deltas rotate about the right axes;
    # C then cancels whatever turn the performer made, so the clip faces forward at the key frame.
    face_frame = contact or (start + end) // 2
    yaw_ref = facing_yaw(src, 1)
    A = Quaternion((0, 0, 1), -math.pi / 2 - yaw_ref)
    C = Quaternion((0, 0, 1), -(facing_yaw(src, face_frame) - yaw_ref))
    CA, A_inv = C @ A, A.inverted()
    hips_start = None

    if name in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[name])
    act = bpy.data.actions.new(name); act.use_fake_user = True
    use_action(act)
    tw_inv = arm.matrix_world.to_quaternion().inverted()
    rest_q = {b.name: (arm.matrix_world @ b.matrix_local).to_quaternion() for b in ab}
    order = [b for b in ab]  # Blender lists bones parents-first
    out_frame = 0
    for f in range(start, end + 1, 4):
        scene.frame_set(f)
        D = {}
        for b in order:
            P = D.get(b.parent.name) if b.parent else None
            rest_rel = (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local
            chain = (P @ rest_rel) if P is not None else b.matrix_local.copy()
            s = MAP.get(b.name)
            if s:
                q_src = (sw @ sp[s].matrix).to_quaternion()
                q_world = CA @ q_src @ ref[s].inverted() @ A_inv @ rest_q[b.name]
                head = chain.translation.copy()
                if b.name == 'pelvis':
                    hp = sw @ sp['Hips'].head
                    if hips_start is None: hips_start = hp.copy()
                    d = CA @ ((hp - hips_start) * ratio)
                    if inplace: d.x = d.y = 0
                    d.z = (hp.z - hips_ref.z) * ratio
                    head = b.matrix_local.translation + (tw_inv @ d)
                D[b.name] = Matrix.Translation(head) @ (tw_inv @ q_world).to_matrix().to_4x4()
            else:
                D[b.name] = chain
            basis = chain.inverted() @ D[b.name]
            pb_ = pb[b.name]
            pb_.rotation_quaternion = basis.to_quaternion()
            pb_.location = basis.translation if b.name == 'pelvis' else Vector((0, 0, 0))
            pb_.keyframe_insert('rotation_quaternion', frame=out_frame, group=b.name)
            pb_.keyframe_insert('location', frame=out_frame, group=b.name)
        out_frame += 1
    arm.animation_data.action = None
    bpy.data.objects.remove(src)
    log(f'mocap {name}: {bvh} frames {start}-{end} -> {out_frame} keys' + (f', strike at key {(contact - start) // 4}' if contact else ''))

MOCAP = [  # (file, clip name, options)
    ('10_02.bvh', 'Kick', dict(kick=True)),
    ('16_35.bvh', 'Jog', dict(loop_trim=0)),
    ('79_69.bvh', 'Celebrate', dict(window=(0.5, 5.0))),
    ('79_71.bvh', 'No', dict(window=(0.5, 5.0))),
    ('77_02.bvh', 'Idle', dict(window=(1.0, 7.0))),
]
for f, n, opt in MOCAP:
    retarget(f, n, **opt)

# ---------------------------------------------------------------- preview renders (to check poses)
if RENDER:
    os.makedirs(RENDER_DIR, exist_ok=True)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.color_type = 'MATERIAL'
    scene.render.resolution_x, scene.render.resolution_y = 420, 520
    world = bpy.data.worlds.new('w'); scene.world = world
    cams = {}
    for name, loc in {'front': (0, -4.2, 1.0), 'side': (4.2, 0, 1.0)}.items():
        cd = bpy.data.cameras.new(name); cd.type = 'ORTHO'; cd.ortho_scale = 2.6
        co = bpy.data.objects.new(name, cd); scene.collection.objects.link(co)
        co.location = loc
        d = Vector((0, 0, 1.0)) - Vector(loc)
        co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cams[name] = co
    shots = [('Idle', 0, 'front')] + [('Kick', k, 'side') for k in range(0, 37, 4)] + [('Celebrate', 40, 'front'), ('No', 40, 'front'),
             ('Keeper_Dive', 0, 'front'), ('Keeper_Dive', 0, 'side'), ('Keeper_Dive', 10, 'front'),
             ('Wall_Jump', 0, 'front'), ('Wall_Jump', 10, 'front'), ('Jog', 6, 'side')]
    for act, frame, cam in shots:
        use_action(bpy.data.actions[act]); scene.frame_set(frame)
        scene.camera = cams[cam]
        scene.render.filepath = os.path.join(RENDER_DIR, f'{act}_{frame}_{cam}.png')
        bpy.ops.render.render(write_still=True)
    arm.animation_data.action = None
    log('renders in', RENDER_DIR)

# ---------------------------------------------------------------- shrink textures, export
for img in bpy.data.images:
    if img.size[0] > 1024:
        img.scale(1024, 1024)
use_action(bpy.data.actions['Idle'])
scene.frame_set(0)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type in ('ARMATURE', 'MESH'): o.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=OUT, export_format='GLB', use_selection=True,
    export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
    export_image_format='JPEG', export_jpeg_quality=82, export_yup=True,
)
log('exported', OUT, round(os.path.getsize(OUT) / 1e6, 2), 'MB')
