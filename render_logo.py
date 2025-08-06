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

if not os.path.exists(svg_path):
    print(f"Error: SVG file does not exist at {svg_path}")
    sys.exit(1)

print("Importing SVG...")
bpy.ops.import_curve.svg(filepath=svg_path)

all_objects = list(bpy.context.scene.objects)
imported_objs = [obj for obj in all_objects if obj.type in ['CURVE', 'MESH']]

if not imported_objs:
    print("Error: No usable objects imported!")
    sys.exit(1)

print(f"Imported {len(imported_objs)} objects")

def convert_and_extrude(obj, extrude_depth, bevel_depth):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    if obj.type == 'CURVE':
        bpy.ops.object.convert(target='MESH')

    # Add Solidify Modifier
    solidify_mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify_mod.thickness = extrude_depth

    # Add Bevel Modifier
    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = bevel_depth
    bevel_mod.segments = 5

def create_material(texture_type):
    mat = bpy.data.materials.new(name=f"{texture_type.capitalize()}Material")
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF")

    presets = {
        "flat": (1.0, 0.0),
        "glossy": (0.1, 0.0),
        "matte": (0.8, 0.0),
        "metallic": (0.3, 1.0),
        "chrome": (0.05, 1.0),
    }

    roughness, metallic = presets.get(texture_type, (0.5, 0.0))
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic

    return mat

def transform_objects(target_size=2.0):
    for obj in imported_objs:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        # Set Origin to Geometry
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

        # Reset Location & Scale
        obj.location = (0, 0, 0)
        obj.scale = (1, 1, 1)

    max_dim = max(max(obj.dimensions) for obj in imported_objs)
    if max_dim != 0:
        scale_factor = target_size / max_dim
        for obj in imported_objs:
            obj.scale = (scale_factor, scale_factor, scale_factor)

    # Rotate objects to face the camera
    # for obj in imported_objs:
    #     obj.rotation_euler[0] = radians(-90)

def apply_materials(material):
    for obj in imported_objs:
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

def setup_camera():
    bpy.ops.object.camera_add(location=(0, -10, 3))
    camera = bpy.context.active_object
    camera.rotation_euler = (radians(75), 0, 0)
    bpy.context.scene.camera = camera

def setup_lighting():
    def add_area_light(location, rotation, energy):
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.active_object
        light.data.energy = energy
        light.scale = (2, 2, 2)
        light.rotation_euler = rotation

    add_area_light((0, -6, 2), (radians(90), 0, 0), 800)  # Key Light
    add_area_light((3, -6, 2), (radians(90), 0, radians(-15)), 200)  # Fill Light
    add_area_light((0, 4, 3), (radians(-90), 0, 0), 200)  # Rim Light

def animate_rotation(obj, duration_frames=240):
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = duration_frames
    obj.rotation_euler = (radians(90), 0, 0)  # Start facing camera
    obj.keyframe_insert(data_path="rotation_euler", frame=1)
    obj.rotation_euler = (radians(90), radians(360), 0)  # Rotate around Y while facing camera
    obj.keyframe_insert(data_path="rotation_euler", frame=duration_frames)

def configure_render(output_dir):
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 32
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.fps = 24
    bpy.context.scene.render.filepath = os.path.join(output_dir, "frame_")
    bpy.context.scene.render.image_settings.file_format = 'PNG'

# main process
print("Processing objects...")
for obj in imported_objs:
    convert_and_extrude(obj, extrude_depth, bevel_depth)

print("Creating material...")
material = create_material(texture_type)

print("Applying material...")
apply_materials(material)

print("Transforming objects...")
transform_objects()

print("Setting up camera & lights...")
setup_camera()
setup_lighting()

print("Animating rotation...")
animate_rotation(imported_objs[0])

print("Configuring render...")
configure_render(output_dir)

print("Rendering animation...")
bpy.ops.render.render(animation=True)

print("Rendering Complete. Output saved to:", bpy.context.scene.render.filepath)
