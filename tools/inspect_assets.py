# Run with: blender -b --factory-startup -P tools/inspect_assets.py
# Prints the armatures, meshes and animation names in the downloaded packs.
import bpy, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'downloads')
CHAR = os.path.join(ROOT, 'base-characters', 'Universal Base Characters[Standard]', 'Base Characters', 'Godot - UE', 'Superhero_Male_FullBody.gltf')
ANIM = os.path.join(ROOT, 'animation-library-2', 'Universal Animation Library 2[Standard]', 'Unreal-Godot', 'UAL2_Standard.glb')

def report(label):
    print(f'===== {label}')
    for ob in bpy.data.objects:
        info = ''
        if ob.type == 'MESH':
            info = f'tris~{sum(len(p.vertices) - 2 for p in ob.data.polygons)} mats={[m.name for m in ob.data.materials if m]}'
        if ob.type == 'ARMATURE':
            info = f'bones={len(ob.data.bones)} first={[b.name for b in ob.data.bones][:12]}'
        dims = tuple(round(d, 2) for d in ob.dimensions)
        print(f'  {ob.type:9} {ob.name:40} dims={dims} {info}')
    print('  ACTIONS:', len(bpy.data.actions))
    for a in bpy.data.actions:
        print(f'    {a.name}  frames={tuple(int(f) for f in a.frame_range)}')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=CHAR)
report('CHARACTER')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ANIM)
report('ANIMATIONS')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ANIM.replace('animation-library-2', 'animation-library-1').replace('Library 2[', 'Library[').replace('UAL2', 'UAL1'))
report('ANIMATIONS 1')
