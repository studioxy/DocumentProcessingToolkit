document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const batchFileInput = document.getElementById('batchFileInput');
    const uploadForm = document.getElementById('uploadForm');
    const resultContainer = document.getElementById('resultContainer');
    const batchResultContainer = document.getElementById('batchResultContainer');
    const detailedResults = document.getElementById('detailedResults');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const alertContainer = document.getElementById('alertContainer');
    const fileTypeDisplay = document.getElementById('fileTypeDisplay');
    
    // Auto-detect file type based on filename for single file
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const filename = this.files[0]?.name.toLowerCase() || '';
            let fileType = detectFileType(filename);
            
            fileTypeDisplay.textContent = fileType !== 'unknown' ? 
                `Wykryto typ pliku: ${fileType}` : 
                'Nie udało się automatycznie wykryć typu pliku';
        });
    }
    
    // Function to detect file type
    function detectFileType(filename) {
        if (filename.includes('bank')) {
            return 'bank';
        } else if (filename.includes('vat')) {
            return 'vat';
        } else if (filename.includes('zak') || filename.includes('kasa')) {
            return 'kasa';
        }
        return 'unknown';
    }
    
    // Handle form submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Determine if it's a batch or single file upload
            const activeTab = document.querySelector('.tab-pane.active');
            const isBatchUpload = activeTab.id === 'batch-upload';
            
            if (isBatchUpload) {
                if (!batchFileInput.files.length) {
                    showAlert('Proszę wybrać pliki do przetworzenia wsadowego.', 'danger');
                    return;
                }
            } else {
                if (!fileInput.files[0]) {
                    showAlert('Proszę wybrać plik do przetworzenia.', 'danger');
                    return;
                }
            }
            
            // Show loading spinner
            loadingSpinner.classList.remove('d-none');
            resultContainer.classList.add('d-none');
            batchResultContainer.classList.add('d-none');
            
            // Clear previous alerts
            alertContainer.innerHTML = '';
            
            const formData = new FormData();
            
            if (isBatchUpload) {
                // Append all files for batch processing
                for (let i = 0; i < batchFileInput.files.length; i++) {
                    formData.append('files[]', batchFileInput.files[i]);
                }
            } else {
                // Single file processing
                formData.append('file', fileInput.files[0]);
            }
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loadingSpinner.classList.add('d-none');
                
                if (data.success) {
                    if (data.batch) {
                        // Display batch results
                        batchResultContainer.classList.remove('d-none');
                        populateBatchResults(data);
                    } else {
                        // Display single file results
                        resultContainer.classList.remove('d-none');
                        populateSingleResults(data);
                    }
                } else {
                    showAlert(data.message || 'Wystąpił błąd podczas przetwarzania.', 'danger');
                }
            })
            .catch(error => {
                loadingSpinner.classList.add('d-none');
                showAlert('Błąd sieciowy: ' + error.message, 'danger');
            });
        });
    }
    
    // Populate results for a single file processing
    function populateSingleResults(data) {
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
    
    // Populate results for batch processing
    function populateBatchResults(data) {
        const batchResults = data.results;
        const totalProcessedFiles = batchResults.length;
        
        document.getElementById('totalProcessedFiles').textContent = totalProcessedFiles;
        
        // Create accordion for each file
        const accordionContainer = document.getElementById('batchResultsAccordion');
        accordionContainer.innerHTML = '';
        
        // Setup cleanup for all temp files when page is unloaded
        const tempFilenames = batchResults.map(item => item.temp_filename);
        window.addEventListener('beforeunload', function() {
            tempFilenames.forEach(filename => {
                navigator.sendBeacon('/cleanup', JSON.stringify({ filename }));
            });
        });
        
        // Group files by type
        const filesByType = {
            bank: [],
            vat: [],
            kasa: [],
            unknown: []
        };
        
        batchResults.forEach(result => {
            filesByType[result.filetype || 'unknown'].push(result);
        });
        
        // Create accordion items grouped by file type
        for (const [fileType, files] of Object.entries(filesByType)) {
            if (files.length === 0) continue;
            
            let fileTypeLabel = '';
            let fileTypeIcon = '';
            
            switch(fileType) {
                case 'bank':
                    fileTypeLabel = 'Dokumenty bankowe';
                    fileTypeIcon = 'fa-university';
                    break;
                case 'vat':
                    fileTypeLabel = 'Dokumenty VAT';
                    fileTypeIcon = 'fa-file-invoice';
                    break;
                case 'kasa':
                    fileTypeLabel = 'Dokumenty kasowe';
                    fileTypeIcon = 'fa-cash-register';
                    break;
                default:
                    fileTypeLabel = 'Inne dokumenty';
                    fileTypeIcon = 'fa-file-alt';
            }
            
            const accordionId = `accordion-${fileType}`;
            
            const accordionItem = document.createElement('div');
            accordionItem.className = 'accordion-item';
            accordionItem.innerHTML = `
                <h2 class="accordion-header" id="heading-${fileType}">
                    <button class="accordion-button" type="button" data-bs-toggle="collapse" 
                            data-bs-target="#${accordionId}" aria-expanded="true" 
                            aria-controls="${accordionId}">
                        <i class="fas ${fileTypeIcon} me-2"></i>
                        ${fileTypeLabel} (${files.length})
                    </button>
                </h2>
                <div id="${accordionId}" class="accordion-collapse collapse show" 
                     aria-labelledby="heading-${fileType}" data-bs-parent="#batchResultsAccordion">
                    <div class="accordion-body p-0">
                        <div class="list-group list-group-flush">
                            ${files.map((file, index) => createFileResultItem(file, index)).join('')}
                        </div>
                    </div>
                </div>
            `;
            
            accordionContainer.appendChild(accordionItem);
        }
    }
    
    // Create a list item for each file in batch results
    function createFileResultItem(file, index) {
        const changes = file.result.changes;
        let changesHTML = '';
        
        if (file.filetype === 'bank') {
            changesHTML = `
                <div class="row">
                    <div class="col-md-4">
                        <span class="badge bg-info">Konto 202-2-1-900102 → 131-5: ${changes.zmiany_konto_900102}</span>
                    </div>
                    <div class="col-md-4">
                        <span class="badge bg-info">Zmiany dat: ${changes.zmiany_data}</span>
                    </div>
                    <div class="col-md-4">
                        <span class="badge bg-info">Konto 9 → 0: ${changes.zmiany_konto_9}</span>
                    </div>
                </div>
            `;
        } else if (file.filetype === 'vat') {
            changesHTML = `
                <div class="row">
                    <div class="col-md-4">
                        <span class="badge bg-info">Konto 731: ${changes.zmiany_konto_731}</span>
                    </div>
                    <div class="col-md-4">
                        <span class="badge bg-info">Zmiany okresu: ${changes.zmiany_okres}</span>
                    </div>
                    <div class="col-md-4">
                        <span class="badge bg-secondary">Niezakwalifikowane: ${changes.niezakwalifikowane_przez_kwote}</span>
                    </div>
                </div>
            `;
        } else if (file.filetype === 'kasa') {
            changesHTML = `
                <div class="row">
                    <div class="col-md-12">
                        <span class="badge bg-info">Konto 9 → 0: ${changes.zmiany_konto_9}</span>
                    </div>
                </div>
            `;
        }
        
        const logFilename = file.result.log_file.split('/').pop();
        
        return `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between align-items-center">
                    <h6 class="mb-1">${file.filename}</h6>
                    <small>Czas: ${file.result.processing_time_ms.toFixed(2)} ms</small>
                </div>
                <div class="mt-2">
                    ${changesHTML}
                </div>
                <div class="d-flex justify-content-end mt-2">
                    <a href="/download/${file.temp_filename}" class="btn btn-sm btn-success me-2">
                        <i class="fas fa-download"></i> Pobierz
                    </a>
                    <a href="/logs#${logFilename}" class="btn btn-sm btn-info">
                        <i class="fas fa-list"></i> Log
                    </a>
                </div>
            </div>
        `;
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
