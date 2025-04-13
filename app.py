import os
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import pandas as pd
import processor
from processor import detect_file_type
from models import db, ProcessedFile
from main import app

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

@app.route('/')
def index():
    """Render the main upload page."""
    return render_template('index.html')

@app.route('/info')
def info():
    """Render the information page with detailed transformation logic."""
    return render_template('info.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    try:
        # Check if it's a batch upload
        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            
            if not files or all(file.filename == '' for file in files):
                return jsonify({"success": False, "message": "No files selected"}), 400
            
            batch_results = []
            for file in files:
                if file.filename == '':
                    continue
                
                # Save the temporary file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                temp_filename = f"temp_{timestamp}_{file.filename}"
                file.save(temp_filename)
                
                # Determine file type
                file_type = detect_file_type(file.filename)
                
                # Process the file
                result = processor.process_file(temp_filename, file_type)
                
                # Save to database
                new_record = ProcessedFile(
                    original_filename=file.filename,
                    processed_filename=temp_filename,
                    file_type=file_type,
                    processing_time=result['processing_time'],
                    changes=result['changes']
                )
                db.session.add(new_record)
                
                batch_results.append({
                    "filename": file.filename,
                    "filetype": file_type,
                    "result": result,
                    "temp_filename": temp_filename
                })
            
            # Commit batch records to database
            db.session.commit()
            
            return jsonify({
                "success": True,
                "batch": True,
                "results": batch_results
            })
                
        # Single file upload (old behavior)
        elif 'file' in request.files:
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({"success": False, "message": "No file selected"}), 400
            
            # Save the temporary file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_filename = f"temp_{timestamp}_{file.filename}"
            file.save(temp_filename)
            
            # Determine file type
            file_type = detect_file_type(file.filename)
            
            # Process the file
            result = processor.process_file(temp_filename, file_type)
            
            # Save to database
            new_record = ProcessedFile(
                original_filename=file.filename,
                processed_filename=temp_filename,
                file_type=file_type,
                processing_time=result['processing_time'],
                changes=result['changes']
            )
            db.session.add(new_record)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "batch": False,
                "filename": file.filename,
                "filetype": file_type,
                "result": result,
                "temp_filename": temp_filename
            })
        else:
            return jsonify({"success": False, "message": "No file part"}), 400
    
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        return jsonify({"success": False, "message": f"Error processing file: {str(e)}"}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download the processed file."""
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        return jsonify({"success": False, "message": f"Error downloading file: {str(e)}"}), 500

@app.route('/download-all', methods=['POST'])
def download_all_files():
    """Generate download links for all files from a batch."""
    try:
        filenames = request.json.get('filenames', [])
        if not filenames:
            return jsonify({"success": False, "message": "No filenames provided"}), 400
            
        valid_files = []
        for filename in filenames:
            if os.path.exists(filename):
                valid_files.append({
                    "filename": filename.replace("temp_", ""),
                    "path": filename
                })
                
        return jsonify({"success": True, "files": valid_files})
    except Exception as e:
        logging.error(f"Error preparing batch download: {str(e)}")
        return jsonify({"success": False, "message": f"Error preparing batch download: {str(e)}"}), 500

@app.route('/logs')
def view_logs():
    """View processing logs."""
    log_files = []
    try:
        log_files = [f for f in os.listdir('logs') if f.startswith('logdata_')]
        log_files.sort(reverse=True)  # Most recent first
    except Exception as e:
        logging.error(f"Error reading log files: {str(e)}")
    
    return render_template('logs.html', log_files=log_files)

@app.route('/log/<filename>')
def get_log(filename):
    """Get a specific log file content."""
    try:
        with open(os.path.join('logs', filename), 'r', encoding='latin-1') as f:
            content = f.read()
        return jsonify({"success": True, "content": content})
    except Exception as e:
        logging.error(f"Error reading log file: {str(e)}")
        return jsonify({"success": False, "message": f"Error reading log file: {str(e)}"}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Remove temporary files after processing."""
    try:
        filename = request.json.get('filename', '')
        if os.path.exists(filename):
            os.remove(filename)
        return jsonify({"success": True})
    except Exception as e:
        logging.error(f"Error cleaning up file: {str(e)}")
        return jsonify({"success": False, "message": f"Error cleaning up file: {str(e)}"}), 500

@app.route('/history')
def history():
    """View history of processed files from database."""
    processed_files = ProcessedFile.query.order_by(ProcessedFile.processing_date.desc()).all()
    return render_template('history.html', processed_files=processed_files)


@app.route('/stats')
def stats():
    """View detailed statistics of file changes."""
    # Get the filter parameters from query string
    file_type = request.args.get('type', 'all')
    time_period = request.args.get('period', '7days')  # Default to last 7 days
    
    # Base query
    query = ProcessedFile.query
    
    # Apply file type filter if not 'all'
    if file_type != 'all':
        query = query.filter(ProcessedFile.file_type == file_type)
    
    # Apply time period filter
    now = datetime.now()
    if time_period == '24hours':
        query = query.filter(ProcessedFile.processing_date >= now - timedelta(days=1))
    elif time_period == '7days':
        query = query.filter(ProcessedFile.processing_date >= now - timedelta(days=7))
    elif time_period == '30days':
        query = query.filter(ProcessedFile.processing_date >= now - timedelta(days=30))
    
    # Get the processed files for the given filters
    processed_files = query.order_by(ProcessedFile.processing_date.desc()).all()
    
    # Collect statistics based on file types
    bank_stats = {'count': 0, 'total_changes': 0, 'changes_by_rule': defaultdict(int)}
    vat_stats = {'count': 0, 'total_changes': 0, 'changes_by_rule': defaultdict(int)}
    kasa_stats = {'count': 0, 'total_changes': 0, 'changes_by_rule': defaultdict(int)}
    
    # Time-based stats (for time series chart)
    time_stats = defaultdict(lambda: {'bank': 0, 'vat': 0, 'kasa': 0})
    
    for file in processed_files:
        # Skip if changes field is None
        if not file.changes:
            continue
            
        # Format date for charts
        date_str = file.processing_date.strftime('%Y-%m-%d')
        
        # Aggregate by file type
        if file.file_type == 'bank':
            bank_stats['count'] += 1
            time_stats[date_str]['bank'] += 1
            
            # Collect specific changes
            if 'zamiana_liczby_kont' in file.changes:
                bank_stats['changes_by_rule']['zamiana_liczby_kont'] += file.changes['zamiana_liczby_kont']
                bank_stats['total_changes'] += file.changes['zamiana_liczby_kont']
            
            if 'zmiana_daty' in file.changes:
                bank_stats['changes_by_rule']['zmiana_daty'] += file.changes['zmiana_daty']
                bank_stats['total_changes'] += file.changes['zmiana_daty']
            
            if 'usunięcie_wpisu' in file.changes:
                bank_stats['changes_by_rule']['usunięcie_wpisu'] += file.changes['usunięcie_wpisu']
                bank_stats['total_changes'] += file.changes['usunięcie_wpisu']
            
        elif file.file_type == 'vat':
            vat_stats['count'] += 1
            time_stats[date_str]['vat'] += 1
            
            # Collect specific changes
            if 'zakwalifikowane_vs_niezakwalifikowane' in file.changes:
                vat_stats['changes_by_rule']['zakwalifikowane_vs_niezakwalifikowane'] += file.changes['zakwalifikowane_vs_niezakwalifikowane']
                vat_stats['total_changes'] += file.changes['zakwalifikowane_vs_niezakwalifikowane']
                
            if 'niezakwalifikowane_przez_kwote' in file.changes:
                vat_stats['changes_by_rule']['niezakwalifikowane_przez_ujemną_kwotę'] += file.changes['niezakwalifikowane_przez_kwote']
                vat_stats['total_changes'] += file.changes['niezakwalifikowane_przez_kwote']
                
            if 'niezakwalifikowane_przez_date' in file.changes:
                vat_stats['changes_by_rule']['niezakwalifikowane_przez_date'] += file.changes['niezakwalifikowane_przez_date']
                vat_stats['total_changes'] += file.changes['niezakwalifikowane_przez_date']
                
        elif file.file_type == 'kasa':
            kasa_stats['count'] += 1
            time_stats[date_str]['kasa'] += 1
            
            # Collect specific changes
            if 'zamiana_9_na_0' in file.changes:
                kasa_stats['changes_by_rule']['zamiana_9_na_0'] += file.changes['zamiana_9_na_0']
                kasa_stats['total_changes'] += file.changes['zamiana_9_na_0']
                
            if 'zamiana_daty' in file.changes:
                kasa_stats['changes_by_rule']['zamiana_daty'] += file.changes['zamiana_daty']
                kasa_stats['total_changes'] += file.changes['zamiana_daty']
    
    # Convert time_stats to a format suitable for charts
    time_series_data = []
    for date_str, counts in sorted(time_stats.items()):
        time_series_data.append({
            'date': date_str,
            'bank': counts['bank'],
            'vat': counts['vat'],
            'kasa': counts['kasa']
        })
    
    # Calculate totals for pie chart
    total_files = bank_stats['count'] + vat_stats['count'] + kasa_stats['count']
    total_changes = bank_stats['total_changes'] + vat_stats['total_changes'] + kasa_stats['total_changes']
    
    return render_template(
        'stats.html',
        file_type=file_type,
        time_period=time_period,
        bank_stats=bank_stats,
        vat_stats=vat_stats,
        kasa_stats=kasa_stats,
        total_files=total_files,
        total_changes=total_changes,
        time_series_data=json.dumps(time_series_data),
        processed_files=processed_files
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
