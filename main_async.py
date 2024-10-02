from fastapi import FastAPI, File, Request, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import aiofiles

app = FastAPI()

UPLOAD_FOLDER = "uploads"
CHUNK_SIZE = 1 * 1024 * 1024  # 1 MB per chunk

# Create upload directory if it doesn't exist
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up the template directory
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


async def save_file_part_async(file_location: str, content: bytes):
    """Helper function to asynchronously save a part of the file"""
    async with aiofiles.open(file_location, "ab") as upload_file:
        await upload_file.write(content)


@app.post("/upload_part/")
async def upload_part(
    file: UploadFile = File(...),
    part_number: int = Form(...),
    total_parts: int = Form(...),
):
    """
    Asynchronous endpoint to upload a part of the file.
    Each request contains a chunk of the file and information
    about part_number and total_parts.
    """
    if part_number <= 0 or total_parts <= 0:
        raise HTTPException(
            status_code=400, detail="Invalid part number or total parts"
        )

    file_location = os.path.join(UPLOAD_FOLDER, file.filename)

    async with aiofiles.open(file_location, "ab") as upload_file:
        while content := await file.read(CHUNK_SIZE):
            await upload_file.write(content)

    # Return a response indicating upload progress
    if part_number == total_parts:
        return {"message": "Upload complete", "filename": file.filename}
    else:
        return {
            "message": f"Part {part_number}/{total_parts} uploaded",
            "filename": file.filename,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
