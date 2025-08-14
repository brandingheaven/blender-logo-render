import bpy
import sys
import os
import mathutils
from math import radians
import subprocess


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:]
    svg_path = argv[0]
    output_dir = argv[1]
    texture_type = argv[2].lower()
    extrude_depth = float(argv[3])
    bevel_depth = float(argv[4])
    transparency = argv[5].lower() if len(argv) > 5 else "opaque"
    return svg_path, output_dir, texture_type, extrude_depth, bevel_depth, transparency


bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

svg_path, output_dir, texture_type, extrude_depth, bevel_depth, transparency = parse_args()
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
            principled.inputs["Roughness"].default_value = 0.08 + (i * 0.02)  
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
    bpy.ops.object.camera_add(location=(0, -8, 0))
    camera = bpy.context.active_object
    camera.rotation_euler = (radians(90), 0, 0)  
    bpy.context.scene.camera = camera
    camera.data.lens = 50
    
    return camera

def setup_transparent_world():
    """Ensure world background is completely transparent"""
    scene = bpy.context.scene
    
    # Enable world nodes
    scene.world.use_nodes = True
    world_nodes = scene.world.node_tree.nodes
    
    # Get or create background node
    bg_node = world_nodes.get('Background')
    if not bg_node:
        bg_node = world_nodes.new(type='ShaderNodeBackground')
    
    # Set background to transparent
    bg_node.inputs['Color'].default_value = (0.0, 0.0, 0.0, 0.0)  # RGBA with 0 alpha
    bg_node.inputs['Strength'].default_value = 0.0  # No emission
    
    print("World background set to transparent")

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


def animate_rotation(parent_obj, duration_frames=240): 
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = duration_frames
    parent_obj.animation_data_clear()
    
    parent_obj.rotation_euler = (radians(90), 0, 0)
    parent_obj.keyframe_insert(data_path="rotation_euler", frame=1)    
    
    parent_obj.rotation_euler = (radians(90), 0, radians(360))
    parent_obj.keyframe_insert(data_path="rotation_euler", frame=duration_frames)
    
    # Set interpolation to linear
    if parent_obj.animation_data and parent_obj.animation_data.action:
        for fcurve in parent_obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'LINEAR'

def configure_render(output_dir, transparency="opaque", quality_mode="final"):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'

    if quality_mode == "preview":
        scene.cycles.samples = 256
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720
        scene.cycles.adaptive_threshold = 0.05
        ffmpeg_preset = 'GOOD'
    else:  # "final"
        scene.cycles.samples = 2048
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.cycles.adaptive_threshold = 0.01
        ffmpeg_preset = 'SLOW'

    scene.cycles.use_denoising = True
    scene.render.fps = 30

    # GPU settings
    scene.cycles.device = 'GPU'
    scene.cycles.tile_size = 128
    prefs = bpy.context.preferences
    cycles_prefs = prefs.addons['cycles'].preferences
    for compute_type in ['CUDA', 'OPTIX', 'OPENCL']:
        try:
            cycles_prefs.compute_device_type = compute_type
            break
        except:
            pass
    for device in cycles_prefs.devices:
        device.use = True

    # Transparency or not
    if transparency == "transparent":
        scene.render.film_transparent = True
        
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.image_settings.color_depth = '16'
        scene.render.image_settings.compression = 15
        
        scene.render.filepath = os.path.join(output_dir, "frame_")
        
        print(f"PNG sequence will be saved as: {scene.render.filepath}####.png")

    else:
        scene.render.film_transparent = False
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'HIGH'
        scene.render.ffmpeg.audio_codec = 'NONE'
        
        scene.render.filepath = os.path.join(output_dir, "rendered_animation.mp4")

    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_min_samples = 64
    scene.render.ffmpeg.ffmpeg_preset = ffmpeg_preset

    os.makedirs(output_dir, exist_ok=True)


    print(f"Render output path: {scene.render.filepath}")
    print(f"Render mode: {quality_mode}")
    print(f"Transparency: {transparency}")


def convert_png_to_webm(output_dir, fps=30):
    """Convert PNG sequence to transparent WEBM using FFmpeg"""
    
    # Check if FFmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: FFmpeg not found! Please install FFmpeg to convert PNG sequence to WEBM.")
        print("PNG sequence remains at:", os.path.join(output_dir, "frame_*.png"))
        return False
    
    # Convert to absolute path and normalize
    output_dir = os.path.abspath(output_dir)
    
    # Check what PNG files actually exist
    import glob
    png_files = glob.glob(os.path.join(output_dir, "frame_*.png"))
    if not png_files:
        print(f"No PNG files found in {output_dir}")
        return False
    
    print(f"Found {len(png_files)} PNG files")
    png_files.sort()  # Sort to ensure proper order
    
    # Use absolute path for input pattern
    input_pattern = os.path.join(output_dir, "frame_%04d.png").replace('\\', '/')
    output_path = os.path.join(output_dir, "rendered_animation_transparent.webm")
    
    # Try multiple FFmpeg approaches for transparency
    
    # Method 1: Explicit alpha handling with filter
    cmd1 = [
        'ffmpeg',
        '-y',
        '-framerate', str(fps),
        '-i', input_pattern,
        '-vf', 'format=yuva420p',  # Force conversion to alpha format
        '-c:v', 'libvpx-vp9',
        '-crf', '20',
        '-b:v', '0',
        '-auto-alt-ref', '0',
        output_path
    ]
    
    # Method 2: Alternative with different pixel format handling
    cmd2 = [
        'ffmpeg',
        '-y',
        '-framerate', str(fps),
        '-i', input_pattern,
        '-c:v', 'libvpx-vp9',
        '-pix_fmt', 'yuva420p',
        '-vf', 'premultiply=inplace=1',  # Handle alpha premultiplication
        '-crf', '20',
        '-b:v', '0',
        '-auto-alt-ref', '0',
        output_path
    ]
    
    # Method 3: Simple approach focusing on alpha
    cmd3 = [
        'ffmpeg',
        '-y',
        '-framerate', str(fps),
        '-i', input_pattern,
        '-c:v', 'libvpx-vp9',
        '-pix_fmt', 'yuva420p',
        '-crf', '15',
        '-b:v', '0',
        '-f', 'webm',
        output_path
    ]
    
    print("Converting PNG sequence to transparent WEBM...")
    print(f"Input pattern: {input_pattern}")
    print(f"Output: {output_path}")
    
    commands = [
        ("Method 1 (format filter)", cmd1),
        ("Method 2 (premultiply)", cmd2), 
        ("Method 3 (simple)", cmd3)
    ]
    
    for method_name, cmd in commands:
        print(f"\nTrying {method_name}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ {method_name} succeeded!")
                
                # Verify the output has alpha
                verify_cmd = ['ffmpeg', '-i', output_path]
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
                
                if 'yuva420p' in verify_result.stderr:
                    print("✅ Verified: Output contains alpha channel (yuva420p)")
                    
                    # Optionally clean up PNG files
                    response = input("Delete PNG sequence files? (y/n): ").lower().strip()
                    if response == 'y':
                        for png_file in png_files:
                            try:
                                os.remove(png_file)
                                print(f"Deleted: {os.path.basename(png_file)}")
                            except OSError:
                                pass
                        print("PNG cleanup completed.")
                    
                    return True
                else:
                    print(f"⚠️ {method_name} succeeded but output may not have alpha channel")
                    print("Output info:")
                    print(verify_result.stderr[-500:])  # Show last 500 chars
            else:
                print(f"❌ {method_name} failed:")
                print("STDERR:", result.stderr[-300:])  # Show last 300 chars
                
        except subprocess.TimeoutExpired:
            print(f"❌ {method_name} timed out!")
        except Exception as e:
            print(f"❌ {method_name} error: {e}")
    
    # If all methods failed
    print("\n❌ All conversion methods failed!")
    print("Your PNG files have transparency, but FFmpeg couldn't create a transparent WEBM.")
    

    return False


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
configure_render(output_dir, transparency, quality_mode="preview") # quick tests



print("Starting render...")
print(f"Rendering {bpy.context.scene.frame_end} frames at {bpy.context.scene.render.resolution_x}x{bpy.context.scene.render.resolution_y}...")
print(f"Using {bpy.context.scene.cycles.samples} samples per frame...")
print(f"Output format: {bpy.context.scene.render.image_settings.file_format}")
print(f"Color mode: {bpy.context.scene.render.image_settings.color_mode}")
print(f"Film transparent: {bpy.context.scene.render.film_transparent}")
print(f"Render filepath: {bpy.context.scene.render.filepath}")

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)
print(f"Output directory created/exists: {os.path.abspath(output_dir)}")

# Add progress callback
def render_progress(scene):
    if scene.frame_current % 10 == 0:  # Print every 10 frames
        progress = (scene.frame_current - scene.frame_start) / (scene.frame_end - scene.frame_start) * 100
        print(f"Rendering progress: {progress:.1f}% (Frame {scene.frame_current}/{scene.frame_end})")

# Register the callback
bpy.app.handlers.render_pre.append(render_progress)

bpy.ops.render.render(animation=True)

print("Rendering Complete!")

# Debug: Check what files were actually created
if transparency == "transparent":
    print("Checking for generated PNG files...")
    import glob
    png_pattern = os.path.join(output_dir, "*.png")
    png_files = glob.glob(png_pattern)
    print(f"Found {len(png_files)} PNG files:")
    for png_file in png_files[:5]:  # Show first 5 files
        print(f"  - {os.path.basename(png_file)}")
    if len(png_files) > 5:
        print(f"  ... and {len(png_files) - 5} more")

# Convert PNG sequence to WEBM if transparency was requested
if transparency == "transparent":
    if len(png_files) > 0:
        print("Converting PNG sequence to transparent WEBM...")
        success = convert_png_to_webm(output_dir, fps=bpy.context.scene.render.fps)
        if success:
            print("Conversion completed successfully!")
        else:
            print("Conversion failed. PNG sequence files are available in:", output_dir)
    else:
        print("No PNG files found - skipping conversion")
        print(f"Expected files at: {png_pattern}")
else:
    print(f"Output saved to: {bpy.context.scene.render.filepath}")

print(f"Total objects processed: {len(imported_objs)}")
print(f"Materials created: {len(materials)}")
