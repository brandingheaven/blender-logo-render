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

# Clear scene
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
for i, obj in enumerate(imported_objs):
    print(f"  Object {i+1}: {obj.name} (type: {obj.type})")

def convert_and_extrude(obj, extrude_depth, bevel_depth):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)

    if obj.type == 'CURVE':
        print(f"Converting {obj.name} to mesh...")
        bpy.ops.object.convert(target='MESH')

    # Add Solidify Modifier
    solidify_mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify_mod.thickness = extrude_depth
    solidify_mod.offset = 0  # Center the extrusion

    # Add Bevel Modifier for smooth edges
    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = bevel_depth
    bevel_mod.segments = 3
    bevel_mod.limit_method = 'ANGLE'

def create_materials(texture_type, num_objects):
    materials = []
    
    base_presets = {
        "flat": (1.0, 0.0),
        "glossy": (0.1, 0.0), 
        "matte": (0.8, 0.0),
        "metallic": (0.3, 1.0),
        "chrome": (0.05, 1.0),
    }
    
    base_roughness, base_metallic = base_presets.get(texture_type, (0.5, 0.0))
    
    # Color variations for multiple objects
    colors = [
        (0.8, 0.8, 0.8, 1.0),  # Light gray
        (0.9, 0.9, 0.9, 1.0),  # White
        (0.7, 0.7, 0.7, 1.0),  # Medium gray
        (0.6, 0.6, 0.6, 1.0),  # Dark gray
        (0.85, 0.85, 0.85, 1.0), # Very light gray
    ]
    
    for i in range(num_objects):
        mat = bpy.data.materials.new(name=f"{texture_type.capitalize()}Material_{i+1}")
        mat.use_nodes = True
        principled = mat.node_tree.nodes.get("Principled BSDF")
        
        principled.inputs["Roughness"].default_value = base_roughness
        principled.inputs["Metallic"].default_value = base_metallic
        
        color_index = i % len(colors)
        principled.inputs["Base Color"].default_value = colors[color_index]
        
        if num_objects > 1:
            roughness_variation = (i * 0.1) % 0.3
            principled.inputs["Roughness"].default_value = min(1.0, base_roughness + roughness_variation)
        
        materials.append(mat)
    
    return materials

def group_objects():
    bpy.ops.object.select_all(action='DESELECT')
    
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    parent_empty = bpy.context.active_object
    parent_empty.name = "SVG_Group"
    
    for obj in imported_objs:
        obj.select_set(True)
    
    parent_empty.select_set(True)
    bpy.context.view_layer.objects.active = parent_empty
    bpy.ops.object.parent_set(type='OBJECT')
    
    return parent_empty

def transform_objects(target_size=2.0):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in imported_objs:
        obj.select_set(True)
    
    # Set origins to geometry
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    
    # Reset transforms
    for obj in imported_objs:
        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        obj.scale = (1, 1, 1)

    # calculate scaling    
    max_dim = 0
    for obj in imported_objs:
        obj_max_dim = max(obj.dimensions)
        if obj_max_dim > max_dim:
            max_dim = obj_max_dim
    
    if max_dim != 0:
        scale_factor = target_size / max_dim
        print(f"Scaling all objects by factor: {scale_factor}")
        for obj in imported_objs:
            obj.scale = (scale_factor, scale_factor, scale_factor)
    
    parent_empty = group_objects()
    
    return parent_empty

def apply_materials(materials):
    for i, obj in enumerate(imported_objs):
        material_index = i % len(materials)
        material = materials[material_index]
        
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
        
        print(f"Applied material {material.name} to {obj.name}")

def setup_camera():
    bpy.ops.object.camera_add(location=(0, -8, 2))
    camera = bpy.context.active_object
    camera.rotation_euler = (radians(70), 0, 0)
    bpy.context.scene.camera = camera
    
    camera.data.lens = 50
    
    return camera

def setup_lighting():
    def add_area_light(location, rotation, energy, size=3):
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.active_object
        light.data.energy = energy
        light.scale = (size, size, size)
        light.rotation_euler = rotation
        return light

    key_light = add_area_light((0, -6, 4), (radians(60), 0, 0), 1000, 4)
    
    fill_light = add_area_light((4, -4, 2), (radians(45), 0, radians(-30)), 300, 3)
    
    rim_light = add_area_light((0, 6, 3), (radians(-60), 0, 0), 400, 2)    
    bpy.context.scene.world.use_nodes = True
    world_nodes = bpy.context.scene.world.node_tree.nodes
    bg_node = world_nodes.get('Background')
    if bg_node:
        bg_node.inputs[1].default_value = 0.1  # Subtle ambient light

def animate_rotation(parent_obj, duration_frames=240):
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = duration_frames
    parent_obj.animation_data_clear()
    parent_obj.rotation_euler = (radians(90), 0, 0)
    parent_obj.keyframe_insert(data_path="rotation_euler", frame=1)    
    parent_obj.rotation_euler = (radians(90), radians(360), 0)
    parent_obj.keyframe_insert(data_path="rotation_euler", frame=duration_frames)
    
    # Set interpolation 
    if parent_obj.animation_data and parent_obj.animation_data.action:
        for fcurve in parent_obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'LINEAR'

def configure_render(output_dir):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 4096
    scene.cycles.use_denoising = True      
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.fps = 24
    
    scene.render.filepath = os.path.join(output_dir, "frame_")
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    os.makedirs(output_dir, exist_ok=True)

# Main processing pipeline
print("Processing objects...")
for i, obj in enumerate(imported_objs):
    print(f"Processing object {i+1}/{len(imported_objs)}: {obj.name}")
    convert_and_extrude(obj, extrude_depth, bevel_depth)

print("Creating materials...")
materials = create_materials(texture_type, len(imported_objs))

print("Applying materials...")
apply_materials(materials)

print("Transforming objects...")
parent_object = transform_objects()

print("Setting up camera...")
camera = setup_camera()

print("Setting up lighting...")
setup_lighting()

print("Setting up animation...")
animate_rotation(parent_object)

print("Configuring render...")
configure_render(output_dir)

print("Starting render...")
print(f"Rendering {bpy.context.scene.frame_end} frames...")
bpy.ops.render.render(animation=True)

print("Rendering Complete!")
print(f"Output saved to: {bpy.context.scene.render.filepath}")
print(f"Total objects processed: {len(imported_objs)}")
print(f"Materials created: {len(materials)}")   
