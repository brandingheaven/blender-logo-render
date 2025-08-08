import runpod
import base64
import tempfile
import subprocess
import os
import json
import time
from typing import Optional

def handler(event):
    """
    Serverless worker handler for Blender logo rendering
    """
    print("=== Blender Logo Render Worker Started ===")
    
    try:
        # Extract input data
        input_data = event['input']
        
        logo = input_data.get('logo')
        material = input_data.get('material', 'golden')
        extrude_depth = float(input_data.get('extrude_depth', 0.1))
        bevel_depth = float(input_data.get('bevel_depth', 0.02))
        
        print(f"Processing render with material: {material}")
        print(f"Extrude depth: {extrude_depth}, Bevel depth: {bevel_depth}")
        
        # Get timeout from environment variable
        timeout_seconds = int(os.getenv('BLENDER_TIMEOUT_SECONDS', 1200))  # Default 20 minutes
        print(f"Using timeout: {timeout_seconds} seconds")
        
        # Validate material
        valid_materials = ["flat", "glossy", "matte", "metallic", "chrome", "golden"]
        if material not in valid_materials:
            return {"error": f"Invalid material. Choose from: {valid_materials}"}
        
        # Decode base64 image
        try:
            # Remove data URL prefix if present
            if logo.startswith('data:'):
                logo = logo.split(',')[1]
            
            image_data = base64.b64decode(logo)
            print(f"Successfully decoded base64, image data length: {len(image_data)}")
        except Exception as e:
            return {"error": f"Invalid base64 image data: {str(e)}"}
        
        # Create temporary file for the logo
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as temp_file:
            temp_file.write(image_data)
            logo_path = temp_file.name
        
        # Create output directory
        output_dir = "/tmp/output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Clear previous output files
        for file in os.listdir(output_dir):
            if file.startswith("frame_") and file.endswith(".png"):
                os.remove(os.path.join(output_dir, file))
        
        # Get Blender path
        blender_paths = [
            "/usr/local/bin/blender",
            "/opt/blender-3.6.0-linux-x64/blender",
            "blender",
        ]
        
        blender_cmd = None
        for path in blender_paths:
            if os.path.exists(path):
                blender_cmd = path
                break
        
        if not blender_cmd:
            return {"error": "Blender not found. Please install Blender."}
        
        print(f"Using Blender at: {blender_cmd}")
        
        # Prepare blender command
        cmd = [
            blender_cmd, "-b", "-P", "/workspace/render_logo.py", "--",
            logo_path,
            output_dir,
            material,
            str(extrude_depth),
            str(bevel_depth)
        ]
        
        print(f"Starting render with command: {' '.join(cmd)}")
        
        # Run blender render with progress monitoring
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
        
        render_time = time.time() - start_time
        print(f"Render completed in {render_time:.2f} seconds")
        
        # Clean up temporary file
        os.unlink(logo_path)
        
        if result.returncode != 0:
            print(f"Blender render failed: {result.stderr}")
            return {"error": f"Render failed: {result.stderr}"}
        
        # Find output files
        output_files = []
        for file in os.listdir(output_dir):
            if file.startswith("frame_") and file.endswith(".png"):
                output_files.append(file)
        
        if not output_files:
            print(f"No output files found in {output_dir}")
            return {"error": "No output files generated"}
        
        # Sort files by frame number
        output_files.sort()
        print(f"Found {len(output_files)} output frames")
        
        # Create MP4 from frames using ffmpeg
        video_path = os.path.join(output_dir, "output.mp4")
        
        # Build ffmpeg command
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-framerate", "24",
            "-i", os.path.join(output_dir, "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "23",
            video_path
        ]
        
        print(f"Creating MP4 with command: {' '.join(ffmpeg_cmd)}")
        
        # Run ffmpeg
        ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
        
        if ffmpeg_result.returncode != 0:
            print(f"FFmpeg failed: {ffmpeg_result.stderr}")
            return {"error": f"Video creation failed: {ffmpeg_result.stderr}"}
        
        # Read the MP4 file and convert to base64
        with open(video_path, "rb") as video_file:
            video_data = video_file.read()
            video_base64 = base64.b64encode(video_data).decode('utf-8')
        
        print("Render completed successfully!")
        print(f"Video size: {len(video_data)} bytes")
        
        return {
            "status": "completed",
            "message": "Render completed successfully",
            "output_url": f"data:video/mp4;base64,{video_base64}",
            "video_size_bytes": len(video_data),
            "render_time_seconds": render_time,
            "frame_count": len(output_files)
        }
        
    except subprocess.TimeoutExpired:
        print(f"Render timed out after {timeout_seconds} seconds")
        return {"error": f"Render timed out after {timeout_seconds} seconds. Please try with simpler settings or contact support."}
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {"error": f"Internal server error: {str(e)}"}

# Start the Serverless function when the script is run
if __name__ == '__main__':
    runpod.serverless.start({"handler": handler})
