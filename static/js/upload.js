document.addEventListener("DOMContentLoaded", () => {
    const uploadForm = document.getElementById("upload-form");
    const downloadForm = document.getElementById("download-form");
    const searchForm = document.getElementById("search-form");
    const filesList = document.getElementById("files");
    const searchResults = document.getElementById("results");
    
    // Handle file upload
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const fileInput = document.getElementById("file-input");
        const file = fileInput.files[0];
        const chunkSize = 1 * 1024 * 1024; // 1 MB

        const uploadUrl = "/upload/";

        for (let start = 0; start < file.size; start += chunkSize) {
            const end = Math.min(start + chunkSize, file.size);
            const chunk = file.slice(start, end);
            const formData = new FormData();
            formData.append("file", chunk);

            try {
                await fetch(uploadUrl, {
                    method: "POST",
                    body: formData
                });
                console.log(`Chunk from ${start} to ${end} uploaded.`);
            } catch (error) {
                console.error("Upload failed:", error);
            }
        }
    });

    // Handle file download
    downloadForm.addEventListener("submit", (e) => {
        e.preventDefault();

        const fileName = document.getElementById("download-file-name").value;
        const downloadUrl = `/download/${fileName}`;

        window.location.href = downloadUrl;
    });

    // Handle file search
    searchForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const fileName = document.getElementById("search-file-name").value;
        const searchUrl = `/search/?file_name=${fileName}`;

        try {
            const response = await fetch(searchUrl);
            const result = await response.json();
            searchResults.innerHTML = "";
            if (result.matching_files.length) {
                result.matching_files.forEach(file => {
                    const li = document.createElement("li");
                    li.textContent = file;
                    searchResults.appendChild(li);
                });
            } else {
                searchResults.innerHTML = "<li>No matching files found.</li>";
            }
        } catch (error) {
            console.error("Search failed:", error);
        }
    });

    // Fetch and display file list on page load
    async function fetchFileList() {
        try {
            const response = await fetch("/files/");
            const result = await response.json();
            filesList.innerHTML = "";
            if (result.files.length) {
                result.files.forEach(file => {
                    const li = document.createElement("li");
                    li.textContent = file;
                    filesList.appendChild(li);
                });
            } else {
                filesList.innerHTML = "<li>No files found.</li>";
            }
        } catch (error) {
            console.error("Failed to fetch files:", error);
        }
    }

    fetchFileList();
});
