#!/home/pi/code/envPumma/bin/python3

import psutil

def get_system_stats():
    cpu_usage = psutil.cpu_percent(interval=1)  # Persentase penggunaan CPU dalam 1 detik
    disk_usage = psutil.disk_usage('/')  # Informasi penggunaan disk
    
    stats = {
        "cpu_usage": f"{cpu_usage} %",
        "disk_free": f"{disk_usage.free / (1024 ** 3):.2f} GB",
        "disk_total": f"{disk_usage.total / (1024 ** 3):.2f} GB",
        "disk_used": f"{disk_usage.used / (1024 ** 3):.2f} GB",
        "disk_percent": f"{disk_usage.percent} %"
    }
    return stats

if __name__ == "__main__":
    stats = get_system_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
