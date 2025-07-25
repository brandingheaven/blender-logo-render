import bpy
import sys
import os

logo_path = sys.argv[-1]
output_path = "/output/spinning_logo.mp4"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.import_image.to_plane(files=[{"name": os.path.basename(logo_path)}], directory=os.path.dirname(logo_path))
logo_obj = bpy.context.selected_objects[0]

bpy.context.view_layer.objects.active = logo_obj
bpy.ops.object.convert(target='MESH')
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 0.05)})
bpy.ops.object.mode_set(mode='OBJECT')

mat = bpy.data.materials.new(name="ChromeMaterial")
mat.metallic = 1.0
mat.roughness = 0.1
logo_obj.data.materials.append(mat)

bpy.ops.object.camera_add(location=(0, -2, 1), rotation=(1.2, 0, 0))
camera = bpy.context.object
bpy.context.scene.camera = camera

bpy.ops.object.light_add(type='AREA', location=(2, -2, 2))
bpy.context.object.data.energy = 1000

logo_obj.rotation_euler = (0, 0, 0)
logo_obj.keyframe_insert(data_path="rotation_euler", frame=1)
logo_obj.rotation_euler = (0, 0, 6.28319)
logo_obj.keyframe_insert(data_path="rotation_euler", frame=120)

bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 120
bpy.context.scene.render.filepath = output_path

bpy.ops.render.render(animation=True)
