import os
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, send_file, session
from werkzeug.utils import secure_filename
from product_system.processor import DocumentProcessor  # Impor DocumentProcessor untuk dokumen tunggal
from product_system.multi_processor import MultiDocumentProcessor, process_multiple_files  # Impor untuk dokumen multi
import json

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Diperlukan untuk menggunakan session

# Konfigurasi folder (gunakan path absolut)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Direktori backend/
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'database', 'product_system', 'uploads')
CSV_FOLDER = os.path.join(BASE_DIR, 'database', 'product_system', 'csv_outputs')
JSON_FOLDER = os.path.join(BASE_DIR, 'database', 'product_system', 'json_outputs')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CSV_FOLDER'] = CSV_FOLDER
app.config['JSON_FOLDER'] = JSON_FOLDER

# Pastikan folder ada dan memiliki izin tulis
for folder in [UPLOAD_FOLDER, CSV_FOLDER, JSON_FOLDER]:
    print(f"Checking if folder exists: {folder}")
    if not os.path.exists(folder):
        print(f"Folder does not exist, creating: {folder}")
        os.makedirs(folder, exist_ok=True)
    else:
        print(f"Folder already exists: {folder}")

    # Periksa izin tulis
    try:
        test_file = os.path.join(folder, "test_write.txt")
        with open(test_file, 'w') as f:
            f.write("Test write permission")
        os.remove(test_file)
        print(f"Write permission confirmed for folder: {folder}")
    except Exception as e:
        print(f"Error: No write permission for folder {folder}: {str(e)}")
        raise Exception(f"Cannot proceed due to lack of write permission in {folder}")

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    error = request.args.get('error')
    success = request.args.get('success')
    print(f"Rendering index with error: {error}, success: {success}")  # Debugging

    # Ambil daftar nomor dokumen dan waktu upload dari session
    uploaded_files = session.get('uploaded_files', [])
    print(f"Uploaded files from session: {uploaded_files}")  # Debugging

    # Konversi data lama (jika ada) dari list string ke list dictionary
    converted_files = []
    for item in uploaded_files:
        if isinstance(item, str):
            # Jika item adalah string (data lama), konversi ke dictionary
            converted_files.append({
                'nomor': item,
                'upload_time': 'Unknown'  # Waktu tidak diketahui untuk data lama
            })
        elif isinstance(item, dict) and 'nomor' in item and 'upload_time' in item:
            # Jika item sudah dalam format dictionary yang benar, gunakan langsung
            converted_files.append(item)
        else:
            # Abaikan item yang tidak sesuai format
            print(f"Skipping invalid session item: {item}")
            continue

    # Simpan kembali data yang telah dikonversi ke session
    session['uploaded_files'] = converted_files
    print(f"Converted uploaded files: {converted_files}")  # Debugging

    # Siapkan daftar file JSON yang akan ditampilkan
    json_files = []
    for file_info in converted_files:
        nomor = file_info['nomor']
        upload_time = file_info['upload_time']
        json_path = os.path.join(app.config['JSON_FOLDER'], f"{nomor}.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as json_file:
                    json_data = json.load(json_file)
                json_files.append({
                    'nomor': nomor,
                    'json_data': json_data,
                    'upload_time': upload_time
                })
            except Exception as e:
                print(f"Error reading JSON file {json_path}: {str(e)}")
                error = f"Gagal membaca JSON: {str(e)}"

    return render_template('upload.html', error=error, success=success, json_files=json_files)

@app.route('/upload-single', methods=['POST'])
def upload_single_file():
    print("Route /upload-single called")  # Debugging
    if 'file' not in request.files:
        print("No file part in request")  # Debugging
        return redirect(url_for('index', error="Harap pilih satu file PDF."))
    
    file = request.files['file']
    print("File received:", file.filename)  # Debugging
    
    if file.filename == '':
        print("No file selected")  # Debugging
        return redirect(url_for('index', error="Harap pilih satu file PDF."))
    
    if not file or not allowed_file(file.filename):
        print("File not allowed:", file.filename)  # Debugging
        return redirect(url_for('index', error="File harus berupa PDF."))

    pdf_path = None
    csv_path = None
    json_path = None
    try:
        # Simpan file PDF
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        csv_filename = f"{timestamp}_{filename.rsplit('.', 1)[0]}.csv"
        csv_path = os.path.join(app.config['CSV_FOLDER'], csv_filename)

        print("Saving file to:", pdf_path)  # Debugging
        file.save(pdf_path)

        # Proses file menggunakan DocumentProcessor
        print("Processing file with DocumentProcessor")  # Debugging
        processor = DocumentProcessor()
        print(f"Processor class used: {processor.__class__.__name__}")  # Debugging
        json_data = processor.process(pdf_path, csv_path)

        # Validasi json_data
        print("json_data:", json_data)  # Debugging
        if not json_data:
            print("Error: json_data is empty or None")  # Debugging
            return redirect(url_for('index', error="Gagal memproses file: Data JSON kosong."))

        # Gunakan nomor dokumen sebagai nama file JSON
        nomor = json_data.get('list_break')[0].get('name').split()[0]  # Ambil nomor dari JSON
        if not nomor:
            print("Error: Nomor dokumen tidak ditemukan di data")  # Debugging
            return redirect(url_for('index', error="Gagal memproses file: Nomor dokumen tidak ditemukan."))
        
        json_filename = f"{nomor}.json"
        json_path = os.path.join(app.config['JSON_FOLDER'], json_filename)

        # Simpan JSON
        print("Saving JSON to:", json_path)  # Debugging
        try:
            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, indent=4)
            print("JSON successfully saved to:", json_path)  # Debugging
            # Verifikasi bahwa file benar-benar ada
            if os.path.exists(json_path):
                print(f"Verified: JSON file exists at {json_path}")
            else:
                print(f"Error: JSON file does not exist at {json_path} after saving")
                return redirect(url_for('index', error="Gagal menyimpan JSON: File tidak ditemukan setelah disimpan."))
        except Exception as e:
            print("Error saving JSON:", str(e))  # Debugging
            return redirect(url_for('index', error=f"Gagal menyimpan JSON: {str(e)}"))

        # Verifikasi ulang setelah semua proses selesai
        if os.path.exists(json_path):
            print(f"Final verification: JSON file still exists at {json_path}")
        else:
            print(f"Final verification failed: JSON file no longer exists at {json_path}")
            return redirect(url_for('index', error="Gagal menyimpan JSON: File hilang setelah disimpan."))

        # Tambahkan nomor dokumen dan waktu upload ke session
        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uploaded_files = session.get('uploaded_files', [])
        # Periksa apakah nomor sudah ada, jika ya, update waktu upload
        for file_info in uploaded_files:
            if isinstance(file_info, dict) and file_info.get('nomor') == nomor:
                file_info['upload_time'] = upload_time
                break
        else:
            uploaded_files.append({'nomor': nomor, 'upload_time': upload_time})
        session['uploaded_files'] = uploaded_files
        print(f"Updated session uploaded_files: {uploaded_files}")  # Debugging

        return redirect(url_for('index', success="Berhasil mengunggah dan memproses file."))

    except Exception as e:
        print("Error during processing:", str(e))  # Debugging
        return redirect(url_for('index', error=f"Terjadi kesalahan: {str(e)}"))

    finally:
        # Hapus file sementara
        if pdf_path and os.path.exists(pdf_path):
            print("Removing temporary PDF file:", pdf_path)  # Debugging
            os.remove(pdf_path)
        if csv_path and os.path.exists(csv_path):
            print("Removing temporary CSV file:", csv_path)  # Debugging
            os.remove(csv_path)

@app.route('/upload-multiple', methods=['POST'])
def upload_multiple_files():
    print("Route /upload-multiple called")  # Debugging
    if 'files[]' not in request.files:
        print("No files part in request")  # Debugging
        return redirect(url_for('index', error="Harap pilih setidaknya satu file PDF."))

    files = request.files.getlist('files[]')
    print("Files received:", [file.filename for file in files])  # Debugging
    if not files or all(file.filename == '' for file in files):
        print("No files selected")  # Debugging
        return redirect(url_for('index', error="Harap pilih setidaknya satu file PDF."))

    # Pastikan setidaknya satu file diunggah
    if len(files) < 1:
        print("No valid files uploaded")  # Debugging
        return redirect(url_for('index', error="Harap unggah setidaknya satu file PDF."))

    valid_files = []
    for file in files:
        if file and allowed_file(file.filename):
            valid_files.append(file)
        else:
            print("File not allowed:", file.filename)  # Debugging
            return redirect(url_for('index', error="Semua file harus berupa PDF."))
    
    if len(valid_files) < 1:
        print("No valid files after filtering:", len(valid_files))  # Debugging
        return redirect(url_for('index', error="Harap unggah setidaknya satu file PDF yang valid."))

    file_list = []
    try:
        # Simpan file PDF sementara dan siapkan untuk pemrosesan
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for idx, file in enumerate(valid_files):
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{idx}_{filename}")
            csv_filename = f"{timestamp}_{idx}_{filename.rsplit('.', 1)[0]}.csv"
            csv_path = os.path.join(app.config['CSV_FOLDER'], csv_filename)

            print("Saving file to:", pdf_path)  # Debugging
            file.save(pdf_path)
            file_list.append({
                "pdf_path": pdf_path,
                "csv_path": csv_path,
                "filename": filename
            })

        # Proses multiple files menggunakan multi_processor.py
        print("Processing files with multi_processor.py")  # Debugging
        json_outputs = process_multiple_files(file_list)

        # Validasi json_outputs
        print("json_outputs:", json_outputs)  # Debugging
        if not json_outputs:
            print("Error: json_outputs is empty or None")  # Debugging
            return redirect(url_for('index', error="Gagal memproses file: Data JSON kosong."))

        # Simpan JSON dengan nama berdasarkan nomor dokumen
        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uploaded_files = session.get('uploaded_files', [])
        for json_data, nomor in json_outputs:
            json_filename = f"{nomor}.json"
            json_path = os.path.join(app.config['JSON_FOLDER'], json_filename)

            print("Saving JSON to:", json_path)  # Debugging
            try:
                with open(json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(json_data, json_file, indent=4)
                print("JSON successfully saved to:", json_path)  # Debugging
                # Verifikasi bahwa file benar-benar ada
                if os.path.exists(json_path):
                    print(f"Verified: JSON file exists at {json_path}")
                else:
                    print(f"Error: JSON file does not exist at {json_path} after saving")
                    return redirect(url_for('index', error="Gagal menyimpan JSON: File tidak ditemukan setelah disimpan."))
            except Exception as e:
                print("Error saving JSON:", str(e))  # Debugging
                return redirect(url_for('index', error=f"Gagal menyimpan JSON: {str(e)}"))

            # Tambahkan nomor dokumen dan waktu upload ke session
            for file_info in uploaded_files:
                if isinstance(file_info, dict) and file_info.get('nomor') == nomor:
                    file_info['upload_time'] = upload_time
                    break
            else:
                uploaded_files.append({'nomor': nomor, 'upload_time': upload_time})

        # Verifikasi ulang setelah semua proses selesai
        for json_data, nomor in json_outputs:
            json_filename = f"{nomor}.json"
            json_path = os.path.join(app.config['JSON_FOLDER'], json_filename)
            if os.path.exists(json_path):
                print(f"Final verification: JSON file still exists at {json_path}")
            else:
                print(f"Final verification failed: JSON file no longer exists at {json_path}")
                return redirect(url_for('index', error="Gagal menyimpan JSON: File hilang setelah disimpan."))

        session['uploaded_files'] = uploaded_files
        print(f"Updated session uploaded_files: {uploaded_files}")  # Debugging

        return redirect(url_for('index', success=f"Berhasil mengunggah dan memproses {len(valid_files)} file."))

    except Exception as e:
        print("Error during processing:", str(e))  # Debugging
        return redirect(url_for('index', error=f"Terjadi kesalahan: {str(e)}"))

    finally:
        # Hapus file sementara
        for file_info in file_list:
            pdf_path = file_info['pdf_path']
            csv_path = file_info['csv_path']
            if os.path.exists(pdf_path):
                print("Removing temporary PDF file:", pdf_path)  # Debugging
                os.remove(pdf_path)
            if os.path.exists(csv_path):
                print("Removing temporary CSV file:", csv_path)  # Debugging
                os.remove(csv_path)

@app.route('/download/<filename>')
def download_json(filename):
    print(f"Route /download/{filename} called")  # Debugging
    json_path = os.path.join(app.config['JSON_FOLDER'], f"{filename}.json")
    print(f"Looking for JSON file at: {json_path}")  # Debugging
    if os.path.exists(json_path):
        print(f"JSON file found, sending: {json_path}")  # Debugging
        return send_file(json_path, as_attachment=True, download_name=f"{filename}.json")
    else:
        print(f"JSON file not found: {json_path}")  # Debugging
        return redirect(url_for('index', error="File JSON tidak ditemukan."))

@app.route('/delete/<filename>', methods=['POST'])
def delete_json(filename):
    print(f"Route /delete/{filename} called")  # Debugging
    json_path = os.path.join(app.config['JSON_FOLDER'], f"{filename}.json")
    print(f"Looking for JSON file to delete at: {json_path}")  # Debugging
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
            print(f"JSON file deleted: {json_path}")  # Debugging
            # Hapus nomor dari session
            uploaded_files = session.get('uploaded_files', [])
            uploaded_files = [file_info for file_info in uploaded_files if file_info.get('nomor') != filename]
            session['uploaded_files'] = uploaded_files
            print(f"Updated session uploaded_files after deletion: {uploaded_files}")  # Debugging
            return redirect(url_for('index', success=f"Berhasil menghapus file {filename}.json"))
        except Exception as e:
            print(f"Error deleting JSON file: {str(e)}")  # Debugging
            return redirect(url_for('index', error=f"Gagal menghapus file: {str(e)}"))
    else:
        print(f"JSON file not found for deletion: {json_path}")  # Debugging
        return redirect(url_for('index', error="File JSON tidak ditemukan."))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)