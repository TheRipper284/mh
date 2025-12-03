"""
Script para generar todos los códigos QR de las 13 mesas
Ejecutar: python generate_all_qr.py
"""
import qrcode
import os
from flask import Flask

app = Flask(__name__)
app.config['SERVER_NAME'] = 'localhost:5000'  # Ajustar según tu configuración

# Crear directorio para QR codes si no existe
qr_dir = "static/qr_codes"
os.makedirs(qr_dir, exist_ok=True)

# URL base (ajustar según tu configuración)
base_url = "http://localhost:5000"  # Cambiar por tu URL de producción

print("Generando códigos QR para las 13 mesas...")

for mesa_num in range(1, 14):
    mesa_url = f"{base_url}/mesa/{mesa_num}"
    
    # Generar QR
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(mesa_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Guardar imagen
    filename = f"{qr_dir}/mesa_{mesa_num}.png"
    img.save(filename)
    
    print(f"✓ QR generado para Mesa {mesa_num}: {filename}")
    print(f"  URL: {mesa_url}")

print("\n¡Todos los códigos QR han sido generados!")
print(f"Los archivos están en: {qr_dir}/")

