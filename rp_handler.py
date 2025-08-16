import runpod
import os
import base64
import tempfile
import json
import subprocess
import time
from pathlib import Path
from s3_utils import create_s3_uploader


def handler(job):
    """
    RunPod handler for logo rendering with S3 upload
    """
    job_input = job["input"]

    print("=== Blender Logo Render Worker Started ===")

    # Extract parameters
    logo_data = job_input.get("logo")
    material = job_input.get("material", "golden")
    extrude_depth = job_input.get("extrude_depth", 0.1)
    bevel_depth = job_input.get("bevel_depth", 0.02)
    user_id = job_input.get("user_id")
    job_id = job_input.get("job_id")

    print(f"Processing render with material: {material}")
    print(f"Extrude depth: {extrude_depth}, Bevel depth: {bevel_depth}")
    print(f"User ID: {user_id}, Job ID: {job_id}")

    # Set timeout
    timeout = int(os.environ.get("BLENDER_TIMEOUT_SECONDS", 1200))
    print(f"Using timeout: {timeout} seconds")

    try:
        # Decode base64 logo
        if logo_data.startswith("data:image/svg+xml;base64,"):
            logo_data = logo_data.split(",")[1]

        logo_bytes = base64.b64decode(logo_data)
        print(f"Successfully decoded base64, image data length: {len(logo_bytes)}")

        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as temp_svg:
            temp_svg.write(logo_bytes)
            temp_svg_path = temp_svg.name

        output_dir = tempfile.mkdtemp()

        # Get Blender path
        blender_path = "/usr/local/bin/blender"
        print(f"Using Blender at: {blender_path}")

        # Build command
        cmd = [
            blender_path,
            "-b",
            "-P",
            "/workspace/render_logo.py",
            "--",
            temp_svg_path,
            output_dir,
            material,
            str(extrude_depth),
            str(bevel_depth),
        ]

        print(f"Starting render with command: {' '.join(cmd)}")

        # Run Blender with timeout
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        render_time = time.time() - start_time

        print(f"Render completed in {render_time:.2f} seconds")

        if result.returncode != 0:
            print(f"Blender render failed: {result.stderr}")
            return {"error": f"Render failed: {result.stderr}"}

        # Look for output files
        output_files = []
        video_path = None

        for file_path in Path(output_dir).glob("*.mp4"):
            video_path = str(file_path)
            output_files.append({"filename": file_path.name, "path": str(file_path)})

        if not output_files:
            print(f"No output files found in {output_dir}")
            print(f"Available files: {list(Path(output_dir).glob('*'))}")
            return {"error": "No output files generated"}

        print(f"Successfully generated {len(output_files)} output files")

        # Try to upload to S3 if configured
        s3_uploader = create_s3_uploader()
        if s3_uploader and video_path:
            print("Uploading video to S3...")
            upload_result = s3_uploader.upload_video_for_user(
                video_path, user_id, job_id
            )

            if upload_result["success"]:
                print(f"Video uploaded to S3: {upload_result['url']}")
                print(f"S3 Key: {upload_result['s3_key']}")

                # Cleanup temporary files
                os.unlink(temp_svg_path)
                for file_path in Path(output_dir).glob("*"):
                    os.unlink(file_path)
                os.rmdir(output_dir)

                return {
                    "output_url": upload_result["url"],
                    "s3_key": upload_result["s3_key"],
                    "presigned_url": upload_result.get("presigned_url"),
                    "message": "Render completed and uploaded to S3",
                }
            else:
                print(f"S3 upload failed: {upload_result['error']}")
                # Continue with base64 encoding as fallback

        # Fallback: encode files as base64
        encoded_files = []
        for file_info in output_files:
            with open(file_info["path"], "rb") as f:
                file_data = base64.b64encode(f.read()).decode("utf-8")
                encoded_files.append(
                    {"filename": file_info["filename"], "data": file_data}
                )

        # Cleanup
        os.unlink(temp_svg_path)
        for file_path in Path(output_dir).glob("*"):
            os.unlink(file_path)
        os.rmdir(output_dir)

        return {"output": encoded_files}

    except subprocess.TimeoutExpired:
        print(f"Render timed out after {timeout} seconds")
        return {"error": f"Render timed out after {timeout} seconds"}
    except Exception as e:
        print(f"Error during render: {str(e)}")
        return {"error": f"Render error: {str(e)}"}


runpod.serverless.start({"handler": handler})
