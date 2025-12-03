import os
import qrcode
import io
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId
from functools import wraps

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "mh"
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static/uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
ADMIN_USER = os.getenv("ADMIN_USER", "Admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "123456")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", "104857600"))

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Colecciones
categories_col = db["categories"]
products_col = db["products"]
orders_col = db["orders"]  # Colección para pedidos

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Context processor para hacer categorías disponibles en todos los templates
@app.context_processor
def inject_categories():
    try:
        categories = list(categories_col.find().sort("order", 1))
        return dict(nav_categories=categories)
    except:
        return dict(nav_categories=[])

# --------------------------------
# INDEX: MUESTRA CATEGORÍAS
# --------------------------------
@app.route("/")
def index():
    try:
        categories = list(categories_col.find().sort("order", 1))
        mesa_num = session.get('mesa_num')
        return render_template("index.html", categories=categories, mesa_num=mesa_num)
    except Exception as e:
        flash(f"Error al cargar categorías: {str(e)}", "danger")
        mesa_num = session.get('mesa_num')
        return render_template("index.html", categories=[], mesa_num=mesa_num)

# -------------------------
# Admin panel (login simple)
# -------------------------
def check_auth(req):
    auth_user = req.form.get("username", "").strip()
    auth_pass = req.form.get("password", "").strip()
    return auth_user == ADMIN_USER and auth_pass == ADMIN_PASS

@app.route("/admin", methods=["GET", "POST"])
def admin():
    # Si ya está autenticado, redirigir al dashboard
    if session.get('admin_logged_in'):
        return redirect(url_for("admin_dashboard"))
    
    if request.method == "POST":
        if not check_auth(request):
            flash("Credenciales incorrectas. Por favor, intenta nuevamente.", "danger")
            return render_template("login.html")
        session['admin_logged_in'] = True
        flash("¡Bienvenido al panel de administración!", "success")
        return redirect(url_for("admin_dashboard"))
    
    return render_template("login.html")

def admin_required(view_func):
    """Decorator que protege rutas del panel admin."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Debes iniciar sesión como administrador", "warning")
            return redirect(url_for("admin"))
        return view_func(*args, **kwargs)
    return wrapper

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    search_query = request.args.get("q", "").strip()
    category_filter = {}
    if search_query:
        category_filter["name"] = {"$regex": search_query, "$options": "i"}
    total_categories = categories_col.count_documents({})
    categories = list(categories_col.find(category_filter).sort("order", 1))
    stats = {
        "categories": total_categories,
        "products": products_col.count_documents({}),
        "active_orders": orders_col.count_documents({"status": {"$in": ["pendiente", "en_preparacion"]}}),
        "pending_media": categories_col.count_documents({
            "$or": [{"image": {"$exists": False}}, {"image": ""}]
        })
    }
    latest_orders = list(orders_col.find().sort("created_at", -1).limit(3))
    latest_products = list(products_col.find().sort("_id", -1).limit(3))
    return render_template(
        "admin.html",
        categories=categories,
        stats=stats,
        latest_orders=latest_orders,
        latest_products=latest_products,
        search_query=search_query
    )

@app.route("/admin/logout")
@admin_required
def admin_logout():
    """Cerrar sesión de administrador"""
    session.pop('admin_logged_in', None)
    flash("Sesión cerrada exitosamente", "info")
    return redirect(url_for("admin"))

# -------------------------
# CRUD Categorías
# -------------------------
@app.route("/admin/category/new", methods=["GET", "POST"])
@admin_required
def new_category():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description", "")
        order = int(request.form.get("order", 0))

        image_path = ""
        file = request.files.get("image")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            if os.path.exists(save_path):
                base, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], f"{base}_{i}{ext}")):
                    i += 1
                filename = f"{base}_{i}{ext}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            file.save(save_path)
            image_path = f"/{save_path.replace(os.path.sep, '/')}"

        doc = {"name": name, "description": description, "order": order, "image": image_path}
        categories_col.insert_one(doc)

        flash("Categoría creada", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("category_form.html", action="Crear", category={})

@app.route("/admin/category/edit/<id>", methods=["GET", "POST"])
@admin_required
def edit_category(id):
    cat = categories_col.find_one({"_id": ObjectId(id)})

    if not cat:
        flash("Categoría no encontrada", "danger")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description", "")
        order = int(request.form.get("order", 0))

        update = {"name": name, "description": description, "order": order}

        file = request.files.get("image")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            if os.path.exists(save_path):
                base, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], f"{base}_{i}{ext}")):
                    i += 1
                filename = f"{base}_{i}{ext}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            file.save(save_path)
            update["image"] = f"/{save_path.replace(os.path.sep, '/')}"

        categories_col.update_one({"_id": ObjectId(id)}, {"$set": update})

        flash("Categoría actualizada", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("category_form.html", action="Editar", category=cat)

@app.route("/admin/category/delete/<id>", methods=["POST"])
@admin_required
def delete_category(id):
    categories_col.delete_one({"_id": ObjectId(id)})
    flash("Categoría eliminada", "success")
    return redirect(url_for("admin_dashboard"))

# -------------------------
# CRUD Productos
# -------------------------
@app.route("/admin/products/<category_id>")
@admin_required
def manage_products(category_id):
    try:
        cat_id = ObjectId(category_id)
    except:
        flash("ID de categoría inválido", "danger")
        return redirect(url_for("admin_dashboard"))
    
    category = categories_col.find_one({"_id": cat_id})
    if not category:
        flash("Categoría no encontrada", "danger")
        return redirect(url_for("admin_dashboard"))
    
    products = list(products_col.find({"category_id": cat_id}).sort("name", 1))
    return render_template("manage_products.html", category=category, products=products)

@app.route("/admin/product/new/<category_id>", methods=["GET", "POST"])
@admin_required
def new_product(category_id):
    try:
        cat_id = ObjectId(category_id)
    except:
        flash("ID de categoría inválido", "danger")
        return redirect(url_for("admin_dashboard"))
    
    category = categories_col.find_one({"_id": cat_id})
    if not category:
        flash("Categoría no encontrada", "danger")
        return redirect(url_for("admin_dashboard"))
    
    if request.method == "POST":
        name = request.form.get("name", "")
        ingredients = request.form.get("ingredients", "")
        
        # Campos específicos por categoría
        doc = {
            "category_id": cat_id,
            "name": name
        }
        
        # PIZZAS: Precios por tamaño
        if category["name"].upper() == "PIZZAS":
            doc["price_individual"] = request.form.get("price_individual", "")
            doc["price_chica"] = request.form.get("price_chica", "")
            doc["price_mediana"] = request.form.get("price_mediana", "")
            doc["price_grande"] = request.form.get("price_grande", "")
            doc["price_h4"] = request.form.get("price_h4", "")
            doc["ingredients"] = ingredients
        
        # BEBIDAS: ML
        elif category["name"].upper() == "BEBIDAS":
            doc["price"] = request.form.get("price", "")
            doc["ml"] = request.form.get("ml", "")
        
        # COMPLEMENTOS: Gramos (y ingredientes solo para algunos)
        elif category["name"].upper() == "COMPLEMENTOS":
            doc["price"] = request.form.get("price", "")
            doc["grams"] = request.form.get("grams", "")
            # Ingredientes solo para productos específicos
            productos_con_ingredientes = [
                "spaghetti", "al horno", "spaghetti a la boloñesa", 
                "papa al horno", "alitas BBQ", "Mango Habanero"
            ]
            if any(prod in name.lower() for prod in productos_con_ingredientes):
                doc["ingredients"] = ingredients
            else:
                doc["ingredients"] = ""
        
        # Otras categorías: precio genérico
        else:
            doc["price"] = request.form.get("price", "")
        
        # Manejo de imagen
        image_path = ""
        file = request.files.get("image")
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            
            if os.path.exists(save_path):
                base, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], f"{base}_{i}{ext}")):
                    i += 1
                filename = f"{base}_{i}{ext}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            
            file.save(save_path)
            image_path = f"/{save_path.replace(os.path.sep, '/')}"
        
        doc["image"] = image_path
        
        products_col.insert_one(doc)
        flash("Producto creado", "success")
        return redirect(url_for("manage_products", category_id=category_id))
    
    return render_template("product_form.html", action="Crear", product={}, category=category)

@app.route("/admin/product/edit/<id>", methods=["GET", "POST"])
@admin_required
def edit_product(id):
    try:
        product_id = ObjectId(id)
    except:
        flash("ID de producto inválido", "danger")
        return redirect(url_for("admin_dashboard"))
    
    product = products_col.find_one({"_id": product_id})
    if not product:
        flash("Producto no encontrado", "danger")
        return redirect(url_for("admin_dashboard"))
    
    category = categories_col.find_one({"_id": product["category_id"]})
    if not category:
        flash("Categoría no encontrada", "danger")
        return redirect(url_for("admin_dashboard"))
    
    if request.method == "POST":
        name = request.form.get("name", "")
        ingredients = request.form.get("ingredients", "")
        
        update = {
            "name": name
        }
        
        # PIZZAS: Precios por tamaño
        if category["name"].upper() == "PIZZAS":
            update["price_individual"] = request.form.get("price_individual", "")
            update["price_chica"] = request.form.get("price_chica", "")
            update["price_mediana"] = request.form.get("price_mediana", "")
            update["price_grande"] = request.form.get("price_grande", "")
            update["price_h4"] = request.form.get("price_h4", "")
            update["ingredients"] = ingredients
        
        # BEBIDAS: ML
        elif category["name"].upper() == "BEBIDAS":
            update["price"] = request.form.get("price", "")
            update["ml"] = request.form.get("ml", "")
        
        # COMPLEMENTOS: Gramos (y ingredientes solo para algunos)
        elif category["name"].upper() == "COMPLEMENTOS":
            update["price"] = request.form.get("price", "")
            update["grams"] = request.form.get("grams", "")
            productos_con_ingredientes = [
                "spaghetti", "al horno", "spaghetti a la boloñesa", 
                "papa al horno", "alitas BBQ", "Mango Habanero"
            ]
            if any(prod in name.lower() for prod in productos_con_ingredientes):
                update["ingredients"] = ingredients
            else:
                update["ingredients"] = ""
        
        # Otras categorías: precio genérico
        else:
            update["price"] = request.form.get("price", "")
        
        # Manejo de imagen
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            
            if os.path.exists(save_path):
                base, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], f"{base}_{i}{ext}")):
                    i += 1
                filename = f"{base}_{i}{ext}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            
            file.save(save_path)
            update["image"] = f"/{save_path.replace(os.path.sep, '/')}"
        
        # Para pizzas, eliminar campo price si existe
        if category["name"].upper() == "PIZZAS":
            products_col.update_one({"_id": product_id}, {"$set": update, "$unset": {"price": ""}})
        else:
            products_col.update_one({"_id": product_id}, {"$set": update})
        
        flash("Producto actualizado", "success")
        return redirect(url_for("manage_products", category_id=product["category_id"]))
    
    return render_template("product_form.html", action="Editar", product=product, category=category)

@app.route("/admin/product/delete/<id>", methods=["POST"])
@admin_required
def delete_product(id):
    try:
        product_id = ObjectId(id)
    except:
        flash("ID de producto inválido", "danger")
        return redirect(url_for("admin_dashboard"))
    
    product = products_col.find_one({"_id": product_id})
    if product:
        category_id = product["category_id"]
        products_col.delete_one({"_id": product_id})
        flash("Producto eliminado", "success")
        return redirect(url_for("manage_products", category_id=category_id))
    
    flash("Producto no encontrado", "danger")
    return redirect(url_for("admin_dashboard"))

# ---------------------------------
# BÚSQUEDA DE PRODUCTOS
# ---------------------------------
@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    results = []
    
    if query:
        # Búsqueda en productos por nombre e ingredientes (case-insensitive)
        search_regex = {"$regex": query, "$options": "i"}
        # Buscar por nombre O por ingredientes
        products = list(products_col.find({
            "$or": [
                {"name": search_regex},
                {"ingredients": search_regex}
            ]
        }))
        
        # Obtener información de categoría para cada producto
        for product in products:
            category = categories_col.find_one({"_id": product.get("category_id")})
            if category:
                product["category_name"] = category.get("name", "")
                product["category_id"] = str(category.get("_id", ""))
            results.append(product)
    
    return render_template("search_results.html", query=query, results=results)

# ---------------------------------
# ARCHIVOS ESTÁTICOS
# ---------------------------------
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------------------------
# MOSTRAR PRODUCTOS POR CATEGORÍA
# ---------------------------------
@app.route("/category/<id>")
def show_category(id):
    try:
        cat_id = ObjectId(id)
    except:
        return "ID inválido", 400

    category = categories_col.find_one({"_id": cat_id})

    if not category:
        return "Categoría no encontrada", 404

    # Obtiene categorías para construir el desplegable de navegación
    categories = list(categories_col.find().sort("order", 1))
    other_categories = [c for c in categories if c["_id"] != cat_id]

    # Paginación: 6 productos por página (2 filas x 3 columnas en móvil)
    page = request.args.get('page', 1, type=int)
    per_page = 6
    skip = (page - 1) * per_page

    # Obtener total de productos
    total_products = products_col.count_documents({"category_id": cat_id})
    
    # Obtener productos paginados
    products = list(products_col.find({"category_id": cat_id}).skip(skip).limit(per_page))
    
    # Calcular total de páginas
    total_pages = (total_products + per_page - 1) // per_page if total_products > 0 else 1

    # Obtener número de mesa de la sesión
    mesa_num = session.get('mesa_num', None)

    return render_template(
        "category_view.html",
        category=category,
        products=products,
        other_categories=other_categories,
        page=page,
        total_pages=total_pages,
        total_products=total_products,
        mesa_num=mesa_num
    )

# ---------------------------------
# SISTEMA DE MESAS Y QR
# ---------------------------------
@app.route("/mesa/<int:mesa_num>")
def mesa_view(mesa_num):
    """Vista principal cuando se escanea el QR de una mesa"""
    if mesa_num < 1 or mesa_num > 13:
        flash("Número de mesa inválido. Debe ser entre 1 y 13.", "danger")
        return redirect(url_for("index"))
    
    # Guardar número de mesa en sesión
    session['mesa_num'] = mesa_num
    session.permanent = True
    
    # Cargar categorías
    try:
        categories = list(categories_col.find().sort("order", 1))
        return render_template("index.html", categories=categories, mesa_num=mesa_num)
    except Exception as e:
        flash(f"Error al cargar categorías: {str(e)}", "danger")
        return render_template("index.html", categories=[], mesa_num=mesa_num)

@app.route("/generate_qr/<int:mesa_num>")
def generate_qr(mesa_num):
    """Genera un código QR para una mesa específica"""
    if mesa_num < 1 or mesa_num > 13:
        return "Número de mesa inválido", 400
    
    # URL que apunta a la mesa
    base_url = request.host_url.rstrip('/')
    mesa_url = f"{base_url}/mesa/{mesa_num}"
    
    # Generar QR
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(mesa_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a base64 para mostrar en HTML
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    
    return render_template("qr_display.html", mesa_num=mesa_num, qr_image=img_str, mesa_url=mesa_url)

@app.route("/admin/qr-codes")
@admin_required
def admin_qr_codes():
    """Panel para generar y ver todos los códigos QR"""
    return render_template("admin_qr_codes.html")

# ---------------------------------
# SISTEMA DE CARRITO
# ---------------------------------
@app.route("/cart")
def view_cart():
    """Ver el carrito de la mesa actual"""
    mesa_num = session.get('mesa_num')
    if not mesa_num:
        flash("No hay mesa asignada. Escanea el QR de tu mesa.", "warning")
        return redirect(url_for("index"))
    
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    
    for cart_key, item in cart.items():
        try:
            # Extraer product_id del cart_key (puede ser "product_id" o "product_id_size")
            product_id = item.get('product_id')
            if not product_id:
                # Si no está en item, intentar extraer del cart_key
                product_id = cart_key.split('_')[0] if '_' in cart_key else cart_key
            
            product = products_col.find_one({"_id": ObjectId(product_id)})
            if product:
                category = categories_col.find_one({"_id": product.get("category_id")})
                # Convertir ObjectId a string para evitar problemas de serialización
                # NO guardar el objeto product completo en item (contiene ObjectId)
                item['product_id'] = str(product_id)  # Asegurar que sea string
                item['cart_key'] = cart_key  # Agregar cart_key al item
                item['category_name'] = category.get("name", "") if category else ""
                # Asegurar que 'name' esté presente (ya debería estar del add_to_cart)
                if 'name' not in item:
                    item['name'] = product.get('name', '')
                cart_items.append(item)
                total += float(item.get('subtotal', 0))
        except Exception as e:
            print(f"Error procesando item del carrito: {e}")
            continue
    
    return render_template("cart.html", cart_items=cart_items, total=total, mesa_num=mesa_num)

@app.route("/cart/add", methods=["POST"])
def add_to_cart():
    """Agregar producto al carrito"""
    mesa_num = session.get('mesa_num')
    if not mesa_num:
        return jsonify({"success": False, "message": "No hay mesa asignada"}), 400
    
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity", 1))
    size = request.form.get("size", "")  # Para pizzas: individual, chica, mediana, etc.
    
    try:
        product = products_col.find_one({"_id": ObjectId(product_id)})
        if not product:
            return jsonify({"success": False, "message": "Producto no encontrado"}), 404
        
        category = categories_col.find_one({"_id": product.get("category_id")})
        category_name = category.get("name", "").upper() if category else ""
        
        # Determinar precio según categoría y tamaño
        if category_name == "PIZZAS" and size:
            price_field = f"price_{size.lower()}"
            price = float(product.get(price_field, 0))
            if not price:
                return jsonify({"success": False, "message": f"Tamaño {size} no disponible"}), 400
        else:
            price = float(product.get("price", 0))
            if not price:
                return jsonify({"success": False, "message": "Precio no disponible"}), 400
        
        # Inicializar carrito si no existe
        if 'cart' not in session:
            session['cart'] = {}
        
        cart = session['cart']
        cart_key = f"{product_id}_{size}" if size else product_id
        
        # Agregar o actualizar item en carrito
        if cart_key in cart:
            cart[cart_key]['quantity'] += quantity
        else:
            cart[cart_key] = {
                'product_id': product_id,
                'name': product.get('name'),
                'quantity': quantity,
                'price': price,
                'size': size,
                'subtotal': price * quantity
            }
        
        # Recalcular subtotal
        cart[cart_key]['subtotal'] = cart[cart_key]['quantity'] * price
        
        session['cart'] = cart
        session.modified = True
        
        return jsonify({
            "success": True,
            "message": "Producto agregado al carrito",
            "cart_count": sum(item['quantity'] for item in cart.values())
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/cart/update", methods=["POST"])
def update_cart():
    """Actualizar cantidad de un item en el carrito"""
    cart_key = request.form.get("cart_key")
    quantity = int(request.form.get("quantity", 1))
    
    if quantity <= 0:
        return redirect(url_for("remove_from_cart", cart_key=cart_key))
    
    cart = session.get('cart', {})
    if cart_key in cart:
        cart[cart_key]['quantity'] = quantity
        cart[cart_key]['subtotal'] = cart[cart_key]['quantity'] * cart[cart_key]['price']
        session['cart'] = cart
        session.modified = True
    
    return redirect(url_for("view_cart"))

@app.route("/cart/remove/<cart_key>")
def remove_from_cart(cart_key):
    """Eliminar item del carrito"""
    cart = session.get('cart', {})
    if cart_key in cart:
        del cart[cart_key]
        session['cart'] = cart
        session.modified = True
    
    return redirect(url_for("view_cart"))

@app.route("/cart/clear")
def clear_cart():
    """Vaciar carrito"""
    session['cart'] = {}
    session.modified = True
    return redirect(url_for("view_cart"))

# ---------------------------------
# SISTEMA DE PEDIDOS
# ---------------------------------
@app.route("/order/checkout")
def checkout():
    """Pantalla de confirmación del pedido"""
    mesa_num = session.get('mesa_num')
    if not mesa_num:
        flash("No hay mesa asignada", "warning")
        return redirect(url_for("index"))
    
    cart = session.get('cart', {})
    if not cart:
        flash("El carrito está vacío", "warning")
        return redirect(url_for("view_cart"))
    
    cart_items = []
    total = 0
    
    for cart_key, item in cart.items():
        try:
            product = products_col.find_one({"_id": ObjectId(item['product_id'])})
            if product:
                category = categories_col.find_one({"_id": product.get("category_id")})
                # NO guardar el objeto product completo (contiene ObjectId)
                # Solo agregar los datos necesarios como strings
                item['product_name'] = product.get('name', '')
                item['product_image'] = product.get('image', '')
                item['category_name'] = category.get("name", "") if category else ""
                cart_items.append(item)
                total += float(item.get('subtotal', 0))
        except Exception as e:
            print(f"Error en checkout: {e}")
            continue
    
    return render_template("checkout.html", cart_items=cart_items, total=total, mesa_num=mesa_num)

@app.route("/order/submit", methods=["POST"])
def submit_order():
    """Enviar pedido a cocina/administración"""
    mesa_num = session.get('mesa_num')
    if not mesa_num:
        return jsonify({"success": False, "message": "No hay mesa asignada"}), 400
    
    cart = session.get('cart', {})
    if not cart:
        return jsonify({"success": False, "message": "El carrito está vacío"}), 400
    
    # Preparar items del pedido
    order_items = []
    total = 0
    
    for cart_key, item in cart.items():
        try:
            product = products_col.find_one({"_id": ObjectId(item['product_id'])})
            if product:
                category = categories_col.find_one({"_id": product.get("category_id")})
                order_item = {
                    'product_id': str(item['product_id']),
                    'product_name': item['name'],
                    'category_name': category.get("name", "") if category else "",
                    'quantity': item['quantity'],
                    'price': item['price'],
                    'size': item.get('size', ''),
                    'subtotal': item['subtotal']
                }
                order_items.append(order_item)
                total += float(item['subtotal'])
        except:
            continue
    
    # Crear pedido en la base de datos
    order = {
        'mesa_num': mesa_num,
        'items': order_items,
        'total': total,
        'status': 'pendiente',  # pendiente, en_preparacion, listo, completado
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    orders_col.insert_one(order)
    
    # Limpiar carrito
    session['cart'] = {}
    session.modified = True
    
    flash("¡Pedido enviado exitosamente! Tu pedido está siendo preparado.", "success")
    return jsonify({"success": True, "message": "Pedido enviado exitosamente"})

@app.route("/order/confirmation")
def order_confirmation():
    """Pantalla de confirmación después de enviar el pedido"""
    mesa_num = session.get('mesa_num')
    return render_template("order_confirmation.html", mesa_num=mesa_num)

# ---------------------------------
# ADMINISTRACIÓN DE PEDIDOS
# ---------------------------------
@app.route("/admin/orders")
@admin_required
def admin_orders():
    """Panel de administración para ver pedidos activos"""
    # Obtener pedidos pendientes y en preparación
    active_orders = list(orders_col.find({
        "status": {"$in": ["pendiente", "en_preparacion"]}
    }).sort("created_at", -1))
    
    # Obtener pedidos completados recientes (últimas 24 horas)
    from datetime import timedelta
    yesterday = datetime.now() - timedelta(days=1)
    completed_orders = list(orders_col.find({
        "status": "completado",
        "created_at": {"$gte": yesterday}
    }).sort("created_at", -1))
    
    return render_template("admin_orders.html", 
                         active_orders=active_orders, 
                         completed_orders=completed_orders)

@app.route("/admin/order/<order_id>/update-status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    """Actualizar estado de un pedido"""
    new_status = request.form.get("status")
    valid_statuses = ["pendiente", "en_preparacion", "listo", "completado"]
    
    if new_status not in valid_statuses:
        flash("Estado inválido", "danger")
        return redirect(url_for("admin_orders"))
    
    orders_col.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": new_status, "updated_at": datetime.now()}}
    )
    
    flash(f"Estado del pedido actualizado a: {new_status}", "success")
    return redirect(url_for("admin_orders"))

@app.route("/admin/order/<order_id>")
@admin_required
def view_order(order_id):
    """Ver detalles de un pedido específico"""
    try:
        order = orders_col.find_one({"_id": ObjectId(order_id)})
        if not order:
            flash("Pedido no encontrado", "danger")
            return redirect(url_for("admin_orders"))
        
        return render_template("view_order.html", order=order)
    except:
        flash("ID de pedido inválido", "danger")
        return redirect(url_for("admin_orders"))

@app.route("/admin/cash")
@admin_required
def admin_cash():
    """Vista de corte de caja por día."""
    from datetime import timedelta
    # Fecha seleccionada (formato YYYY-MM-DD)
    fecha_str = request.args.get("fecha")
    today = datetime.now().date()
    try:
        selected_date = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else today
    except ValueError:
        selected_date = today

    start_dt = datetime.combine(selected_date, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    status_filter = request.args.get("status", "completado")
    query = {
        "created_at": {"$gte": start_dt, "$lt": end_dt}
    }
    if status_filter == "completado":
        query["status"] = "completado"

    orders = list(orders_col.find(query).sort("created_at", 1))

    total_ventas = sum(float(o.get("total", 0) or 0) for o in orders)
    total_pedidos = len(orders)
    ticket_promedio = total_ventas / total_pedidos if total_pedidos > 0 else 0

    return render_template(
        "admin_cash.html",
        orders=orders,
        total_ventas=total_ventas,
        total_pedidos=total_pedidos,
        ticket_promedio=ticket_promedio,
        selected_date=selected_date.strftime("%Y-%m-%d"),
        status_filter=status_filter,
    )

# ---------------------------------
# MAIN
# ---------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
