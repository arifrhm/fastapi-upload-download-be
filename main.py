from fastapi import FastAPI, File, Request, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import aiofiles
from dotenv import load_dotenv
import psutil
import time

# Load environment variables
load_dotenv()

app = FastAPI()

# Environment variables with defaults
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 1 * 1024 * 1024))  # Default 1MB
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 100 * 1024 * 1024))  # Default 100MB
ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', '.pdf,.doc,.docx,.txt,.zip,.rar,.jpg,.jpeg,.png').split(',')

# Create upload directory if it doesn't exist
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up the template directory
templates = Jinja2Templates(directory="templates")

def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "max_file_size": MAX_FILE_SIZE,
        "allowed_extensions": ALLOWED_EXTENSIONS
    })

async def save_file_part_async(file_location: str, content: bytes):
    """Helper function to asynchronously save a part of the file"""
    async with aiofiles.open(file_location, "ab") as upload_file:
        await upload_file.write(content)

@app.post("/upload_part/")
async def upload_part(
    file: UploadFile = File(...),
    part_number: int = Form(...),
    total_parts: int = Form(...),
    file_name: str = Form(...),
):
    """
    Asynchronous endpoint to upload a part of the file.
    """
    # Validate file extension
    if not is_allowed_file(file_name):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    if part_number <= 0 or total_parts <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid part number or total parts"
        )

    file_location = os.path.join(UPLOAD_FOLDER, file_name)

    # Check total file size
    if os.path.exists(file_location):
        current_size = os.path.getsize(file_location)
        if current_size >= MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE/1024/1024}MB"
            )

    # Ensure the file exists before writing the chunks
    if part_number == 1 and not os.path.exists(file_location):
        Path(file_location).touch()

    # Save the file chunk
    async with aiofiles.open(file_location, "ab") as upload_file:
        while content := await file.read(CHUNK_SIZE):
            await upload_file.write(content)

    # Check final file size
    if os.path.getsize(file_location) > MAX_FILE_SIZE:
        os.remove(file_location)  # Delete the file if it exceeds size limit
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE/1024/1024}MB"
        )

    if part_number == total_parts:
        return {"message": "Upload complete", "filename": file_name}
    else:
        return {
            "message": f"Part {part_number}/{total_parts} uploaded",
            "filename": file_name,
        }

async def read_file_part_async(file_path: str, start: int, size: int) -> bytes:
    """Helper function to asynchronously read part of the file"""
    async with aiofiles.open(file_path, "rb") as file:
        await file.seek(start)
        return await file.read(size)

@app.get("/download/{file_name}")
async def download_file(file_name: str):
    file_path = os.path.join(UPLOAD_FOLDER, file_name)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(file_path)

    async def iter_file():
        for start in range(0, file_size, CHUNK_SIZE):
            chunk = await read_file_part_async(file_path, start, CHUNK_SIZE)
            yield chunk

    return StreamingResponse(
        iter_file(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_name}"},
    )

@app.get("/resume-upload")
async def resume_upload(file_name: str):
    """
    Endpoint to check the last uploaded chunk for a file and resume upload.
    """
    file_path = os.path.join(UPLOAD_FOLDER, file_name)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(file_path)
    chunk_index = file_size // CHUNK_SIZE

    return {"chunk_index": chunk_index, "message": f"Resume from chunk {chunk_index}"}

@app.get("/files/")
async def list_files():
    """
    Endpoint to list all files in the upload directory
    """
    files = os.listdir(UPLOAD_FOLDER)
    if not files:
        return {"message": "No files found."}
    return {"files": files}

@app.get("/search/")
async def search_file(file_name: str):
    """
    Endpoint to search for a file by name
    """
    if not file_name:
        raise HTTPException(
            status_code=400, detail="File name parameter is required"
            )

    files = os.listdir(UPLOAD_FOLDER)
    matching_files = [
        file for file in files if file_name.lower() in file.lower()
        ]

    if not matching_files:
        raise HTTPException(status_code=404, detail="No matching files found.")

    return {"matching_files": matching_files}

@app.get("/health")
async def health_check():
    """
    Health check endpoint that returns system metrics and application status
    """
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check upload directory
        upload_dir_exists = os.path.exists(UPLOAD_FOLDER)
        upload_dir_writable = os.access(UPLOAD_FOLDER, os.W_OK) if upload_dir_exists else False
        
        # Application status
        status = {
            "status": "healthy",
            "timestamp": time.time(),
            "system": {
                "cpu_usage": f"{cpu_percent}%",
                "memory_used": f"{memory.percent}%",
                "disk_used": f"{disk.percent}%"
            },
            "upload_directory": {
                "exists": upload_dir_exists,
                "writable": upload_dir_writable,
                "path": os.path.abspath(UPLOAD_FOLDER)
            },
            "configuration": {
                "max_file_size": f"{MAX_FILE_SIZE/1024/1024}MB",
                "chunk_size": f"{CHUNK_SIZE/1024}KB",
                "allowed_extensions": ALLOWED_EXTENSIONS
            }
        }
        
        return JSONResponse(
            content=status,
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            },
            status_code=503
        )

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    
    uvicorn.run(app, host=host, port=port)
