import os
import base64
import tempfile
import subprocess
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Blender Logo Render API", version="1.0.0")

class RenderRequest(BaseModel):
    logo: str  # base64 encoded image
    material: str = "golden"
    extrude_depth: float = 0.1
    bevel_depth: float = 0.02

class RenderResponse(BaseModel):
    status: str
    message: str
    output_url: Optional[str] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Blender Logo Render API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "blender-logo-render"}

@app.post("/render", response_model=RenderResponse)
async def render_logo(
    logo: str = Form(...),
    material: str = Form("golden"),
    extrude_depth: float = Form(0.1),
    bevel_depth: float = Form(0.02)
):
    """
    Render a 3D logo with the specified parameters
    """
    try:
        # Validate material - these are the materials supported by render_logo.py
        valid_materials = ["flat", "glossy", "matte", "metallic", "chrome", "golden"]
        if material not in valid_materials:
            raise HTTPException(status_code=400, detail=f"Invalid material. Choose from: {valid_materials}")
        
        # Validate extrude_depth
        if extrude_depth < 0.01 or extrude_depth > 1.0:
            raise HTTPException(status_code=400, detail="Extrude depth must be between 0.01 and 1.0")
        
        # Validate bevel_depth
        if bevel_depth < 0.0 or bevel_depth > 0.1:
            raise HTTPException(status_code=400, detail="Bevel depth must be between 0.0 and 0.1")
        
        # Decode base64 image
        try:
            print(f"Original logo data length: {len(logo)}")
            print(f"Logo starts with 'data:': {logo.startswith('data:')}")
            
            # Remove data URL prefix if present
            if logo.startswith('data:'):
                logo = logo.split(',')[1]
                print(f"After removing data URL prefix, length: {len(logo)}")
            
            image_data = base64.b64decode(logo)
            print(f"Successfully decoded base64, image data length: {len(image_data)}")
        except Exception as e:
            print(f"Base64 decode error: {str(e)}")
            print(f"Logo data (first 100 chars): {logo[:100]}")
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")
        
        # Create temporary file for the logo
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as temp_file:
            temp_file.write(image_data)
            logo_path = temp_file.name
        
        # Create output directory
        output_dir = "/blender-logo-render/output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Clear previous output files
        for file in os.listdir(output_dir):
            if file.startswith("frame_") and file.endswith(".png"):
                os.remove(os.path.join(output_dir, file))
        
        # Get Blender path - try different locations
        blender_paths = [
            "/blender-logo-render/blender-4.5.1-linux-x64/blender",  # Current RunPod path
            "/usr/local/bin/blender",  # Docker container path
            "/opt/blender-3.6.0-linux-x64/blender",  # Docker container path
            "/Applications/Blender.app/Contents/MacOS/Blender",  # Mac
            "/opt/homebrew/bin/blender",  # Homebrew
            "blender",  # System PATH
        ]
        
        print("Checking Blender paths:")
        blender_cmd = None
        for path in blender_paths:
            exists = os.path.exists(path)
            print(f"  {path}: {'EXISTS' if exists else 'NOT FOUND'}")
            if exists:
                blender_cmd = path
                print(f"Using Blender at: {blender_cmd}")
                break
        
        if not blender_cmd:
            print("ERROR: No Blender installation found in any of the expected paths")
            raise HTTPException(status_code=500, detail="Blender not found. Please install Blender.")
        
        # Prepare blender command - this matches the render_logo.py script expectations
        cmd = [
            blender_cmd, "-b", "-P", "/blender-logo-render/render_logo.py", "--",
            logo_path,
            output_dir,
            material,
            str(extrude_depth),
            str(bevel_depth)
        ]
        
        # Run blender render
        print(f"Starting render with material: {material}, extrude_depth: {extrude_depth}, bevel_depth: {bevel_depth}")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        # Clean up temporary file
        os.unlink(logo_path)
        
        if result.returncode != 0:
            print(f"Blender render failed: {result.stderr}")
            print(f"Blender stdout: {result.stdout}")
            raise HTTPException(status_code=500, detail=f"Render failed: {result.stderr}")
        
        # Find output files
        output_files = []
        for file in os.listdir(output_dir):
            if file.startswith("frame_") and file.endswith(".png"):
                output_files.append(file)
        
        if not output_files:
            print(f"No output files found in {output_dir}")
            print(f"Directory contents: {os.listdir(output_dir)}")
            raise HTTPException(status_code=500, detail="No output files generated")
        
        # Sort files by frame number
        output_files.sort()
        
        # Create MP4 from frames using ffmpeg
        video_path = os.path.join(output_dir, "output.mp4")
        
        # Build ffmpeg command to create MP4 from PNG frames
        ffmpeg_cmd = [
            "ffmpeg", "-y",  # Overwrite output file
            "-framerate", "24",  # 24 fps
            "-i", os.path.join(output_dir, "frame_%04d.png"),  # Input pattern
            "-c:v", "libx264",  # H.264 codec
            "-pix_fmt", "yuv420p",  # Pixel format for compatibility
            "-crf", "23",  # Quality setting
            video_path
        ]
        
        print(f"Creating MP4 with command: {' '.join(ffmpeg_cmd)}")
        
        # Run ffmpeg
        ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
        
        if ffmpeg_result.returncode != 0:
            print(f"FFmpeg failed: {ffmpeg_result.stderr}")
            raise HTTPException(status_code=500, detail=f"Video creation failed: {ffmpeg_result.stderr}")
        
        # Read the MP4 file and convert to base64
        with open(video_path, "rb") as video_file:
            video_data = video_file.read()
            video_base64 = base64.b64encode(video_data).decode('utf-8')
        
        return RenderResponse(
            status="completed",
            message="Render completed successfully",
            output_url=f"data:video/mp4;base64,{video_base64}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
