import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "mh"
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static/uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "adminpass123")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", "104857600"))

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Colecciones
categories_col = db["categories"]
products_col = db["products"]   # <-- Aquí agregamos la colección de productos

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --------------------------------
# INDEX: MUESTRA CATEGORÍAS
# --------------------------------
@app.route("/")
def index():
    try:
        categories = list(categories_col.find().sort("order", 1))
        print(categories)
        return render_template("index.html", categories=categories)
    except Exception as e:
        flash(f"Error al cargar categorías: {str(e)}", "danger")
        return render_template("index.html", categories=[])

# -------------------------
# Admin panel (login simple)
# -------------------------
def check_auth(req):
    auth_user = req.form.get("username")
    auth_pass = req.form.get("password")
    return auth_user == ADMIN_USER and auth_pass == ADMIN_PASS

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if not check_auth(request):
            flash("Credenciales incorrectas", "danger")
            return redirect(url_for("admin"))
        return redirect(url_for("admin_dashboard"))
    return render_template("admin.html", categories=list(categories_col.find().sort("order", 1)))

@app.route("/admin/dashboard")
def admin_dashboard():
    categories = list(categories_col.find().sort("order", 1))
    return render_template("admin.html", categories=categories)

# -------------------------
# CRUD Categorías
# -------------------------
@app.route("/admin/category/new", methods=["GET", "POST"])
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
def delete_category(id):
    categories_col.delete_one({"_id": ObjectId(id)})
    flash("Categoría eliminada", "success")
    return redirect(url_for("admin_dashboard"))

# -------------------------
# CRUD Productos
# -------------------------
@app.route("/admin/products/<category_id>")
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

    # Obtiene SOLO los productos de esa categoría
    products = list(products_col.find({"category_id": cat_id}))

    return render_template(
        "category_view.html",
        category=category,
        products=products
    )

# ---------------------------------
# MAIN
# ---------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
