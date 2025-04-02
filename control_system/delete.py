import os
from datetime import datetime, timedelta

# Daftar folder dan pola nama file
directories = [
    {
        "path": "/home/pi/Data/LogSeaWater",
        "prefix": "Log_WP ",
        "date_format": "%d-%m-%Y"",
        "extension": ".txt"
    },
    {
        "path": "/home/pi/Data/LogAlert",
        "prefix": "Log_AS",
        "date_format": "%d-%m-%Y"",
        "extension": ".txt"
    },
    {
        "path": "/home/pi/Data/InfoSistem_Log/Device",
        "prefix": "Device_",
        "date_format": "%Y%m%d",
        "extension": ".csv"
    },
    {
        "path": "/home/pi/data/Data_Climate",
        "prefix": "Climate_",
        "date_format": "%Y%m%d",
        "extension": ".csv"
    },
    {
        "path": "/home/pi/Data/Log_maxbo",
        "prefix": "Log_MB",
        "date_format": "%d-%m-%Y"",
        "extension": ".txt"
    },
    {
        "path": "/home/pi/Data/Pumma",
        "prefix": "Pumma_",
        "date_format": "%d-%m-%Y"",
        "extension": ".txt"
    },
    {
        "path": "/home/pi/Data/Adjusment",
        "prefix": "Data_",
        "date_format": "%d-%m-%Y"",
        "extension": ".csv"
    }
]

# Hitung batas waktu 60 hari yang lalu
sixty_days_ago = datetime.now() - timedelta(days=30)

# Fungsi untuk menghapus file berdasarkan pola
def delete_old_files(directory, prefix, date_format, extension):
    deleted_files_count = 0
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if filename.startswith(prefix) and filename.endswith(extension):
            try:
                # Ekstrak tanggal dari nama file
                date_str = filename[len(prefix):-len(extension)]
                file_date = datetime.strptime(date_str, date_format)
                
                # Jika file lebih dari 60 hari, hapus
                if file_date < sixty_days_ago:
                    os.remove(file_path)
                    deleted_files_count += 1
            except Exception as e:
                print(f"Kesalahan saat memproses file {filename} di {directory}: {e}")
    return deleted_files_count

# Total file yang dihapus
total_deleted_files = 0

# Proses semua direktori
for dir_info in directories:
    deleted_files = delete_old_files(
        directory=dir_info["path"],
        prefix=dir_info["prefix"],
        date_format=dir_info["date_format"],
        extension=dir_info["extension"]
    )
    total_deleted_files += deleted_files
    if deleted_files > 0:
        print(f"File 20 hari terakhir berhasil dihapus dari direktori {dir_info['path']}.")

# Jika tidak ada file yang memenuhi kriteria, hentikan program
if total_deleted_files == 0:
    print("Tidak ada file yang memenuhi kriteria untuk dihapus. Program dihentikan.")
else:
    # Tambahkan timestamp saat ini untuk konfirmasi
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Proses penghapusan selesai pada {current_time}. Total file yang dihapus: {total_deleted_files}.")
