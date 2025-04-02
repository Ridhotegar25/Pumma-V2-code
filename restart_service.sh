#!/bin/bash

# Daftar service yang ingin direstart
SERVICES=(
    main.service
    climate.service
    mppt.service
    capture.service
    del_image.service
    delete_file.service
    ardunano.service
    reboot_pi.service
    res_ssh.service
)

# Menghentikan semua service
echo "Menghentikan semua service..."
for SERVICE in "${SERVICES[@]}"; do
    echo "Restart $SERVICE..."
    sudo systemctl restart "$SERVICE"
done

echo "Semua service telah direstart!"
