import bpy
import sys
import os
from math import radians

def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:]  
    svg_path = argv[0]
    output_dir = argv[1]
    texture_type = argv[2].lower()
    extrude_depth = float(argv[3])
    bevel_depth = float(argv[4])
    return svg_path, output_dir, texture_type, extrude_depth, bevel_depth

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

svg_path, output_dir, texture_type, extrude_depth, bevel_depth = parse_args()

bpy.ops.import_curve.svg(filepath=svg_path)
imported_objs = bpy.context.selected_objects

def convert_and_extrude(obj, extrude_depth, bevel_depth):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    solidify_mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify_mod.thickness = extrude_depth
    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = bevel_depth
    bevel_mod.segments = 5

def create_material(texture_type):
    mat = bpy.data.materials.new(name=texture_type.capitalize() + "Material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    principled = nodes.get("Principled BSDF")

    if not principled:
        print("Principled BSDF node not found!")
        return mat  

    if texture_type == "flat":
        principled.inputs["Roughness"].default_value = 1.0
        principled.inputs["Metallic"].default_value = 0.0
    elif texture_type == "glossy":
        principled.inputs["Roughness"].default_value = 0.1
        principled.inputs["Metallic"].default_value = 0.0
    elif texture_type == "matte":
        principled.inputs["Roughness"].default_value = 0.8
        principled.inputs["Metallic"].default_value = 0.0
    elif texture_type == "metallic":
        principled.inputs["Roughness"].default_value = 0.3
        principled.inputs["Metallic"].default_value = 1.0
    elif texture_type == "chrome":
        principled.inputs["Roughness"].default_value = 0.05
        principled.inputs["Metallic"].default_value = 1.0
    else:
        principled.inputs["Roughness"].default_value = 0.5  

    return mat

def apply_material(obj, material):
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)

def center_and_scale_objects(target_size=2.0):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    bpy.ops.object.location_clear()
    bpy.ops.object.rotation_clear()
    bpy.ops.object.scale_clear()
    # Compute bounding box dimensions
    max_dim = max(obj.dimensions.length for obj in bpy.context.selected_objects)

    if max_dim != 0:
        scale_factor = target_size / max_dim
        bpy.ops.transform.resize(value=(scale_factor, scale_factor, scale_factor))

def setup_camera():
    bpy.ops.object.camera_add(location=(0, -10, 3))
    camera = bpy.context.active_object
    camera.rotation_euler = (radians(75), 0, 0)
    bpy.context.scene.camera = camera

def setup_lighting():
    # key light
    bpy.ops.object.light_add(type='AREA', location=(0, -6, 2))
    key_light = bpy.context.active_object
    key_light.data.energy = 800
    key_light.scale = (2, 2, 2)
    key_light.rotation_euler = (radians(90), 0, 0)  

    # fill light
    bpy.ops.object.light_add(type='AREA', location=(3, -6, 2))
    fill_light = bpy.context.active_object
    fill_light.data.energy = 200
    fill_light.scale = (2, 2, 2)
    fill_light.rotation_euler = (radians(90), 0, radians(-15))  

    # rim light
    bpy.ops.object.light_add(type='AREA', location=(0, 4, 3))
    rim_light = bpy.context.active_object
    rim_light.data.energy = 200
    rim_light.scale = (2, 2, 2)
    rim_light.rotation_euler = (radians(-90), 0, 0)  


def animate_rotation(obj, duration_frames=240):
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = duration_frames
    obj.rotation_euler = (0, 0, 0)
    obj.keyframe_insert(data_path="rotation_euler", frame=1)
    obj.rotation_euler = (radians(360), 0, 0)
    obj.keyframe_insert(data_path="rotation_euler", frame=duration_frames)

def configure_render(output_dir):
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 4096
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.fps = 24
    bpy.context.scene.render.filepath = os.path.join(output_dir, "frame_")
    bpy.context.scene.render.image_settings.file_format = 'PNG'

def final_set_up(output_dir):
    setup_camera()
    setup_lighting()
    animate_rotation(imported_objs[0])
    configure_render(output_dir)

# Run processing steps
for obj in imported_objs:
    convert_and_extrude(obj, extrude_depth, bevel_depth)

material = create_material(texture_type)
for obj in imported_objs:
    apply_material(obj, material)

center_and_scale_objects()
final_set_up(output_dir)

bpy.ops.render.render(animation=True)

print("Rendering Complete. Output saved to:", bpy.context.scene.render.filepath)
