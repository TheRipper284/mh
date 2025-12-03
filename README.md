# Sistema de Menú Digital para Restaurante

Sistema web desarrollado con Flask, Python, MongoDB y Bootstrap que funciona mediante códigos QR asignados a cada mesa.

## Características

✅ **Sistema de Códigos QR**: Genera códigos QR para 13 mesas (1-13)  
✅ **Menú Digital**: Categorías y productos con imágenes, precios y descripciones  
✅ **Carrito por Mesa**: Cada mesa tiene su propio carrito de compras  
✅ **Gestión de Pedidos**: Envío de pedidos a cocina/administración  
✅ **Panel de Administración**: 
   - Crear, editar y eliminar categorías
   - Crear, editar y eliminar productos
   - Subir imágenes
   - Monitorear pedidos activos por mesa
   - Generar códigos QR

## Requisitos

- Python 3.8+
- MongoDB (local o remoto)
- pip

## Instalación

1. Clonar o descargar el proyecto

2. Crear un entorno virtual (recomendado):
```bash
python -m venv venv
```

3. Activar el entorno virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. Instalar dependencias:
```bash
pip install -r requirements.txt
```

5. Configurar variables de entorno (opcional):
   Crear un archivo `.env` en la raíz del proyecto:
```
MONGO_URI=mongodb://localhost:27017/
DB_NAME=mh
UPLOAD_FOLDER=static/uploads
ADMIN_USER=Admin
ADMIN_PASS=123456
```

6. Inicializar la base de datos (opcional):
```bash
python create_db.py
```

## Uso

### Iniciar el servidor

```bash
python app.py
```

El servidor estará disponible en `http://localhost:5000`

### Generar Códigos QR

1. Acceder al panel de administración: `http://localhost:5000/admin`
   - Usuario: `Admin` (por defecto)
   - Contraseña: `123456` (por defecto)

2. Ir a "Códigos QR" en el panel de administración

3. Generar el QR para cada mesa (1-13)

4. Imprimir cada código QR y colocarlo en la mesa correspondiente

### Flujo de Uso

1. **Cliente escanea QR**: Al escanear el QR de su mesa, se abre el menú digital
2. **Navegar categorías**: El cliente puede ver todas las categorías disponibles
3. **Ver productos**: Al hacer clic en una categoría, se muestran los productos
4. **Agregar al carrito**: Los clientes pueden agregar productos al carrito
5. **Revisar carrito**: Ver y modificar el carrito desde el menú
6. **Finalizar pedido**: Enviar el pedido a cocina
7. **Monitoreo**: Los administradores pueden ver y gestionar pedidos desde el panel

## Estructura del Proyecto

```
mh/
├── app.py                 # Aplicación principal Flask
├── create_db.py           # Script para inicializar BD
├── generate_all_qr.py     # Script para generar todos los QR
├── requirements.txt       # Dependencias Python
├── templates/             # Plantillas HTML
│   ├── layout.html
│   ├── index.html
│   ├── category_view.html
│   ├── cart.html
│   ├── checkout.html
│   ├── admin.html
│   ├── admin_orders.html
│   ├── admin_qr_codes.html
│   └── ...
├── static/               # Archivos estáticos
│   ├── styles/
│   ├── js/
│   └── uploads/
└── instance/             # Archivos de instancia
```

## Características Especiales

### Productos por Categoría

- **Pizzas**: Precios por tamaño (Individual, Chica, Mediana, Grande, H4)
- **Bebidas**: Precio y contenido en ml
- **Complementos**: Precio y peso en gramos
- **Otras categorías**: Precio genérico

### Carrito de Compras

- Carrito único por mesa (identificado por el QR)
- Agregar productos con diferentes tamaños (para pizzas)
- Modificar cantidades
- Eliminar productos
- Vaciar carrito completo

### Gestión de Pedidos

- Estados: Pendiente → En Preparación → Listo → Completado
- Vista detallada de cada pedido
- Filtrado por estado
- Historial de pedidos completados

## Seguridad

- Autenticación simple para panel de administración
- Sesiones para mantener el estado del carrito por mesa
- Validación de datos en formularios

## Notas

- Ajustar `base_url` en `generate_all_qr.py` según tu configuración de producción
- Las imágenes se guardan en `static/uploads/`
- Los códigos QR generados se guardan en `static/qr_codes/` (si usas el script)

## Desarrollo

Para desarrollo local:
- MongoDB debe estar corriendo en `localhost:27017`
- El servidor Flask corre en modo debug
- Los cambios se reflejan automáticamente

## Licencia

Este proyecto es de uso libre para fines educativos y comerciales.

