# Extracts evenly spaced frames from a video into a contact sheet set (uses Blender's video decoder).
import bpy, sys, os
src, out = sys.argv[sys.argv.index('--') + 1:][:2]
os.makedirs(out, exist_ok=True)
clip = bpy.data.movieclips.load(src)
n, fps = clip.frame_duration, clip.fps
print('[frames] duration', n, 'fps', fps, 'size', tuple(clip.size))
scene = bpy.context.scene
scene.sequence_editor_create()
strip = scene.sequence_editor.strips.new_movie('v', src, 1, 1) if hasattr(scene.sequence_editor, 'strips') else scene.sequence_editor.sequences.new_movie('v', src, 1, 1)
scene.render.resolution_x, scene.render.resolution_y = clip.size[0] // 2, clip.size[1] // 2
scene.render.image_settings.file_format = 'JPEG'
scene.render.use_sequencer = True
count = 24
for i in range(count):
    f = 1 + int(i * (n - 2) / (count - 1))
    scene.frame_set(f)
    scene.render.filepath = os.path.join(out, f'f{i:02d}_{f / fps:05.1f}s.jpg')
    bpy.ops.render.render(write_still=True)
print('[frames] done')
