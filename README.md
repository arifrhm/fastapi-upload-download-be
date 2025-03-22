# Chunk Upload with Resume

A FastAPI application that handles large file uploads with chunk splitting and resume capability.

## Features

- 📁 Chunk-based file upload
- ⏸️ Resume interrupted uploads
- 🎯 Progress tracking
- 🖼️ Drag and drop interface
- 🛡️ File type restrictions
- 📊 File size limitations
- 🔄 Async file handling

## Features in Detail

### Chunk Upload
- Files are split into 1MB chunks by default
- Each chunk is uploaded separately
- Progress is tracked in real-time

### Resume Capability
- Uploads can be resumed after interruption
- Server keeps track of uploaded chunks
- Client can request resume information

### File Validation
- File type restrictions
- Maximum file size limit
- Chunk integrity checking

## Security

- File type validation
- File size limitations
- Configurable restrictions
- Secure file handling

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the amazing framework
- Tailwind CSS for the styling
- All contributors who participate in this project

## Support

For support, please open an issue in the repository.

## Tech Stack

- FastAPI
- Python 3.8+
- Tailwind CSS
- JavaScript (ES6+)

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. Clone the repository
```bash
git clone https://github.com/arifrhm/fastapi-upload-download-be.git
cd fastapi-upload-download-be
```

2. Create and activate virtual environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings
nano .env
```

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000

# Upload Configuration
UPLOAD_FOLDER=uploads
CHUNK_SIZE=1048576  # 1MB in bytes

# File Configuration
MAX_FILE_SIZE=104857600  # 100MB in bytes
ALLOWED_EXTENSIONS=.pdf,.doc,.docx,.txt,.zip,.rar,.jpg,.jpeg,.png
```

## Running the Application

### Development Mode
1. Start the FastAPI server with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

3. For API documentation, visit:
```
http://localhost:8000/docs    # Swagger UI
http://localhost:8000/redoc   # ReDoc UI
```

### Production Mode
1. Install production server:
```bash
pip install gunicorn
```

2. Start the server:
```bash
# For Linux/Mac
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# For Windows (use uvicorn directly)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment
1. Build the Docker image:
```bash
docker build -t chunk-upload-app .
```

2. Run the container:
```bash
docker run -d -p 8000:8000 \
  --name chunk-upload \
  -v $(pwd)/uploads:/app/uploads \
  chunk-upload-app
```

### Environment Specific Configuration
- Development:
```bash
export ENVIRONMENT=development
# or set ENVIRONMENT=development (Windows)
```

- Production:
```bash
export ENVIRONMENT=production
# or set ENVIRONMENT=production (Windows)
```

### Health Check
Monitor the application status:
```
http://localhost:8000/health
```

### Common Issues and Solutions

1. Port already in use:
```bash
# Find process using port 8000
lsof -i :8000    # Linux/Mac
netstat -ano | findstr :8000    # Windows

# Kill the process
kill -9 <PID>    # Linux/Mac
taskkill /PID <PID> /F    # Windows
```

2. Permission issues with upload directory:
```bash
# Linux/Mac
chmod 755 uploads
chown -R <user>:<group> uploads

# Windows (Run as Administrator)
icacls uploads /grant Users:(OI)(CI)F
```

3. Memory issues with large files:
```bash
# Increase Python memory limit (Linux/Mac)
export PYTHONMEM=4096

# Windows
set PYTHONMEM=4096
```

### Monitoring
1. Basic process monitoring:
```bash
# Install monitoring tool
pip install prometheus_client

# Access metrics
http://localhost:8000/metrics
```

2. Log monitoring:
```bash
# View logs in real-time
tail -f app.log    # Linux/Mac
Get-Content app.log -Wait    # Windows PowerShell
```

### Backup Configuration
1. Automatic backup of uploaded files:
```bash
# Linux/Mac (add to crontab)
0 0 * * * tar -czf /backup/uploads-$(date +%Y%m%d).