# Blender Logo Render API

A FastAPI-based service that renders 3D logos using Blender. This service is designed to be deployed on RunPod for GPU-accelerated rendering.

## Features

- **3D Logo Rendering**: Convert 2D logos into stunning 3D animations
- **Material Presets**: Multiple material finishes (Gold, Chrome, Silver, Glass, Matte, etc.)
- **Customizable Parameters**: Adjust extrude depth (thickness) and bevel depth (edge smoothing)
- **FastAPI Integration**: RESTful API for easy integration with frontend applications
- **GPU Acceleration**: Optimized for CUDA-enabled GPUs on RunPod

## Supported Materials

- **Gold**: Luxurious metallic finish with rich golden tones
- **Chrome**: Polished metal shine with high reflectivity
- **Silver**: Elegant silver tone with metallic properties
- **Glass**: Transparent crystal effect with refraction
- **Matte**: Smooth matte texture with low reflectivity
- **Metallic**: Industrial metal look with medium reflectivity
- **Glossy**: High-gloss finish with smooth surface
- **Flat**: Minimal flat design with no 3D effects

## API Endpoints

### Health Check
```
GET /
GET /health
```

### Render Logo
```
POST /render
```

**Parameters:**
- `logo` (string): Base64 encoded image data
- `material` (string): Material type (default: "gold")
- `extrude_depth` (float): Thickness of the 3D extrusion (0.01-1.0, default: 0.1)
- `bevel_depth` (float): Edge smoothing amount (0.0-0.1, default: 0.02)

**Response:**
```json
{
  "status": "completed",
  "message": "Render completed successfully",
  "output_url": "/output/frame_0001.png"
}
```

## Deployment on RunPod

### Prerequisites

1. **RunPod Account**: Sign up at [runpod.io](https://runpod.io)
2. **API Key**: Get your API key from RunPod dashboard
3. **Docker**: Ensure Docker is installed locally for testing

### Step 1: Build and Push Docker Image

```bash
# Build the Docker image
docker build -t blender-logo-render .

# Tag for your registry (replace with your registry)
docker tag blender-logo-render your-registry/blender-logo-render:latest

# Push to registry
docker push your-registry/blender-logo-render:latest
```

### Step 2: Create RunPod Template

1. Go to RunPod dashboard
2. Navigate to "Community Cloud" → "Templates"
3. Create a new template with these settings:

**Basic Settings:**
- **Name**: Blender Logo Render API
- **Description**: 3D logo rendering service with Blender
- **Container Image**: `your-registry/blender-logo-render:latest`
- **Port**: `8000`

**Hardware Requirements:**
- **GPU**: RTX 4090 or similar (for optimal performance)
- **CPU**: 4+ cores
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 20GB minimum

**Environment Variables:**
```
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

### Step 3: Deploy on RunPod

1. **Create Pod**: Use the template to create a new pod
2. **Wait for Startup**: The service will be available at `http://your-pod-ip:8000`
3. **Test Health**: Visit `http://your-pod-ip:8000/health`

### Step 4: Configure Frontend Integration

Update your React frontend environment variables:

```env
RUNPOD_ENDPOINT_ID=your-endpoint-id
RUNPOD_API_KEY=your-api-key
```

## Local Development

### Prerequisites

- Python 3.8+
- Blender 3.6+
- CUDA-compatible GPU (optional, for faster rendering)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd blender-logo-render

# Install Python dependencies
pip install fastapi uvicorn python-multipart aiofiles

# Run the development server
python server.py
```

The API will be available at `http://localhost:8000`

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test render endpoint (example)
curl -X POST http://localhost:8000/render \
  -F "logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCI+PGNpcmNsZSBjeD0iNTAiIGN5PSI1MCIgcj0iNDAiIGZpbGw9ImdyZWVuIi8+PC9zdmc+" \
  -F "material=gold" \
  -F "extrude_depth=0.1" \
  -F "bevel_depth=0.02"
```

## File Structure

```
blender-logo-render/
├── Dockerfile          # Container configuration
├── server.py           # FastAPI server
├── render_logo.py      # Blender rendering script
├── logo.svg           # Example logo file
├── logo1.svg          # Example logo file
├── test.svg           # Test logo file
├── output/            # Rendered output directory
└── README.md          # This file
```

## Configuration

### Blender Settings

The rendering script (`render_logo.py`) includes several configurable parameters:

- **Resolution**: 1920x1080 (configurable in `configure_render()`)
- **Samples**: 4096 for high quality (adjustable)
- **Animation**: 240 frames with rotation
- **Output Format**: PNG sequence

### Performance Optimization

- **GPU Rendering**: Uses CUDA for faster rendering
- **Memory Management**: Automatic cleanup of temporary files
- **Timeout**: 5-minute timeout for render jobs
- **Error Handling**: Comprehensive error reporting

## Troubleshooting

### Common Issues

1. **CUDA Not Available**: Ensure GPU drivers are installed
2. **Memory Issues**: Increase pod RAM allocation
3. **Timeout Errors**: Reduce render quality or increase timeout
4. **File Format Issues**: Ensure SVG files are valid

### Logs

Check container logs for detailed error information:

```bash
# View logs
docker logs <container-id>

# Follow logs
docker logs -f <container-id>
```

## Integration with React Frontend

This service is designed to work with the React frontend. The frontend sends:

1. **Base64 encoded logo**
2. **Material selection**
3. **Extrude depth (thickness)**
4. **Bevel depth (edge smoothing)**

The service returns:
1. **Render status**
2. **Output file URL**
3. **Error messages (if any)**

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review RunPod documentation
3. Open an issue in the repository
