import bpy
import sys
import os

logo_path = "C:/Users/JANE/Documents/dev/projects/blender-logo-render-proj/logo1.svg"
output_path = "C:/Users/JANE/Documents/dev/projects/blender-logo-render-proj/blender-logo-render/frames/test-run1/frame_"

os.makedirs(os.path.dirname(output_path), exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Import SVG and check if it worked
try:
    bpy.ops.import_curve.svg(filepath=logo_path)
    print(f"SVG import completed. Objects in scene: {[obj.name for obj in bpy.context.scene.objects]}")
except Exception as e:
    print(f"Error importing SVG: {e}")
    sys.exit(1)

# Check if any objects were imported
if not bpy.context.selected_objects:
    print("No objects were selected after SVG import. Checking all objects in scene...")
    imported_objects = [obj for obj in bpy.context.scene.objects if obj.type in ['CURVE', 'MESH']]
    if imported_objects:
        print(f"Found imported objects: {[obj.name for obj in imported_objects]}")
        logo_obj = imported_objects[0]
        logo_obj.select_set(True)
        bpy.context.view_layer.objects.active = logo_obj
    else:
        print("No objects found in scene. Checking if SVG file exists...")
        if not os.path.exists(logo_path):
            print(f"SVG file not found at: {logo_path}")
        else:
            print("SVG file exists but no objects were imported. This might be due to SVG content issues.")
        sys.exit(1)
else:
    logo_obj = bpy.context.selected_objects[0]
    print(f"Selected logo object: {logo_obj.name}")

bpy.context.view_layer.objects.active = logo_obj
logo_obj.select_set(True)

logo_obj.rotation_euler = (1.5708, 0, 0)  

try:
    bpy.ops.object.convert(target='MESH')
    print("Successfully converted curve to mesh")
except Exception as e:
    print(f"Error converting to mesh: {e}")
    sys.exit(1)

bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.selected_objects:
    obj.select_set(False)
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
bpy.ops.object.join()
logo_obj = bpy.context.active_object

solidify = logo_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
solidify.thickness = 0.05
bpy.ops.object.modifier_apply(modifier="Solidify")

mat = bpy.data.materials.new(name="ChromeMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

for node in nodes:
    nodes.remove(node)

output_node = nodes.new(type='ShaderNodeOutputMaterial')
principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')

principled_node.inputs['Metallic'].default_value = 1.0
principled_node.inputs['Roughness'].default_value = 0.1
principled_node.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1)

links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])

logo_obj.data.materials.append(mat)

bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
logo_obj.location = (0, 0, 0)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
logo_obj.scale = (1, 1, 1)

bpy.ops.object.camera_add(location=(0, -3, 1), rotation=(1.2, 0, 0))
camera = bpy.context.object
bpy.context.scene.camera = camera

bpy.ops.object.light_add(type='AREA', location=(2, -2, 2))
light = bpy.context.object
light.data.energy = 1000

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
bpy.context.scene.render.film_transparent = True  
bpy.context.scene.render.filepath = output_path
bpy.context.scene.render.image_settings.file_format = 'PNG'  

bpy.ops.render.render(animation=True)
