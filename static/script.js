document.addEventListener("DOMContentLoaded", function() {
    const form = document.querySelector("form"),
    fileInput = document.getElementById("file-input"),
    progressArea = document.querySelector(".progress-area"),
    uploadedArea = document.querySelector(".uploaded-area"),
    submitButton = document.querySelector(".submit-file"),
    fileNameDisplay = document.getElementById('fileName'),
    searchInput = document.getElementById('search-input'),
    deleteFolderButtons = document.querySelectorAll('.delete-folder'),
    deleteFileButtons = document.querySelectorAll('.delete-file'),
    submitFolderButton = document.querySelector(".submit-folder"),
    btnReply = document.querySelector('.btn-reply'),
    btnLogout = document.querySelector('.btn-logout'),
    folderForm = document.getElementById("createFolderForm"),
    shareFileButtons = document.querySelectorAll('.share-file'),
    shareForms = document.querySelectorAll('.share-file-form'),
    currentPath = window.location.pathname;

    let selectedFile;

    shareFileButtons.forEach(button => {
        button.addEventListener('click', () => {
            const file = button.getAttribute('data-file');
            const form = Array.from(shareForms).find(f => f.querySelector('.submit-share').getAttribute('data-file') === file);
    
            // Kiểm tra trạng thái hiện tại của form
            if (form) {
                if (form.style.display === 'flex') {
                    // Nếu form đang hiển thị thì ẩn đi
                    form.style.display = 'none';
                } else {
                    // Ẩn tất cả các form chia sẻ khác
                    shareForms.forEach(f => f.style.display = 'none');
                    
                    // Hiển thị form chia sẻ tương ứng với file được chọn
                    form.style.display = 'flex';
                }
            }
        });
    });
    

    document.querySelectorAll('.submit-share').forEach(button => {
        button.addEventListener('click', () => {
            const form = button.closest('.share-file-form');
            const username = form.querySelector('.share-username').value;
            const file = button.getAttribute('data-file');

            if (username && file) {
                fetch('/share_file', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: username,
                        file: file
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('File đã được chia sẻ thành công!');
                        location.reload(); // Tải lại trang để cập nhật
                    } else {
                        alert('Lỗi: ' + data.message);
                    }
                });
            } else {
                alert('Vui lòng nhập tên người nhận và chọn file!');
            }
        });
    });


    if (currentPath === "/home") {
        btnReply.disabled = true;  
    }

    btnReply.addEventListener('click', function () {
        const pathSegments = currentPath.split('/').filter(segment => segment !== ""); 
        if (pathSegments.length > 0) {  
            pathSegments.pop();  
            const newPath = "/" + pathSegments.join('/') ;  

            window.location.href = newPath;
        } else {
            btnReply.disabled = true;
        }
    });

    btnLogout.addEventListener('click', function () {
        const confirmLogout = confirm("Are you sure you want to exit?");
        
        if (confirmLogout) {
            window.location.href = '/logout';
        }
    });

    fileInput.addEventListener('change', function() {
        selectedFile = this.files[0];
        fileNameDisplay.textContent = selectedFile ? selectedFile.name : "No file chosen";
        console.log("File selected:", selectedFile.name);
    });

    submitButton.addEventListener("click", (e) => {
        e.preventDefault(); 
    
        if (selectedFile) {
            let fileName = selectedFile.name;
            
            simulateUpload(fileName);
    
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('current_folder', document.querySelector('input[name="current_folder"]').value); // Thêm folder hiện tại nếu cần
    
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    flashMessage('success', data.message);  
                } else {
                    flashMessage('error', data.message);  
                }
            })
            .catch(error => {
                flashMessage('error', 'An error occurred during file upload');
                console.error('Error:', error);
            });
        }
    });
    
    submitFolderButton.addEventListener("click", (e) => {
        e.preventDefault(); 
    
        let folderForm = document.getElementById('createFolderForm');
        let formData = new FormData(folderForm);
    
        fetch('/create_folder', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.reload();
            } else {
                console.error('Error:', data.message); 
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
        });  
    });
    

    function simulateUpload(name) {
        let fileLoaded = 0;
        
        let progressHTML = `<li class="row">
                                <i class="fas fa-file-alt"></i>
                                <div class="content">
                                    <div class="details">
                                        <span class="name">${name} • Uploading</span>
                                        <span class="percent">${fileLoaded}%</span>
                                    </div>
                                    <div class="progress-bar">
                                        <div class="progress" style="width: ${fileLoaded}%"></div>
                                    </div>
                                </div>
                            </li>`;
        progressArea.innerHTML = progressHTML;
    
        let uploadInterval = setInterval(() => {
            if (fileLoaded < 100) {
                fileLoaded++;
                let progressBar = progressArea.querySelector(".progress");
                let percentText = progressArea.querySelector(".percent");
    
                progressBar.style.width = fileLoaded + "%";
                percentText.textContent = fileLoaded + "%";
            } else {
                clearInterval(uploadInterval);
    
                // Upload file thực tế lên server
                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('current_folder', currentPath);  
        
                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        let lastModified = data.last_modified;
                        let fileSize = data.file_size;
    
                        let uploadedHTML = `
                        <li class="row file" data-name="${name.toLowerCase()}">
                            <div class="content">
                                <i class="fas fa-file-alt"></i>
                                <div class="details">
                                    <a href="/download/${name}" class="name">${name}</a>
                                    <span class="size">${fileSize}</span>
                                </div>
                            </div>
                            <div class="right-lm">
                                <span class="last-modified">Last modified: ${lastModified}</span>
                                <i class="fas fa-check" style="margin-left: 10px;"></i>
                                <button class="delete-file" data-file="${name}">
                                    <i class="fas fa-trash-alt" ></i>
                                </button>
                            </div>
                        </li>`;
                        
                        uploadedArea.insertAdjacentHTML("afterbegin", uploadedHTML);
                        window.location.reload();
                        progressArea.innerHTML = ""; // Xóa thông tin trạng thái tải lên sau khi hoàn tất
                    } else {
                        console.error('Upload failed:', data.message);
                        // Cập nhật thông báo lỗi nếu cần
                        progressArea.innerHTML = `<p class="error">Upload failed: ${data.message}</p>`;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    // Cập nhật thông báo lỗi nếu có lỗi xảy ra
                    progressArea.innerHTML = `<p class="error">Upload error: ${error.message}</p>`;
                });
            }
        }, 20);
    }

    searchInput.addEventListener("input", () => {
        const searchValue = searchInput.value.toLowerCase();
        const rows = uploadedArea.querySelectorAll(".row");

        rows.forEach(row => {
            const fileName = row.getAttribute("data-name");
            if (fileName.includes(searchValue)) {
                row.style.display = "flex";
            } else {
                row.style.display = "none";
            }
        });
    });

    deleteFolderButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();

            const folderName = button.getAttribute('data-folder');
            if (folderName) {
                if (confirm(`Bạn có chắc muốn xóa thư mục "${folderName}"?`)) {
                    const form = button.previousElementSibling; // Form ẩn để xóa thư mục
                    if (form && form.tagName === 'FORM') {
                        const inputFolder = form.querySelector('input[name="folder"]');
                        const inputCurrentFolder = form.querySelector('input[name="current_folder"]');

                        if (inputFolder && inputCurrentFolder) {
                            const folder = inputFolder.value;
                            const currentFolder = inputCurrentFolder.value;

                            // Gửi yêu cầu xóa thư mục qua AJAX
                            const xhr = new XMLHttpRequest();
                            xhr.open('POST', form.action, true);
                            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                            
                            xhr.onload = function() {
                                if (xhr.status >= 200 && xhr.status < 300) {
                                    const response = JSON.parse(xhr.responseText);
                                    if (response.status === 'success') {
                                        alert('Thư mục đã được xóa thành công!');
                                        window.location.reload(); // Tải lại trang sau khi xóa thành công
                                    } else {
                                        alert('Lỗi: ' + response.message);
                                    }
                                } else {
                                    alert('Lỗi xảy ra: ' + xhr.statusText);
                                }
                            };

                            xhr.send(new URLSearchParams({
                                'folder': folder,
                                'current_folder': currentFolder
                            }).toString());
                        } else {
                            alert('Không tìm thấy thông tin thư mục hoặc thư mục hiện tại.');
                        }
                    } else {
                        alert('Không tìm thấy form để xóa thư mục.');
                    }
                }
            } else {
                alert('Tên thư mục không hợp lệ!');
            }
        });
    });
    
    
    deleteFileButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();

            const fileName = button.getAttribute('data-file');
            if (fileName) {
                if (confirm(`Bạn có chắc muốn xóa file "${fileName}"?`)) {
                    const form = button.previousElementSibling; // Form ẩn để xóa file
                    if (form && form.tagName === 'FORM') {
                        const inputFile = form.querySelector('input[name="file"]');
                        const inputFolder = form.querySelector('input[name="current_folder"]');

                        if (inputFile && inputFolder) {
                            const file = inputFile.value;
                            const currentFolder = inputFolder.value;

                            // Gửi yêu cầu xóa file qua AJAX
                            const xhr = new XMLHttpRequest();
                            xhr.open('POST', form.action, true);
                            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                            
                            xhr.onload = function() {
                                if (xhr.status >= 200 && xhr.status < 300) {
                                    const response = JSON.parse(xhr.responseText);
                                    if (response.status === 'success') {
                                        alert('File đã được xóa thành công!');
                                        window.location.reload(); // Tải lại trang sau khi xóa thành công
                                    } else {
                                        alert('Lỗi: ' + response.message);
                                    }
                                } else {
                                    alert('Lỗi xảy ra: ' + xhr.statusText);
                                }
                            };

                            xhr.send(new URLSearchParams({
                                'file': file,
                                'current_folder': currentFolder
                            }).toString());
                        } else {
                            alert('Không tìm thấy thông tin file hoặc thư mục.');
                        }
                    } else {
                        alert('Không tìm thấy form để xóa file.');
                    }
                }
            } else {
                alert('Tên file không hợp lệ!');
            }
        });
    });
    
    
    
    
    

    
    
        

});
