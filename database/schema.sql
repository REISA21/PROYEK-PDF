CREATE DATABASE IF NOT EXISTS produk_db;

USE produk_db;

CREATE TABLE IF NOT EXISTS produk (
    id INT AUTO_INCREMENT PRIMARY KEY,
    brand VARCHAR(255),
    product_category VARCHAR(255),
    harga DECIMAL(10, 2),
    diskon DECIMAL(5, 2),
    kategori VARCHAR(255)
);

-- Tabel untuk menyimpan data produk (khusus aplikasi baru)
CREATE TABLE IF NOT EXISTS product_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    brand TEXT NOT NULL,
    sku TEXT NOT NULL,
    upload_date TEXT NOT NULL,
    file_path TEXT NOT NULL
);


