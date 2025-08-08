import os
import base64
import tempfile
import subprocess
import json
import shutil
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn
from s3_utils import create_s3_uploader
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    s3_key: Optional[str] = None
    presigned_url: Optional[str] = None
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
    bevel_depth: float = Form(0.02),
    user_id: Optional[str] = Form(None),
    job_id: Optional[str] = Form(None)
):
    """
    Render a 3D logo with the specified parameters and upload to S3
    """
    # Create temporary directory for rendering
    temp_dir = tempfile.mkdtemp()
    
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
        
        # Clear any previous output files in temp directory
        for file in os.listdir(temp_dir):
            if file.startswith("frame_") and file.endswith(".png"):
                os.remove(os.path.join(temp_dir, file))
        
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
        render_script_path = os.path.join(os.getcwd(), "render_logo.py")
        cmd = [
            blender_cmd, "-b", "-P", render_script_path, "--",
            logo_path,
            temp_dir,
            material,
            str(extrude_depth),
            str(bevel_depth)
        ]
        
        # Run blender render
        print(f"Starting render with material: {material}, extrude_depth: {extrude_depth}, bevel_depth: {bevel_depth}")
        print(f"User ID: {user_id}, Job ID: {job_id}")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        # Clean up temporary logo file
        os.unlink(logo_path)
        
        if result.returncode != 0:
            print(f"Blender render failed: {result.stderr}")
            print(f"Blender stdout: {result.stdout}")
            raise HTTPException(status_code=500, detail=f"Render failed: {result.stderr}")
        
        # Check for the rendered MP4 file
        video_path = os.path.join(temp_dir, "rendered_animation.mp4")
        
        if not os.path.exists(video_path):
            print(f"Video file not found at {video_path}")
            print(f"Directory contents: {os.listdir(temp_dir)}")
            raise HTTPException(status_code=500, detail="Video file not generated")
        
        print(f"Video file found: {video_path}")
        
        # Upload to S3
        s3_uploader = create_s3_uploader()
        if s3_uploader:
            print("Uploading video to S3...")
            upload_result = s3_uploader.upload_video_for_user(video_path, user_id, job_id)
            
            if upload_result['success']:
                print(f"Video uploaded to S3: {upload_result['url']}")
                print(f"S3 Key: {upload_result['s3_key']}")
                return RenderResponse(
                    status="completed",
                    message="Render completed successfully and uploaded to S3",
                    output_url=upload_result['url'],
                    s3_key=upload_result['s3_key'],
                    presigned_url=upload_result.get('presigned_url')
                )
            else:
                print(f"S3 upload failed: {upload_result['error']}")
                raise HTTPException(status_code=500, detail=f"S3 upload failed: {upload_result['error']}")
        else:
            raise HTTPException(status_code=500, detail="S3 uploader not configured")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Warning: Failed to clean up temporary directory {temp_dir}: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
