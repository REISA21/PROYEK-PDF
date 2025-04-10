import sqlite3
import os

DATABASE_PATH = 'database/database.db'

def init_db():
    """Inisialisasi database dan buat tabel jika belum ada."""
    if not os.path.exists('database'):
        os.makedirs('database')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            brand TEXT NOT NULL,
            sku TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_timestamp INTEGER NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def save_product_record(category, brand, sku, upload_date, file_path, upload_timestamp):
    """Simpan record produk ke database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO product_records (category, brand, sku, upload_date, file_path, upload_timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (category, brand, sku, upload_date, file_path, upload_timestamp))
    
    conn.commit()
    conn.close()

def get_product_records():
    """Ambil semua record produk dari database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM product_records')
    records = cursor.fetchall()
    
    conn.close()
    return records

# lanjud besok kalo mau update
init_db()