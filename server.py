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
            # Remove data URL prefix if present
            if logo.startswith('data:'):
                logo = logo.split(',')[1]
            
            image_data = base64.b64decode(logo)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
        
        # Create temporary file for the logo
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as temp_file:
            temp_file.write(image_data)
            logo_path = temp_file.name
        
        # Create output directory
        output_dir = "./output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Clear previous output files
        for file in os.listdir(output_dir):
            if file.startswith("frame_") and file.endswith(".png"):
                os.remove(os.path.join(output_dir, file))
        
        # Get Blender path - try different locations
        blender_paths = [
            "/Applications/Blender.app/Contents/MacOS/Blender",  # Mac
            "/opt/homebrew/bin/blender",  # Homebrew
            "blender",  # System PATH
        ]
        
        blender_cmd = None
        for path in blender_paths:
            if os.path.exists(path):
                blender_cmd = path
                break
        
        if not blender_cmd:
            raise HTTPException(status_code=500, detail="Blender not found. Please install Blender.")
        
        # Prepare blender command - this matches the render_logo.py script expectations
        cmd = [
            blender_cmd, "-b", "-P", "./render_logo.py", "--",
            logo_path,
            output_dir,
            material,
            str(extrude_depth),
            str(bevel_depth)
        ]
        
        # Run blender render
        print(f"Starting render with material: {material}, extrude_depth: {extrude_depth}, bevel_depth: {bevel_depth}")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)  # 20 minute timeout
        
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
        
        # Return success response with first frame
        first_frame = output_files[0]
        return RenderResponse(
            status="completed",
            message="Render completed successfully",
            output_url=f"/output/{first_frame}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/output/{filename}")
async def get_output_file(filename: str):
    """
    Serve rendered output files
    """
    output_dir = "./output"
    file_path = os.path.join(output_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Return the actual file
    return FileResponse(file_path, media_type="image/png")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
