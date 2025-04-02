#!/home/pi/code/envPumma/bin/python3

import os
from datetime import datetime, timedelta

# Path direktori
directory_path = "/home/pi/Data/snapshots"

# Hitung batas waktu 3 hari yang lalu
seven_days_ago = datetime.now() - timedelta(days=3)

# Loop melalui semua file di direktori
for filename in os.listdir(directory_path):
    file_path = os.path.join(directory_path, filename)
    
    # Periksa apakah file sesuai dengan pola nama
    if filename.startswith("snapshot_") and filename.endswith(".jpg"):
        try:
            # Ekstrak tanggal dari nama file
            file_date_str = filename.split('_')[1]  # Bagian tanggal
            file_date = datetime.strptime(file_date_str, "%d%m%Y")
            
            # Jika file lebih dari 7 hari, hapus
            if file_date < seven_days_ago:
                os.remove(file_path)
                print(f"File Image telah dihapus.")
        except Exception as e:
            print(f"Kesalahan saat memproses file {filename}: {e}")
