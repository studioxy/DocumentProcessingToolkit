document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const resultContainer = document.getElementById('resultContainer');
    const detailedResults = document.getElementById('detailedResults');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const alertContainer = document.getElementById('alertContainer');
    const fileTypeDisplay = document.getElementById('fileTypeDisplay');
    
    // Auto-detect file type based on filename
    fileInput.addEventListener('change', function() {
        const filename = this.files[0]?.name.toLowerCase() || '';
        let fileType = 'unknown';
        
        if (filename.includes('bank')) {
            fileType = 'bank';
        } else if (filename.includes('vat')) {
            fileType = 'vat';
        } else if (filename.includes('zak') || filename.includes('kasa')) {
            fileType = 'kasa';
        }
        
        fileTypeDisplay.textContent = fileType !== 'unknown' ? 
            `Wykryto typ pliku: ${fileType}` : 
            'Nie udało się automatycznie wykryć typu pliku';
    });
    
    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!fileInput.files[0]) {
            showAlert('Proszę wybrać plik do przetworzenia.', 'danger');
            return;
        }
        
        // Show loading spinner
        loadingSpinner.classList.remove('d-none');
        resultContainer.classList.add('d-none');
        
        // Clear previous alerts
        alertContainer.innerHTML = '';
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingSpinner.classList.add('d-none');
            
            if (data.success) {
                resultContainer.classList.remove('d-none');
                populateResults(data);
            } else {
                showAlert(data.message || 'Wystąpił błąd podczas przetwarzania pliku.', 'danger');
            }
        })
        .catch(error => {
            loadingSpinner.classList.add('d-none');
            showAlert('Błąd sieciowy: ' + error.message, 'danger');
        });
    });
    
    function populateResults(data) {
        // Update the filename and file type
        document.getElementById('processedFilename').textContent = data.filename;
        document.getElementById('processedFiletype').textContent = data.filetype;
        
        // Update processing time
        document.getElementById('processingTime').textContent = data.result.processing_time_ms.toFixed(2) + ' ms';
        
        // Clear previous detailed results
        detailedResults.innerHTML = '';
        
        // Display changes based on file type
        const changes = data.result.changes;
        let html = '<table class="table table-striped"><thead><tr><th>Typ zmiany</th><th>Ilość</th></tr></thead><tbody>';
        
        if (data.filetype === 'bank') {
            html += `
                <tr><td>Zmiany konta 202-2-1-900102 na 131-5</td><td>${changes.zmiany_konto_900102}</td></tr>
                <tr><td>Zmiany dat</td><td>${changes.zmiany_data}</td></tr>
                <tr><td>Zmiany konta 9 na 0</td><td>${changes.zmiany_konto_9}</td></tr>
            `;
        } else if (data.filetype === 'vat') {
            html += `
                <tr><td>Zmiany konta 731-1, 731-3, 731-4 na odpowiednie wartości</td><td>${changes.zmiany_konto_731}</td></tr>
                <tr><td>Zmiany daty okresu na ostatni dzień poprzedniego miesiąca</td><td>${changes.zmiany_okres}</td></tr>
                <tr><td>Przypadki niezakwalifikowane przez kwotę <= 0</td><td>${changes.niezakwalifikowane_przez_kwote}</td></tr>
            `;
        } else if (data.filetype === 'kasa') {
            html += `
                <tr><td>Zmiany konta 9 na 0</td><td>${changes.zmiany_konto_9}</td></tr>
            `;
        }
        
        html += '</tbody></table>';
        
        // Add errors if any
        if (data.result.errors && data.result.errors.length > 0) {
            html += '<div class="alert alert-danger mt-3"><h5>Błędy:</h5><ul>';
            data.result.errors.forEach(error => {
                html += `<li>${error}</li>`;
            });
            html += '</ul></div>';
        }
        
        // Add download and log buttons
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.setAttribute('href', `/download/${data.temp_filename}`);
        downloadBtn.classList.remove('d-none');
        
        const viewLogBtn = document.getElementById('viewLogBtn');
        const logFilename = data.result.log_file.split('/').pop();
        viewLogBtn.setAttribute('href', `/logs#${logFilename}`);
        viewLogBtn.classList.remove('d-none');
        
        detailedResults.innerHTML = html;
        
        // Setup cleanup when page is unloaded
        window.addEventListener('beforeunload', function() {
            navigator.sendBeacon('/cleanup', JSON.stringify({ filename: data.temp_filename }));
        });
    }
    
    function showAlert(message, type) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        alertContainer.appendChild(alert);
    }
});

// Log viewer functions
function loadLogContent(filename) {
    const logContent = document.getElementById('logContent');
    logContent.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Ładowanie pliku...</p></div>';
    
    fetch(`/log/${filename}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Format the log content for better readability
                const formattedContent = data.content
                    .replace(/\n/g, '<br>')
                    .replace(/(-{80})/g, '<hr>');
                
                logContent.innerHTML = `<div class="log-entry">${formattedContent}</div>`;
                
                // Scroll to the selected log in the sidebar
                const logItem = document.getElementById(`log-${filename}`);
                if (logItem) {
                    logItem.scrollIntoView({ behavior: 'smooth' });
                }
                
                // Highlight the selected log in the sidebar
                document.querySelectorAll('.log-item').forEach(item => {
                    item.classList.remove('active');
                });
                logItem.classList.add('active');
                
                // Update URL hash
                window.location.hash = filename;
            } else {
                logContent.innerHTML = `<div class="alert alert-danger">Błąd: ${data.message}</div>`;
            }
        })
        .catch(error => {
            logContent.innerHTML = `<div class="alert alert-danger">Błąd sieciowy: ${error.message}</div>`;
        });
}

// Check for hash in URL when logs page loads
window.addEventListener('load', function() {
    if (document.getElementById('logsList') && window.location.hash) {
        const filename = window.location.hash.substring(1);
        loadLogContent(filename);
    }
});
