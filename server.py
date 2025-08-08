import os
import base64
import tempfile
import subprocess
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Blender Logo Render API", version="1.0.0")

class RenderRequest(BaseModel):
    logo: str  # base64 encoded image
    material: str = "gold"
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
    material: str = Form("gold"),
    extrude_depth: float = Form(0.1),
    bevel_depth: float = Form(0.02)
):
    """
    Render a 3D logo with the specified parameters
    """
    try:
        # Validate material
        valid_materials = ["gold", "chrome", "silver", "glass", "matte", "glossy", "flat", "metallic", "golden"]
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
        output_dir = "/workspace/output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare blender command
        cmd = [
            "blender", "-b", "-P", "/workspace/render_logo.py", "--",
            logo_path,
            output_dir,
            material,
            str(extrude_depth),
            str(bevel_depth)
        ]
        
        # Run blender render
        print(f"Starting render with material: {material}, extrude_depth: {extrude_depth}, bevel_depth: {bevel_depth}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        # Clean up temporary file
        os.unlink(logo_path)
        
        if result.returncode != 0:
            print(f"Blender render failed: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Render failed: {result.stderr}")
        
        # Find output files
        output_files = []
        for file in os.listdir(output_dir):
            if file.startswith("frame_") and file.endswith(".png"):
                output_files.append(file)
        
        if not output_files:
            raise HTTPException(status_code=500, detail="No output files generated")
        
        # Sort files by frame number
        output_files.sort()
        
        # Return success response
        return RenderResponse(
            status="completed",
            message="Render completed successfully",
            output_url=f"/output/{output_files[0]}"  # Return first frame for now
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
    output_dir = "/workspace/output"
    file_path = os.path.join(output_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # For now, return file info. In production, you'd serve the actual file
    return {"filename": filename, "path": file_path, "exists": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
