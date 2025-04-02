#!/home/pi/code/envPumma/bin/python3

import os
import datetime

def read_last_n_lines(file_path, n):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            return [line.strip().split(',') for line in lines[-n:]]  # Menghapus newline dan split dengan koma
    except FileNotFoundError:
        print(f"File {file_path} tidak ditemukan.")
        return []

def read_last_line(file_path):
    lines = read_last_n_lines(file_path, 1)
    return lines[0] if lines else None

def main():
    today = datetime.datetime.now().strftime('%d-%m-%Y')
    wp_file = f"/home/pi/Data/LogSeaWater/Log_WP {today}.txt"
    mb_file = f"/home/pi/Data/Log_maxbo/Log_MB{today}.txt"
    
    wp_data = read_last_n_lines(wp_file, 5)
    mb_data = read_last_line(mb_file)
    
    if not wp_data or not mb_data:
        print("Data tidak ditemukan atau file kosong.")
        return
    
    wp_dict = {entry[0]: float(entry[1]) for entry in wp_data if len(entry) >= 2}
    
    mb_datetime = mb_data[1]
    mb_original_value = float(mb_data[2]) if len(mb_data) >= 2 else None
    mb_adjusted_value = mb_original_value
    
    if mb_datetime in wp_dict:
        wp_value = wp_dict[mb_datetime]
        total = 7.5
        
        if mb_original_value + wp_value != total:
            adjustment = round(total - (mb_original_value + wp_value),3)
            mb_adjusted_value += adjustment
            print(f"Nilai MB_Awal: {mb_original_value}")
            print(f"Nilai MB_Adjusment: {mb_adjusted_value}")
            print(f"Nilai Adjusment: {adjustment}")
        else:
            print(f"Nilai MB diambil dari file: {mb_original_value}")
        
        print(f"Datetime cocok: {mb_datetime}")
        print(f"Nilai WP: {wp_value}")
    else:
        print("Tidak ada data dengan datetime yang cocok.")

if __name__ == "__main__":
    main()
