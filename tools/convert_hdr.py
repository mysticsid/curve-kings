# Converts the stadium HDRI to a JPG (the artifact host doesn't serve .hdr).
# Run: .\blender.exe -b --factory-startup -P tools\convert_hdr.py
import bpy, os
GAME = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
img = bpy.data.images.load(os.path.join(GAME, 'assets', 'stadium_1k.hdr'))
scene = bpy.context.scene
scene.view_settings.view_transform = 'Standard'
scene.view_settings.exposure = 0.0
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 88
img.save_render(os.path.join(GAME, 'assets', 'stadium_env.jpg'), scene=scene)
print('[hdr] saved stadium_env.jpg')
