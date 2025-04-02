#!/bin/bash

# Daftar service yang ingin di-enable dan dijalankan
SERVICES=(
    main.service
    climate.service
    mppt.service
    capture.service
    del_image.service
    del_image.timer
    delete_file.service
    ardunano.service
    reboot_pi.service
    res_ssh.service
)

# Enable dan start semua service
echo "Mengaktifkan dan menjalankan semua service..."
for SERVICE in "${SERVICES[@]}"; do
#    echo "Enabling $SERVICE..."
#    sudo systemctl enable "$SERVICE"

    echo "Starting $SERVICE..."
    sudo systemctl start "$SERVICE"
done

echo "Semua service telah di-enable dan dijalankan!"
