document.addEventListener('DOMContentLoaded', function() {
    // Global variables
    let uploadQueue = {};
    let currentChunkIndex = 0;
    let totalChunks = 0;
    let fileName = '';
    let fileSize = 0;

    // Get DOM elements
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const fileInfo = document.getElementById('fileInfo');
    const fileNameElement = document.getElementById('fileName');
    const fileSizeElement = document.getElementById('fileSize');
    const uploadBtn = document.getElementById('uploadBtn');
    const resumeBtn = document.getElementById('resumeBtn');
    const progressContainer = document.getElementById('progressContainer');
    const statusMessage = document.getElementById('statusMessage');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');

    // Verify all elements exist
    if (!fileInput || !dropZone || !fileInfo || !fileNameElement || 
        !fileSizeElement || !uploadBtn || !resumeBtn || !progressContainer || 
        !statusMessage || !progressBar || !progressText) {
        console.error('Some DOM elements are missing');
        return;
    }

    // Format file size function
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Show status message
    function showStatus(message, type = 'info') {
        statusMessage.className = 'text-sm rounded-lg p-3 ' + 
            (type === 'error' ? 'bg-red-100 text-red-700' : 
             type === 'success' ? 'bg-green-100 text-green-700' : 
             'bg-blue-100 text-blue-700');
        statusMessage.textContent = message;
        statusMessage.classList.remove('hidden');
    }

    // File input change handler
    fileInput.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (file) {
            fileName = file.name;
            fileSize = file.size;
            
            fileNameElement.textContent = fileName;
            fileSizeElement.textContent = formatFileSize(fileSize);
            fileInfo.classList.remove('hidden');
            
            try {
                const response = await fetch(`/search?file_name=${encodeURIComponent(fileName)}`);
                const data = await response.json();
                
                if (data.matching_files && data.matching_files.includes(fileName)) {
                    showStatus('File already exists. You can resume the upload.', 'info');
                    resumeBtn.disabled = false;
                } else {
                    uploadBtn.disabled = false;
                    resumeBtn.disabled = true;
                }
            } catch (error) {
                console.error('Error checking file:', error);
                uploadBtn.disabled = false;
            }
        }
    });

    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('border-blue-500');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('border-blue-500');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-blue-500');
        fileInput.files = e.dataTransfer.files;
        fileInput.dispatchEvent(new Event('change'));
    });

    // Make functions globally available
    window.startUpload = function() {
        const file = fileInput.files[0];
        if (!file) {
            showStatus('Please select a file first.', 'error');
            return;
        }

        fileSize = file.size;
        const chunkSize = 1024 * 1024; // 1MB
        totalChunks = Math.ceil(fileSize / chunkSize);
        fileName = file.name;
        uploadQueue = {};

        for (let i = 0; i < totalChunks; i++) {
            const start = i * chunkSize;
            const end = Math.min(start + chunkSize, fileSize);
            const chunk = file.slice(start, end);
            uploadQueue[i] = { chunk, index: i };
        }

        currentChunkIndex = 0;
        progressContainer.classList.remove('hidden');
        uploadBtn.disabled = true;
        resumeBtn.disabled = true;
        uploadNextChunk();
    };

    // Add this function to update progress bar
    function updateProgressBar() {
        if (totalChunks === 0) return;
        const percent = Math.min((currentChunkIndex / totalChunks) * 100, 100);
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `${Math.round(percent)}%`;
    }

    function completeProgress() {
        progressBar.style.width = '100%';
        progressText.textContent = '100%';
        showStatus('Upload completed successfully!', 'success');
    }

    window.uploadNextChunk = function() {
        if (currentChunkIndex >= totalChunks) {
            completeProgress();
            return;
        }

        if (!uploadQueue[currentChunkIndex]) {
            currentChunkIndex++;
            uploadNextChunk();
            return;
        }

        const { chunk, index } = uploadQueue[currentChunkIndex];
        const formData = new FormData();
        formData.append('part_number', index + 1);
        formData.append('total_parts', totalChunks);
        formData.append('file', chunk);
        formData.append('file_name', fileName);

        fetch('/upload_part/', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.message.includes('uploaded') || data.message.includes('complete')) {
                delete uploadQueue[currentChunkIndex];
                currentChunkIndex++;
                
                if (currentChunkIndex >= totalChunks) {
                    completeProgress();
                } else {
                    updateProgressBar();
                    uploadNextChunk();
                }
            } else {
                showStatus('Error uploading chunk: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showStatus('Error uploading chunk. Please try resuming.', 'error');
            resumeBtn.disabled = false;
        });
    };

    window.resumeUpload = function() {
        if (!fileName || !fileInput.files[0]) {
            showStatus('No file selected for resume.', 'error');
            return;
        }

        const file = fileInput.files[0];
        fileSize = file.size;
        const chunkSize = 1024 * 1024; // 1MB
        totalChunks = Math.ceil(fileSize / chunkSize);

        fetch(`/resume-upload?file_name=${encodeURIComponent(fileName)}`)
            .then(response => response.json())
            .then(data => {
                currentChunkIndex = data.chunk_index;
                console.log(`Resuming from chunk ${currentChunkIndex}`);

                // If resuming from last chunk, complete the progress
                if (currentChunkIndex >= totalChunks) {
                    completeProgress();
                    return;
                }

                // Recreate upload queue for remaining chunks
                uploadQueue = {};
                for (let i = currentChunkIndex; i < totalChunks; i++) {
                    const start = i * chunkSize;
                    const end = Math.min(start + chunkSize, fileSize);
                    const chunk = file.slice(start, end);
                    uploadQueue[i] = { chunk, index: i };
                }

                progressContainer.classList.remove('hidden');
                resumeBtn.disabled = true;
                updateProgressBar();
                uploadNextChunk();
            })
            .catch(error => {
                console.error('Error resuming upload:', error);
                showStatus('Error resuming upload.', 'error');
            });
    };
});
