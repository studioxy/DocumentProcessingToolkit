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
    const downloadAllBtn = document.getElementById('downloadAllBtn');
    
    // Store processed filenames for batch download
    let processedFiles = [];
    
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
        } else {
            return 'unknown';
        }
    }
    
    // Handle form submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Check if we're in single or batch mode
            const isBatchMode = document.getElementById('batch-tab').classList.contains('active');
            
            // Show loading spinner
            loadingSpinner.classList.remove('d-none');
            
            // Clear previous results
            resultContainer.classList.add('d-none');
            batchResultContainer.classList.add('d-none');
            
            // Create form data
            const formData = new FormData();
            
            if (isBatchMode) {
                const files = batchFileInput.files;
                if (files.length === 0) {
                    showAlert('Proszę wybrać co najmniej jeden plik do przetworzenia wsadowego.', 'danger');
                    loadingSpinner.classList.add('d-none');
                    return;
                }
                
                for (let i = 0; i < files.length; i++) {
                    formData.append('files[]', files[i]);
                }
            } else {
                const file = fileInput.files[0];
                if (!file) {
                    showAlert('Proszę wybrać plik do przetworzenia.', 'danger');
                    loadingSpinner.classList.add('d-none');
                    return;
                }
                
                formData.append('file', file);
            }
            
            // Send AJAX request
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loadingSpinner.classList.add('d-none');
                
                if (!data.success) {
                    showAlert(data.message || 'Wystąpił błąd podczas przetwarzania pliku.', 'danger');
                    return;
                }
                
                if (data.batch) {
                    // Batch processing results
                    batchResultContainer.classList.remove('d-none');
                    populateBatchResults(data);
                    
                    // Scroll to results
                    batchResultContainer.scrollIntoView({ behavior: 'smooth' });
                } else {
                    // Single file processing results
                    resultContainer.classList.remove('d-none');
                    populateSingleResults(data);
                    
                    // Scroll to results
                    resultContainer.scrollIntoView({ behavior: 'smooth' });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                loadingSpinner.classList.add('d-none');
                showAlert('Wystąpił błąd podczas przetwarzania pliku.', 'danger');
            });
        });
    }
    
    // Handle download all button click
    if (downloadAllBtn) {
        downloadAllBtn.addEventListener('click', function() {
            if (processedFiles.length === 0) {
                showAlert('Brak plików do pobrania.', 'warning');
                return;
            }
            
            fetch('/download-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ filenames: processedFiles })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.files.length > 0) {
                    // Sequentially download each file
                    data.files.forEach((file, index) => {
                        // Use setTimeout to space out downloads slightly
                        setTimeout(() => {
                            const a = document.createElement('a');
                            a.href = `/download/${file.path}`;
                            a.download = file.filename;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                        }, index * 500);
                    });
                    
                    showAlert(`Pobieranie ${data.files.length} plików w toku...`, 'success');
                } else {
                    showAlert('Nie znaleziono plików do pobrania.', 'warning');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('Wystąpił błąd podczas przygotowywania plików do pobrania.', 'danger');
            });
        });
    }
    
    // Populate results for single file processing
    function populateSingleResults(data) {
        const fileInfoContainer = document.getElementById('fileInfo');
        const processingTimeContainer = document.getElementById('processingTime');
        const changesInfoContainer = document.getElementById('changesInfo');
        
        // Basic info
        fileInfoContainer.textContent = `${data.filename} (${data.filetype})`;
        processingTimeContainer.textContent = `${data.result.processing_time.toFixed(2)} sekund`;
        
        // Changes info
        let changesHTML = '';
        const changes = data.result.changes;
        
        if (data.filetype === 'bank') {
            changesHTML = `
                <div class="row mt-3">
                    <div class="col-md-4">
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>Zmiany konta 202-2-1-900102 na 131-5</h6>
                                <p class="mb-0 counter-value">${changes.zmiany_konto_900102}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>Zmiany dat</h6>
                                <p class="mb-0 counter-value">${changes.zmiany_data}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>Zmiany konta 9 na 0</h6>
                                <p class="mb-0 counter-value">${changes.zmiany_konto_9}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else if (data.filetype === 'vat') {
            changesHTML = `
                <div class="row mt-3">
                    <div class="col-md-4">
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>Zmiany konta 731</h6>
                                <p class="mb-0 counter-value">${changes.zmiany_konto_731}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>Zmiany okresu</h6>
                                <p class="mb-0 counter-value">${changes.zmiany_okres}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>Całkowita liczba zmian</h6>
                                <p class="mb-0 counter-value">${changes.zmiany_konto_731 + changes.zmiany_okres}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else if (data.filetype === 'kasa') {
            changesHTML = `
                <div class="row mt-3">
                    <div class="col-md-4">
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>Zmiany konta 9 na 0</h6>
                                <p class="mb-0 counter-value">${changes.zmiany_konto_9}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>Konto 201-2-1-9</h6>
                                <p class="mb-0 counter-value">${changes.zmiany_konto_201 || 0}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>Konto 202-2-1-9</h6>
                                <p class="mb-0 counter-value">${changes.zmiany_konto_202 || 0}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        changesInfoContainer.innerHTML = changesHTML;
        
        // Set download button URL
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
        
        // Store filenames for batch download
        processedFiles = tempFilenames;
        
        // Enable download all button if we have files
        if (downloadAllBtn && processedFiles.length > 0) {
            downloadAllBtn.classList.remove('d-none');
        }
        
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
        let accordionIndex = 0;
        for (const [type, files] of Object.entries(filesByType)) {
            if (files.length === 0) continue;
            
            // Skip unknown files
            if (type === 'unknown' && files.length === 0) continue;
            
            // Create group header
            const accordionItem = document.createElement('div');
            accordionItem.className = 'accordion-item';
            
            // Translate file type for display
            let typeDisplay = '';
            switch(type) {
                case 'bank':
                    typeDisplay = 'Dokumenty Bankowe';
                    break;
                case 'vat':
                    typeDisplay = 'Dokumenty VAT';
                    break;
                case 'kasa':
                    typeDisplay = 'Dokumenty Kasowe';
                    break;
                default:
                    typeDisplay = 'Inne Dokumenty';
            }
            
            accordionItem.innerHTML = `
                <h2 class="accordion-header" id="heading${accordionIndex}">
                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${accordionIndex}" aria-expanded="true" aria-controls="collapse${accordionIndex}">
                        <span class="me-2 badge bg-primary">${files.length}</span>
                        ${typeDisplay}
                    </button>
                </h2>
                <div id="collapse${accordionIndex}" class="accordion-collapse collapse show" aria-labelledby="heading${accordionIndex}">
                    <div class="accordion-body p-0">
                        <div class="list-group list-group-flush">
                            ${files.map((file, index) => createFileResultItem(file, index)).join('')}
                        </div>
                    </div>
                </div>
            `;
            
            accordionContainer.appendChild(accordionItem);
            accordionIndex++;
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
                        <span class="badge bg-info">Całkowita liczba zmian: ${changes.zmiany_konto_731 + changes.zmiany_okres}</span>
                    </div>
                </div>
            `;
        } else if (file.filetype === 'kasa') {
            changesHTML = `
                <div class="row">
                    <div class="col-md-4">
                        <span class="badge bg-info">Konto 9 → 0: ${changes.zmiany_konto_9}</span>
                    </div>
                    <div class="col-md-4">
                        <span class="badge bg-info">Konto 201-2-1-9: ${changes.zmiany_konto_201 || 0}</span>
                    </div>
                    <div class="col-md-4">
                        <span class="badge bg-info">Konto 202-2-1-9: ${changes.zmiany_konto_202 || 0}</span>
                    </div>
                </div>
            `;
        }
        
        return `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="mb-0">${file.filename}</h6>
                    <div>
                        <span class="badge bg-primary">${(file.result.processing_time).toFixed(2)}s</span>
                        <a href="/download/${file.temp_filename}" class="btn btn-sm btn-outline-primary ms-2">
                            <i class="fas fa-download"></i>
                        </a>
                    </div>
                </div>
                ${changesHTML}
            </div>
        `;
    }
    
    function showAlert(message, type) {
        alertContainer.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = document.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }
});

function loadLogContent(filename) {
    fetch(`/log/${filename}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const logContentContainer = document.getElementById('logContent');
                if (logContentContainer) {
                    logContentContainer.textContent = data.content;
                    // Highlight the selected log
                    document.querySelectorAll('.log-item').forEach(item => {
                        item.classList.remove('active');
                    });
                    document.getElementById(`log-${filename}`).classList.add('active');
                    
                    // Update the active log filename display
                    const activeLogFilename = document.getElementById('activeLogFilename');
                    if (activeLogFilename) {
                        activeLogFilename.textContent = filename;
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error loading log content:', error);
        });
}
