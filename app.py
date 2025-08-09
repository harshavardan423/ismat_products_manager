from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    product_name = db.Column(db.String(200))
    short_description = db.Column(db.Text)
    long_description = db.Column(db.Text)
    mrp = db.Column(db.Float)
    offer_price = db.Column(db.Float)
    sku = db.Column(db.String(50))
    in_stock = db.Column(db.Boolean, default=True)
    stock_number = db.Column(db.Integer)
    download_pdfs = db.Column(db.Text)
    product_image_urls = db.Column(db.Text)
    youtube_links = db.Column(db.Text)
    technical_information = db.Column(db.Text)
    manufacturer = db.Column(db.String(200))
    special_note = db.Column(db.Text)
    whatsapp_number = db.Column(db.String(20))
    is_rubber = db.Column(db.Boolean, default=False)
    rubber_density = db.Column(db.Float, nullable=True)
    rubber_height = db.Column(db.Float, nullable=True)
    rubber_length = db.Column(db.Float, nullable=True)
    rubber_thickness = db.Column(db.Float, nullable=True)
    rubber_description = db.Column(db.Text, nullable=True)
    variants = db.Column(db.Text)  # Store variants as JSON string

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "product_name": self.product_name,
            "short_description": self.short_description,
            "long_description": self.long_description,
            "mrp": self.mrp,
            "offer_price": self.offer_price,
            "sku": self.sku,
            "in_stock": self.in_stock,
            "stock_number": self.stock_number,
            "download_pdfs": self.download_pdfs.split(",") if self.download_pdfs else [],
            "product_image_urls": self.product_image_urls.split(",") if self.product_image_urls else [],
            "youtube_links": self.youtube_links.split(",") if self.youtube_links else [],
            "technical_information": self.technical_information,
            "manufacturer": self.manufacturer,
            "special_note": self.special_note,
            "whatsapp_number": self.whatsapp_number,
            "is_rubber": self.is_rubber,
            "rubber_density": self.rubber_density,
            "rubber_height": self.rubber_height,
            "rubber_length": self.rubber_length,
            "rubber_thickness": self.rubber_thickness,
            "rubber_description": self.rubber_description,
            "variants": json.loads(self.variants) if self.variants else []
        }

# Create DB
with app.app_context():
    db.create_all()

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Login required decorator
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error="Username already exists")
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Serve static files explicitly (for debugging)
@app.route('/static/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# UI Routes
@app.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    query = request.args.get('q', '').lower()
    category = request.args.get('category', '')
    in_stock = request.args.get('in_stock', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    # Build query with filters
    product_query = Product.query
    if query:
        product_query = product_query.filter(
            Product.product_name.ilike(f'%{query}%') |
            Product.category.ilike(f'%{query}%') |
            Product.short_description.ilike(f'%{query}%') |
            Product.long_description.ilike(f'%{query}%') |
            Product.rubber_description.ilike(f'%{query}%')
        )
    if category:
        product_query = product_query.filter(Product.category == category)
    if in_stock:
        product_query = product_query.filter(Product.in_stock == (in_stock == 'true'))
    if min_price is not None:
        product_query = product_query.filter(Product.offer_price >= min_price)
    if max_price is not None:
        product_query = product_query.filter(Product.offer_price <= max_price)

    products_pagination = product_query.paginate(page=page, per_page=per_page, error_out=False)
    categories = [p.category for p in Product.query.distinct(Product.category)]
    return render_template('index.html', products=products_pagination.items, pagination=products_pagination, categories=categories)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product_ui():
    if request.method == 'POST':
        data = request.form
        images = request.files.getlist('images')
        pdfs = request.files.getlist('pdfs')
        image_order = data.get('image_order', '').split(',') if data.get('image_order') else []

        app.logger.debug(f"Received form data: {data}")
        app.logger.debug(f"Received images: {[f.filename for f in images]}")
        app.logger.debug(f"Received image order: {image_order}")

        image_urls = []
        for image in images:
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    image.save(image_path)
                    image_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved image: {image_path}")
                except Exception as e:
                    app.logger.error(f"Error saving image {filename}: {str(e)}")

        # Reorder images based on image_order
        ordered_urls = []
        for filename in image_order:
            for url in image_urls[:]:
                if filename in url:
                    ordered_urls.append(url)
                    image_urls.remove(url)
                    break
        image_urls = ordered_urls + image_urls
        app.logger.debug(f"Final image URLs: {image_urls}")

        pdf_urls = []
        for pdf in pdfs:
            if pdf and allowed_file(pdf.filename):
                filename = secure_filename(pdf.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    pdf.save(pdf_path)
                    pdf_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved PDF: {pdf_path}")
                except Exception as e:
                    app.logger.error(f"Error saving PDF {filename}: {str(e)}")

        # Handle multiple variants
        variants = []
        variant_names = data.getlist('variant_name[]')
        variant_prices = data.getlist('variant_price[]')
        variant_skus = data.getlist('variant_sku[]')
        for name, price, sku in zip(variant_names, variant_prices, variant_skus):
            if name and price:
                try:
                    variants.append({"name": name, "price": float(price), "sku": sku})
                except ValueError:
                    app.logger.error(f"Invalid variant price: {price}")
        app.logger.debug(f"Variants: {variants}")

        product = Product(
            category=data.get('category'),
            product_name=data.get('product_name'),
            short_description=data.get('short_description'),
            long_description=data.get('long_description'),
            mrp=float(data.get('mrp')) if data.get('mrp') else 0.0,
            offer_price=float(data.get('offer_price')) if data.get('offer_price') else 0.0,
            sku=data.get('sku'),
            in_stock=data.get('in_stock') == 'on',
            stock_number=int(data.get('stock_number')) if data.get('stock_number') else 0,
            download_pdfs=",".join(pdf_urls),
            product_image_urls=",".join(image_urls),
            youtube_links=data.get('youtube_links'),
            technical_information=data.get('technical_information'),
            manufacturer=data.get('manufacturer'),
            special_note=data.get('special_note'),
            whatsapp_number=data.get('whatsapp_number'),
            is_rubber=data.get('is_rubber') == 'on',
            rubber_density=float(data.get('rubber_density')) if data.get('rubber_density') else None,
            rubber_height=float(data.get('rubber_height')) if data.get('rubber_height') else None,
            rubber_length=float(data.get('rubber_length')) if data.get('rubber_length') else None,
            rubber_thickness=float(data.get('rubber_thickness')) if data.get('rubber_thickness') else None,
            rubber_description=data.get('rubber_description'),
            variants=json.dumps(variants) if variants else None
        )
        db.session.add(product)
        db.session.commit()
        app.logger.debug(f"Added product: {product.product_name}, Image URLs: {product.product_image_urls}")
        return redirect(url_for('index'))
    
    return render_template('add_product.html')

@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product_ui(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        data = request.form
        images = request.files.getlist('images')
        pdfs = request.files.getlist('pdfs')
        image_order = data.get('image_order', '').split(',') if data.get('image_order') else []

        app.logger.debug(f"Received form data: {data}")
        app.logger.debug(f"Received images: {[f.filename for f in images]}")
        app.logger.debug(f"Received image order: {image_order}")

        image_urls = product.product_image_urls.split(",") if product.product_image_urls else []
        for image in images:
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    image.save(image_path)
                    image_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved image: {image_path}")
                except Exception as e:
                    app.logger.error(f"Error saving image {filename}: {str(e)}")

        # Reorder images based on image_order
        ordered_urls = []
        for filename in image_order:
            for url in image_urls[:]:
                if filename in url:
                    ordered_urls.append(url)
                    image_urls.remove(url)
                    break
        image_urls = ordered_urls + image_urls
        app.logger.debug(f"Final image URLs: {image_urls}")

        pdf_urls = product.download_pdfs.split(",") if product.download_pdfs else []
        for pdf in pdfs:
            if pdf and allowed_file(pdf.filename):
                filename = secure_filename(pdf.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    pdf.save(pdf_path)
                    pdf_urls.append(f"{app.config['UPLOAD_FOLDER']}/{filename}")
                    app.logger.debug(f"Saved PDF: {pdf_path}")
                except Exception as e:
                    app.logger.error(f"Error saving PDF {filename}: {str(e)}")

        # Handle multiple variants
        variants = []
        variant_names = data.getlist('variant_name[]')
        variant_prices = data.getlist('variant_price[]')
        variant_skus = data.getlist('variant_sku[]')
        for name, price, sku in zip(variant_names, variant_prices, variant_skus):
            if name and price:
                try:
                    variants.append({"name": name, "price": float(price), "sku": sku})
                except ValueError:
                    app.logger.error(f"Invalid variant price: {price}")
        app.logger.debug(f"Variants: {variants}")

        product.category = data.get('category', product.category)
        product.product_name = data.get('product_name', product.product_name)
        product.short_description = data.get('short_description', product.short_description)
        product.long_description = data.get('long_description', product.long_description)
        product.mrp = float(data.get('mrp', product.mrp)) if data.get('mrp') else product.mrp
        product.offer_price = float(data.get('offer_price', product.offer_price)) if data.get('offer_price') else product.offer_price
        product.sku = data.get('sku', product.sku)
        product.in_stock = data.get('in_stock') == 'on'
        product.stock_number = int(data.get('stock_number', product.stock_number)) if data.get('stock_number') else product.stock_number
        product.download_pdfs = ",".join(pdf_urls)
        product.product_image_urls = ",".join(image_urls)
        product.youtube_links = data.get('youtube_links', product.youtube_links)
        product.technical_information = data.get('technical_information', product.technical_information)
        product.manufacturer = data.get('manufacturer', product.manufacturer)
        product.special_note = data.get('special_note', product.special_note)
        product.whatsapp_number = data.get('whatsapp_number', product.whatsapp_number)
        product.is_rubber = data.get('is_rubber') == 'on'
        product.rubber_density = float(data.get('rubber_density')) if data.get('rubber_density') else None
        product.rubber_height = float(data.get('rubber_height')) if data.get('rubber_height') else None
        product.rubber_length = float(data.get('rubber_length')) if data.get('rubber_length') else None
        product.rubber_thickness = float(data.get('rubber_thickness')) if data.get('rubber_thickness') else None
        product.rubber_description = data.get('rubber_description', product.rubber_description)
        product.variants = json.dumps(variants) if variants else product.variants
        db.session.commit()
        app.logger.debug(f"Updated product: {product.product_name}, Image URLs: {product.product_image_urls}")
        return redirect(url_for('index'))
    
    return render_template('edit_product.html', product=product)

@app.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product_ui(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    app.logger.debug(f"Deleted product ID: {product_id}")
    return redirect(url_for('index'))

@app.route('/delete-selected', methods=['POST'])
@login_required
def delete_selected():
    product_ids = request.form.getlist('product_ids[]')
    for product_id in product_ids:
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
    db.session.commit()
    app.logger.debug(f"Deleted products: {product_ids}")
    return redirect(url_for('index'))

# Existing API Routes
@app.route('/add-product', methods=['POST'])
def add_product():
    data = request.get_json()
    variants = data.get('variants', [])
    product = Product(
        category=data.get('category'),
        product_name=data.get('product_name'),
        short_description=data.get('short_description'),
        long_description=data.get('long_description'),
        mrp=data.get('mrp'),
        offer_price=data.get('offer_price'),
        sku=data.get('sku'),
        in_stock=data.get('in_stock', True),
        stock_number=data.get('stock_number', 0),
        download_pdfs=",".join(data.get('download_pdfs', [])),
        product_image_urls=",".join(data.get('product_image_urls', [])),
        youtube_links=data.get('youtube_links'),
        technical_information=data.get('technical_information'),
        manufacturer=data.get('manufacturer'),
        special_note=data.get('special_note'),
        whatsapp_number=data.get('whatsapp_number'),
        is_rubber=data.get('is_rubber', False),
        rubber_density=data.get('rubber_density'),
        rubber_height=data.get('rubber_height'),
        rubber_length=data.get('rubber_length'),
        rubber_thickness=data.get('rubber_thickness'),
        rubber_description=data.get('rubber_description'),
        variants=json.dumps(variants) if variants else None
    )
    db.session.add(product)
    db.session.commit()
    app.logger.debug(f"API: Added product: {product.product_name}")
    return jsonify({"message": "Product added", "product_id": product.id}), 201

@app.route('/products', methods=['GET'])
def get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    products_pagination = Product.query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "products": [p.to_dict() for p in products_pagination.items],
        "total_items": products_pagination.total,
        "total_pages": products_pagination.pages,
        "current_page": page,
        "per_page": per_page
    }), 200

@app.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict()), 200

@app.route('/product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    product = Product.query.get_or_404(product_id)
    product.category = data.get('category', product.category)
    product.product_name = data.get('product_name', product.product_name)
    product.short_description = data.get('short_description', product.short_description)
    product.long_description = data.get('long_description', product.long_description)
    product.mrp = data.get('mrp', product.mrp)
    product.offer_price = data.get('offer_price', product.offer_price)
    product.sku = data.get('sku', product.sku)
    product.in_stock = data.get('in_stock', product.in_stock)
    product.stock_number = data.get('stock_number', product.stock_number)
    product.download_pdfs = ",".join(data.get('download_pdfs', product.download_pdfs.split(",") if product.download_pdfs else []))
    product.product_image_urls = ",".join(data.get('product_image_urls', product.product_image_urls.split(",") if product.product_image_urls else []))
    product.youtube_links = data.get('youtube_links', product.youtube_links)
    product.technical_information = data.get('technical_information', product.technical_information)
    product.manufacturer = data.get('manufacturer', product.manufacturer)
    product.special_note = data.get('special_note', product.special_note)
    product.whatsapp_number = data.get('whatsapp_number', product.whatsapp_number)
    product.is_rubber = data.get('is_rubber', product.is_rubber)
    product.rubber_density = data.get('rubber_density', product.rubber_density)
    product.rubber_height = data.get('rubber_height', product.rubber_height)
    product.rubber_length = data.get('rubber_length', product.rubber_length)
    product.rubber_thickness = data.get('rubber_thickness', product.rubber_thickness)
    product.rubber_description = data.get('rubber_description', product.rubber_description)
    product.variants = json.dumps(data.get('variants', json.loads(product.variants) if product.variants else []))
    db.session.commit()
    app.logger.debug(f"API: Updated product ID: {product_id}")
    return jsonify({"message": "Product updated"}), 200

@app.route('/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    app.logger.debug(f"API: Deleted product ID: {product_id}")
    return jsonify({"message": "Product deleted"}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').lower()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search_results_pagination = Product.query.filter(
        Product.product_name.ilike(f'%{query}%') |
        Product.category.ilike(f'%{query}%') |
        Product.short_description.ilike(f'%{query}%') |
        Product.long_description.ilike(f'%{query}%') |
        Product.rubber_description.ilike(f'%{query}%')
    ).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "products": [p.to_dict() for p in search_results_pagination.items],
        "total_items": search_results_pagination.total,
        "total_pages": search_results_pagination.pages,
        "current_page": page,
        "per_page": per_page
    }), 200

# New API to update product by SKU
@app.route('/product/sku/<string:sku>', methods=['PUT'])
def update_product_by_sku(sku):
    data = request.get_json()
    product = Product.query.filter_by(sku=sku).first()
    if not product:
        return jsonify({"error": "Product with given SKU not found"}), 404
    
    product.category = data.get('category', product.category)
    product.product_name = data.get('product_name', product.product_name)
    product.short_description = data.get('short_description', product.short_description)
    product.long_description = data.get('long_description', product.long_description)
    product.mrp = data.get('mrp', product.mrp)
    product.offer_price = data.get('offer_price', product.offer_price)
    product.sku = data.get('sku', product.sku)
    product.in_stock = data.get('in_stock', product.in_stock)
    product.stock_number = data.get('stock_number', product.stock_number)
    product.download_pdfs = ",".join(data.get('download_pdfs', product.download_pdfs.split(",") if product.download_pdfs else []))
    product.product_image_urls = ",".join(data.get('product_image_urls', product.product_image_urls.split(",") if product.product_image_urls else []))
    product.youtube_links = data.get('youtube_links', product.youtube_links)
    product.technical_information = data.get('technical_information', product.technical_information)
    product.manufacturer = data.get('manufacturer', product.manufacturer)
    product.special_note = data.get('special_note', product.special_note)
    product.whatsapp_number = data.get('whatsapp_number', product.whatsapp_number)
    product.is_rubber = data.get('is_rubber', product.is_rubber)
    product.rubber_density = data.get('rubber_density', product.rubber_density)
    product.rubber_height = data.get('rubber_height', product.rubber_height)
    product.rubber_length = data.get('rubber_length', product.rubber_length)
    product.rubber_thickness = data.get('rubber_thickness', product.rubber_thickness)
    product.rubber_description = data.get('rubber_description', product.rubber_description)
    product.variants = json.dumps(data.get('variants', json.loads(product.variants) if product.variants else []))
    db.session.commit()
    app.logger.debug(f"API: Updated product with SKU: {sku}")
    return jsonify({"message": "Product updated", "sku": sku}), 200

# New API to update product by name
@app.route('/product/name/<string:name>', methods=['PUT'])
def update_product_by_name(name):
    data = request.get_json()
    product = Product.query.filter_by(product_name=name).first()
    if not product:
        return jsonify({"error": "Product with given name not found"}), 404
    
    product.category = data.get('category', product.category)
    product.product_name = data.get('product_name', product.product_name)
    product.short_description = data.get('short_description', product.short_description)
    product.long_description = data.get('long_description', product.long_description)
    product.mrp = data.get('mrp', product.mrp)
    product.offer_price = data.get('offer_price', product.offer_price)
    product.sku = data.get('sku', product.sku)
    product.in_stock = data.get('in_stock', product.in_stock)
    product.stock_number = data.get('stock_number', product.stock_number)
    product.download_pdfs = ",".join(data.get('download_pdfs', product.download_pdfs.split(",") if product.download_pdfs else []))
    product.product_image_urls = ",".join(data.get('product_image_urls', product.product_image_urls.split(",") if product.product_image_urls else []))
    product.youtube_links = data.get('youtube_links', product.youtube_links)
    product.technical_information = data.get('technical_information', product.technical_information)
    product.manufacturer = data.get('manufacturer', product.manufacturer)
    product.special_note = data.get('special_note', product.special_note)
    product.whatsapp_number = data.get('whatsapp_number', product.whatsapp_number)
    product.is_rubber = data.get('is_rubber', product.is_rubber)
    product.rubber_density = data.get('rubber_density', product.rubber_density)
    product.rubber_height = data.get('rubber_height', product.rubber_height)
    product.rubber_length = data.get('rubber_length', product.rubber_length)
    product.rubber_thickness = data.get('rubber_thickness', product.rubber_thickness)
    product.rubber_description = data.get('rubber_description', product.rubber_description)
    product.variants = json.dumps(data.get('variants', json.loads(product.variants) if product.variants else []))
    db.session.commit()
    app.logger.debug(f"API: Updated product with name: {name}")
    return jsonify({"message": "Product updated", "product_name": name}), 200

# New API for bulk update of products
@app.route('/products/bulk-update', methods=['PUT'])
def bulk_update_products():
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "Request body must be a list of product updates"}), 400

    updated_products = []
    errors = []

    for update in data:
        identifier = update.get('id') or update.get('sku') or update.get('product_name')
        if not identifier:
            errors.append({"error": "Missing identifier (id, sku, or product_name) for a product update"})
            continue

        if 'id' in update:
            product = Product.query.get(update['id'])
        elif 'sku' in update:
            product = Product.query.filter_by(sku=update['sku']).first()
        else:
            product = Product.query.filter_by(product_name=update['product_name']).first()

        if not product:
            errors.append({"error": f"Product not found for identifier: {identifier}"})
            continue

        try:
            product.category = update.get('category', product.category)
            product.product_name = update.get('product_name', product.product_name)
            product.short_description = update.get('short_description', product.short_description)
            product.long_description = update.get('long_description', product.long_description)
            product.mrp = update.get('mrp', product.mrp)
            product.offer_price = update.get('offer_price', product.offer_price)
            product.sku = update.get('sku', product.sku)
            product.in_stock = update.get('in_stock', product.in_stock)
            product.stock_number = update.get('stock_number', product.stock_number)
            product.download_pdfs = ",".join(update.get('download_pdfs', product.download_pdfs.split(",") if product.download_pdfs else []))
            product.product_image_urls = ",".join(update.get('product_image_urls', product.product_image_urls.split(",") if product.product_image_urls else []))
            product.youtube_links = update.get('youtube_links', product.youtube_links)
            product.technical_information = update.get('technical_information', product.technical_information)
            product.manufacturer = update.get('manufacturer', product.manufacturer)
            product.special_note = update.get('special_note', product.special_note)
            product.whatsapp_number = update.get('whatsapp_number', product.whatsapp_number)
            product.is_rubber = update.get('is_rubber', product.is_rubber)
            product.rubber_density = update.get('rubber_density', product.rubber_density)
            product.rubber_height = update.get('rubber_height', product.rubber_height)
            product.rubber_length = update.get('rubber_length', product.rubber_length)
            product.rubber_thickness = update.get('rubber_thickness', product.rubber_thickness)
            product.rubber_description = update.get('rubber_description', product.rubber_description)
            product.variants = json.dumps(update.get('variants', json.loads(product.variants) if product.variants else []))
            updated_products.append({"identifier": identifier, "status": "updated"})
        except Exception as e:
            errors.append({"error": f"Failed to update product {identifier}: {str(e)}"})

    db.session.commit()
    app.logger.debug(f"API: Bulk updated products: {len(updated_products)} succeeded, {len(errors)} failed")
    return jsonify({
        "message": "Bulk update processed",
        "updated": updated_products,
        "errors": errors
    }), 200 if not errors else 207

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')