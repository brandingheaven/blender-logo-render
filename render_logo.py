import bpy
import sys
import os
import mathutils
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
for i, obj in enumerate(imported_objs):
    print(f"  Object {i+1}: {obj.name} (type: {obj.type})")

def convert_and_extrude(obj, extrude_depth, bevel_depth):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)

    if obj.type == 'CURVE':
        print(f"Converting {obj.name} to mesh...")
        bpy.ops.object.convert(target='MESH')

    solidify_mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify_mod.thickness = extrude_depth
    solidify_mod.offset = 0  

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
        "chrome": (0.1, 1.0),  
        "golden": (0.2, 1.0),
    }
    
    base_roughness, base_metallic = base_presets.get(texture_type, (0.5, 0.0))
    
    if texture_type == "golden":
        colors = [
            (1.000, 0.766, 0.336, 1.0),  
            (0.945, 0.776, 0.341, 1.0),
            (0.830, 0.686, 0.215, 1.0),
            (1.000, 0.598, 0.000, 1.0),
            (0.996, 0.882, 0.561, 1.0),
        ]
    elif texture_type == "chrome":
        colors = [
            (0.95, 0.95, 0.95, 1.0),  # Pure chrome white
            (0.98, 0.98, 0.98, 1.0),  # Bright chrome
            (0.92, 0.92, 0.92, 1.0),  # Slightly darker chrome
            (0.96, 0.96, 0.98, 1.0),  # Cool chrome
            (0.97, 0.97, 0.95, 1.0),  # Warm chrome
        ]
    else:
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
        
        if texture_type == "chrome":
            principled.inputs["Roughness"].default_value = 0.08 + (i * 0.02)  # Variation for flow effect
        elif num_objects > 1:
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

    direction = mathutils.Vector((0, 0, 0)) - camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()
    camera.data.lens = 50
    
    return camera

def setup_lighting(texture_type):
    def add_area_light(location, rotation, energy, size=3, color=(1.0, 1.0, 1.0)):
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.active_object
        light.data.energy = energy
        light.scale = (size, size, size)
        light.rotation_euler = rotation
        light.data.color = color
        return light

    warm_color = (1.0, 0.9, 0.8)
    cool_color = (0.8, 0.9, 1.0)

    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)

    if texture_type in ["gold", "golden"]:
        key_light  = add_area_light((0, -6, 5), (radians(60), 0, 0), 1400, 5, color=warm_color)
        fill_light = add_area_light((4, -4, 3), (radians(45), 0, radians(-30)), 500, 3, color=warm_color)
        rim_light  = add_area_light((0, 6, 3), (radians(-60), 0, 0), 800, 3, color=warm_color)

    elif texture_type in ["chrome", "metallic"]:
        key_light = add_area_light((0, -10, 8), (radians(35), 0, 0), 2500, 15, color=(1.0, 1.0, 1.0))
        fill_light = add_area_light((8, -6, 6), (radians(25), 0, radians(-45)), 1800, 12, color=(0.9, 0.95, 1.0))
        rim_light = add_area_light((0, 10, 4), (radians(-30), 0, 0), 1500, 12, color=(1.0, 1.0, 1.0))
        side_light = add_area_light((-8, 0, 5), (radians(45), 0, radians(90)), 1200, 10, color=(0.95, 0.95, 1.0))

    else:
        key_light  = add_area_light((0, -6, 4), (radians(60), 0, 0), 1000, 4)
        fill_light = add_area_light((4, -4, 2), (radians(45), 0, radians(-30)), 400, 3)
        rim_light  = add_area_light((0, 6, 3), (radians(-60), 0, 0), 600, 3)

    bpy.context.scene.world.use_nodes = True
    world_nodes = bpy.context.scene.world.node_tree.nodes
    bg_node = world_nodes.get('Background')

    if bg_node:
        if texture_type in ["chrome", "metallic"]:
            bg_strength = 0.3 
        elif texture_type in ["gold", "golden"]:
            bg_strength = 0.2
        else:
            bg_strength = 0.1
        bg_node.inputs[1].default_value = bg_strength


def animate_rotation(parent_obj, duration_frames=60):  # Much shorter animation
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
    scene.cycles.samples = 32   # Much faster rendering
    scene.cycles.use_denoising = False  # Disable denoising for speed
    scene.render.resolution_x = 640   # Much smaller for speed
    scene.render.resolution_y = 360   # Much smaller for speed
    scene.render.fps = 24
    
    # Optimize Cycles settings for speed
    scene.cycles.device = 'GPU'  # Force GPU rendering
    scene.cycles.tile_size = 256  # Larger tiles for GPU
    
    # Debug GPU detection
    print("=== GPU Debug Info ===")
    print(f"Cycles device: {scene.cycles.device}")
    
    # Set GPU compute device
    prefs = bpy.context.preferences
    cycles_prefs = prefs.addons['cycles'].preferences
    
    print(f"Available compute device types: {[d.type for d in cycles_prefs.devices]}")
    print(f"Number of devices: {len(cycles_prefs.devices)}")
    
    # Try different compute device types
    for compute_type in ['CUDA', 'OPTIX', 'OPENCL']:
        try:
            cycles_prefs.compute_device_type = compute_type
            print(f"Set compute device type to: {compute_type}")
            break
        except:
            print(f"Failed to set compute device type to: {compute_type}")
    
    # Enable all available GPUs
    enabled_devices = 0
    for device in cycles_prefs.devices:
        device.use = True
        enabled_devices += 1
        print(f"Enabled device: {device.name} (type: {device.type})")
    
    print(f"Total enabled devices: {enabled_devices}")
    
    if enabled_devices == 0:
        print("WARNING: No GPU devices found! Falling back to CPU")
        scene.cycles.device = 'CPU'
    else:
        print("Using GPU rendering")
    
    print("=== End GPU Debug Info ===")
    
    scene.cycles.use_adaptive_sampling = False  # Disable for speed
    scene.cycles.adaptive_threshold = 0.1
    scene.cycles.adaptive_min_samples = 16
    
    scene.render.filepath = os.path.join(output_dir, "rendered_animation.mp4")
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.image_settings.color_mode = 'RGB'
    
    scene.render.film_transparent = False  
    
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'  # Changed from HIGH for faster encoding
    scene.render.ffmpeg.ffmpeg_preset = 'REALTIME'       # Changed from GOOD for faster encoding
    scene.render.ffmpeg.video_bitrate = 4000             # Reduced from 8000
    scene.render.ffmpeg.max_b_frames = 2

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
setup_lighting(texture_type)

print("Setting up animation...")
animate_rotation(parent_object)

print("Configuring render...")
configure_render(output_dir)

print("Starting render...")
print(f"Rendering {bpy.context.scene.frame_end} frames at {bpy.context.scene.render.resolution_x}x{bpy.context.scene.render.resolution_y}...")
print(f"Using {bpy.context.scene.cycles.samples} samples per frame...")

# Add progress callback
def render_progress(scene):
    if scene.frame_current % 10 == 0:  # Print every 10 frames
        progress = (scene.frame_current - scene.frame_start) / (scene.frame_end - scene.frame_start) * 100
        print(f"Rendering progress: {progress:.1f}% (Frame {scene.frame_current}/{scene.frame_end})")

# Register the callback
bpy.app.handlers.render_pre.append(render_progress)

bpy.ops.render.render(animation=True)

print("Rendering Complete!")
print(f"Output saved to: {bpy.context.scene.render.filepath}")
print(f"Total objects processed: {len(imported_objs)}")
print(f"Materials created: {len(materials)}")
