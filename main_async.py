from fastapi import FastAPI, Request, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import aiofiles

app = FastAPI()

UPLOAD_FOLDER = "uploads"
CHUNK_SIZE = 1 * 1024 * 1024  # 1 MB per chunk
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB in bytes
MAX_PARTS = 100  # Maximum number of parts

# Create upload directory if it doesn't exist
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up the template directory
templates = Jinja2Templates(directory="templates")


# Middleware to validate Content-Length
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

    # Proceed with the request if no validation errors
    response = await call_next(request)
    return response

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

    # Validasi jumlah part maksimal
    if total_parts > MAX_PARTS:
        raise HTTPException(
            status_code=400, detail=f"Total parts cannot exceed {MAX_PARTS}."
        )

    # Baca data file chunk demi chunk
    content = await file.read(CHUNK_SIZE + 1)  # Lebihkan 1 byte untuk validasi cepat

    # Jika part lebih dari 1 MB, tolak permintaan
    if len(content) > CHUNK_SIZE:
        raise HTTPException(status_code=400, detail="Each part must not exceed 1 MB.")

    # Jika content kurang dari 1 MB (kecuali part terakhir), tolak permintaan
    if len(content) < CHUNK_SIZE and part_number < total_parts:
        raise HTTPException(
            status_code=400, detail="Each part except the last must be exactly 1 MB."
        )

    # Simpan bagian file yang valid
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)

    # Validasi ukuran file saat ini
    current_file_size = (
        os.path.getsize(file_location) if os.path.exists(file_location) else 0
    )

    # Pastikan ukuran file saat ini tidak melebihi 100 MB
    if current_file_size + len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Total file size exceeds the allowed limit of 100 MB.",
        )

    # Simpan bagian file secara asynchronous
    async with aiofiles.open(file_location, "ab") as upload_file:
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
        raise HTTPException(status_code=400, detail="File name parameter is required")

    files = os.listdir(UPLOAD_FOLDER)
    matching_files = [file for file in files if file_name.lower() in file.lower()]

    if not matching_files:
        raise HTTPException(status_code=404, detail="No matching files found.")

    return {"matching_files": matching_files}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
