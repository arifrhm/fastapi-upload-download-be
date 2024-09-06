from fastapi import FastAPI, File, Request, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from concurrent.futures import ThreadPoolExecutor
import asyncio

app = FastAPI()

UPLOAD_FOLDER = "uploads"
CHUNK_SIZE = 1 * 1024 * 1024  # 1 MB per chunk
MAX_WORKERS = 5  # Maximum number of threads

# Create upload directory if it doesn't exist
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

# Thread pool executor for handling file operations
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up the template directory
templates = Jinja2Templates(directory="templates")


@app.middleware("http")
async def validate_content_length(request: Request, call_next):
    # Only check for POST requests that are multipart/form-data
    if request.method == "POST" and 'Content-Length' in request.headers:
        content_length = request.headers.get('Content-Length')
        if content_length:
            try:
                content_length = int(content_length)
                if content_length > CHUNK_SIZE:
                    return JSONResponse(
                        content={"detail": "Each part must not exceed 1 MB based on Content-Length."},
                        status_code=400
                    )
            except ValueError:
                return JSONResponse(
                    content={"detail": "Invalid Content-Length header."},
                    status_code=400
                )
    response = await call_next(request)
    return response


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def save_file_part(file_location, content):
    """Helper function to save a part of the file"""
    with open(file_location, "ab") as upload_file:
        upload_file.write(content)


@app.post("/upload_part/")
async def upload_part(
    file: UploadFile = File(...),
    part_number: int = Form(...),
    total_parts: int = Form(...),
):
    """
    Endpoint to upload a part of the file.
    Each request contains a chunk of the file and information
    about part_number and total_parts.
    """
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)

    # Run file writing in a separate thread using ThreadPoolExecutor
    loop = asyncio.get_event_loop()

    while True:
        content = await file.read(CHUNK_SIZE)
        if not content:
            break
        await loop.run_in_executor(
            executor,
            save_file_part,
            file_location,
            content
        )

    # Check if this is the last part
    if part_number == total_parts:
        return {"message": "Upload complete", "filename": file.filename}
    else:
        return {
            "message": f"Part {part_number}/{total_parts} uploaded",
            "filename": file.filename,
        }


def read_file_part(file_path, start, size):
    """Helper function to read part of the file"""
    with open(file_path, "rb") as file:
        file.seek(start)
        return file.read(size)


@app.get("/download/{file_name}")
async def download_file(file_name: str):
    file_path = os.path.join(UPLOAD_FOLDER, file_name)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(file_path)

    async def iter_file():
        loop = asyncio.get_event_loop()
        for start in range(0, file_size, CHUNK_SIZE):
            chunk = await loop.run_in_executor(
                executor, read_file_part, file_path, start, CHUNK_SIZE
            )
            yield chunk

    return StreamingResponse(
        iter_file(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_name}"},
    )


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
    files = os.listdir(UPLOAD_FOLDER)

    matching_files = [
        file for file in files
        if file_name.lower() in file.lower()
    ]

    if not matching_files:
        raise HTTPException(status_code=404, detail="No matching files found.")

    return {"matching_files": matching_files}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
