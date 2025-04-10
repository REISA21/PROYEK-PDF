import mysql.connector

def save_to_database(data):
    try:
        conn = mysql.connector.connect(
            host="localhost",  # Pastikan ini benar
            user="root",      # Ganti dengan username MySQL Anda
            password="password",  # Ganti dengan password MySQL Anda
            database="produk_db"  # Pastikan database sudah dibuat
        )
        cursor = conn.cursor()
        
        # Simpan data utama
        query = """
            INSERT INTO produk (brand, product_category, harga, diskon, kategori)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data["BRAND"],
            data["PRODUCT CATEGORY"],
            data.get("harga", 0),  # Default 0 jika tidak ada
            data.get("diskon", 0),  # Default 0 jika tidak ada
            data.get("kategori", "Lainnya")  # Default "Lainnya" jika tidak ada
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

