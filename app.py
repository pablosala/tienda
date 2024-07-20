import os
from flask import Flask, render_template, redirect, url_for, request, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime 
import mysql.connector
from flask_migrate import Migrate
import pytz
from werkzeug.utils import secure_filename

# Configurar la zona horaria de Madrid
madrid_tz = pytz.timezone('Europe/Madrid')

app = Flask(__name__)



app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024  # 16 MB limit
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://sammy:password@localhost/tienda_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'


# Inicializar la base de datos
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Definir modelos
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    ordenes = db.relationship('Orden', backref='usuario', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)
    productos = db.relationship('Producto', backref='categoria', lazy=True)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    ordenes = db.relationship('OrdenProducto', backref='producto', lazy=True)
    imagenes = db.relationship('Imagen', backref='producto', lazy=True)

class Imagen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)


class Orden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(madrid_tz))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    productos = db.relationship('OrdenProducto', backref='orden', lazy=True)

class OrdenProducto(db.Model):
    orden_id = db.Column(db.Integer, db.ForeignKey('orden.id'), primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), primary_key=True)
    cantidad = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Float, nullable=False)

class Carrito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    items = db.relationship('CarritoItem', backref='carrito', lazy=True)

class CarritoItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey('carrito.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    producto = db.relationship('Producto', backref='carrito_items')




@app.before_request
def before_request():
    if current_user.is_authenticated:
        carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
        g.carrito_items_count = sum(item.cantidad for item in carrito.items) if carrito else 0
    else:
        g.carrito_items_count = 0

@app.context_processor
def inject_carrito_items_count():
    return {'carrito_items_count': g.carrito_items_count}


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        user = Usuario(nombre=nombre, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Usuario registrado con éxito', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Usuario.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Credenciales inválidas', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    productos = Producto.query.all()
    return render_template('index.html', productos=productos)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/galeria')
def galeria():
    imagenes = Imagen.query.all()  # Asumiendo que tienes un modelo Imagen
    return render_template('galeria.html', imagenes=imagenes)

@app.route('/buscar', methods=['GET'])
def buscar():
    query = request.args.get('q', '')
    if query:
        productos = Producto.query.filter(Producto.nombre.like(f'%{query}%')).all()
    else:
        productos = []
    return render_template('resultados_busqueda.html', productos=productos, query=query)


@app.route('/productos')
def productos():
    productos = Producto.query.all()
    return render_template('productos.html', productos=productos)


@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/single')
def single():
    return render_template('single.html')


@app.route('/categoria/<int:categoria_id>')
def categoria_productos(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    productos = Producto.query.filter_by(categoria_id=categoria.id).all()
    for producto in productos:
        producto.imagen_principal = producto.imagenes[0].url if producto.imagenes else 'default.jpg'
    return render_template('categoria_productos.html', categoria=categoria, productos=productos)



@app.context_processor
def inject_categories():
    categorias = Categoria.query.all()
    return dict(categorias=categorias)


@app.route('/category/<int:category_id>')
def category_products(category_id):
    categoria = Categoria.query.get_or_404(category_id)
    productos = Producto.query.filter_by(categoria_id=category_id).all()
    return render_template('category_products.html', categoria=categoria, productos=productos)


@app.route('/producto/<int:producto_id>')
def producto_detalle(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    return render_template('single.html', producto=producto)

@app.route('/agregar_carrito/<int:producto_id>', methods=['POST'])
@login_required
def agregar_carrito(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    cantidad = int(request.form['cantidad'])
    
    # Obtener o crear el carrito para el usuario actual
    carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if not carrito:
        carrito = Carrito(usuario_id=current_user.id)
        db.session.add(carrito)
        db.session.commit()

    # Verificar si el producto ya está en el carrito
    item = CarritoItem.query.filter_by(carrito_id=carrito.id, producto_id=producto_id).first()
    if item:
        item.cantidad += cantidad
    else:
        item = CarritoItem(carrito_id=carrito.id, producto_id=producto_id, cantidad=cantidad)
        db.session.add(item)

    db.session.commit()
    flash(f'{producto.nombre} agregado al carrito', 'success')
    return redirect(url_for('index'))



@app.route('/carrito')
@login_required
def carrito():
    carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
    items = carrito.items if carrito else []
    return render_template('carrito.html', items=items)


@app.route('/realizar_pedido', methods=['POST'])
@login_required
def realizar_pedido():
    carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if not carrito or not carrito.items:
        flash('El carrito está vacío', 'danger')
        return redirect(url_for('index'))

    total = sum(item.cantidad * item.producto.precio for item in carrito.items)
    orden = Orden(usuario_id=current_user.id, total=total)
    db.session.add(orden)
    db.session.commit()

    for item in carrito.items:
        orden_producto = OrdenProducto(orden_id=orden.id, producto_id=item.producto_id, cantidad=item.cantidad, precio=item.producto.precio)
        db.session.add(orden_producto)
        db.session.delete(item)

    db.session.commit()
    db.session.delete(carrito)
    db.session.commit()
    flash('Pedido realizado con éxito', 'success')
    return redirect(url_for('index'))



@app.route('/mis_pedidos')
@login_required
def mis_pedidos():
    pedidos = Orden.query.filter_by(usuario_id=current_user.id).all()
    return render_template('mis_pedidos.html', pedidos=pedidos)

@app.route('/pedido/<int:pedido_id>')
@login_required
def pedido_detalle(pedido_id):
    pedido = Orden.query.get_or_404(pedido_id)
    if pedido.usuario_id != current_user.id:
        flash('No tienes permiso para ver este pedido', 'danger')
        return redirect(url_for('index'))
    return render_template('pedido_detalle.html', pedido=pedido)












@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    return render_template('admin.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_dashboard.html')


@app.route('/admin/products')
@login_required
def admin_products():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    productos = Producto.query.all()
    return render_template('admin_products.html', productos=productos)



@app.route('/admin/agregar_producto', methods=['GET', 'POST'])
@login_required
def agregar_producto():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        stock = int(request.form['stock'])
        categoria_id = int(request.form['categoria_id'])
        producto = Producto(nombre=nombre, descripcion=descripcion, precio=precio, stock=stock, categoria_id=categoria_id)
        db.session.add(producto)
        db.session.commit()
        
        # Guardar la imagen
        if 'imagen' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['imagen']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagen = Imagen(url=filename, producto_id=producto.id)
            db.session.add(imagen)
            db.session.commit()
        
        flash('Producto agregado con éxito', 'success')
        return redirect(url_for('admin'))
    categorias = Categoria.query.all()
    return render_template('agregar_producto.html', categorias=categorias)

@app.route('/admin/editar_producto/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def editar_producto(producto_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    producto = Producto.query.get_or_404(producto_id)
    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.descripcion = request.form['descripcion']
        producto.precio = float(request.form['precio'])
        producto.stock = int(request.form['stock'])
        producto.categoria_id = int(request.form['categoria_id'])
        db.session.commit()
        
        # Guardar la imagen
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen = Imagen(url=filename, producto_id=producto.id)
                db.session.add(imagen)
                db.session.commit()
        
        flash('Producto editado con éxito', 'success')
        return redirect(url_for('admin'))
    categorias = Categoria.query.all()
    return render_template('editar_producto.html', producto=producto, categorias=categorias)



@app.route('/admin/eliminar_producto/<int:producto_id>', methods=['POST'])
@login_required
def eliminar_producto(producto_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    producto = Producto.query.get_or_404(producto_id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado con éxito', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/ver_pedidos')
@login_required
def ver_pedidos():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    pedidos = Orden.query.all()
    return render_template('ver_pedidos.html', pedidos=pedidos)

@app.route('/admin/ver_pedido/<int:order_id>')
@login_required
def ver_pedido(order_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    order = Orden.query.get_or_404(order_id)
    return render_template('ver_pedido.html', order=order)

@app.route('/admin/eliminar_pedido/<int:order_id>', methods=['POST'])
@login_required
def eliminar_pedido(order_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    order = Orden.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash('Order deleted successfully', 'success')
    return redirect(url_for('admin_orders'))


@app.route('/admin/categorias')
@login_required
def admin_categorias():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    categorias = Categoria.query.all()
    return render_template('admin_categorias.html', categorias=categorias)

@app.route('/admin/categorias/nueva', methods=['GET', 'POST'])
@login_required
def nueva_categoria():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if not nombre:
            flash('El nombre es obligatorio', 'danger')
            return render_template('nueva_categoria.html')
        categoria = Categoria(nombre=nombre)
        db.session.add(categoria)
        db.session.commit()
        flash('Categoría creada con éxito', 'success')
        return redirect(url_for('admin_categorias'))
    return render_template('nueva_categoria.html')


@app.route('/admin/categorias/editar/<int:categoria_id>', methods=['GET', 'POST'])
@login_required
def editar_categoria(categoria_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    categoria = Categoria.query.get_or_404(categoria_id)
    if request.method == 'POST':
        categoria.nombre = request.form['nombre']
        db.session.commit()
        flash('Categoría editada con éxito', 'success')
        return redirect(url_for('admin_categorias'))
    return render_template('editar_categoria.html', categoria=categoria)

@app.route('/admin/eliminar_categoria/<int:categoria_id>', methods=['POST'])
@login_required
def eliminar_categoria(categoria_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    categoria = Categoria.query.get_or_404(categoria_id)
    db.session.delete(categoria)
    db.session.commit()
    flash('Categoría eliminada con éxito', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/orders')
@login_required
def admin_orders():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    orders = Orden.query.all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    usuarios = Usuario.query.all()
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin/editar_usuario/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(usuario_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    usuario = Usuario.query.get_or_404(usuario_id)
    if request.method == 'POST':
        usuario.nombre = request.form['nombre']
        usuario.email = request.form['email']
        usuario.role = request.form['role']
        db.session.commit()
        flash('Usuario editado con éxito', 'success')
        return redirect(url_for('admin_usuarios'))
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/admin/eliminar_usuario/<int:usuario_id>', methods=['POST'])
@login_required
def eliminar_usuario(usuario_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    usuario = Usuario.query.get_or_404(usuario_id)
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuario eliminado con éxito', 'success')
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/customers')
@login_required
def admin_customers():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    customers = User.query.filter_by(role='customer').all()
    return render_template('admin_customers.html', customers=customers)

@app.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    # Implement report logic here
    return render_template('admin_reports.html')

@app.route('/admin/settings')
@login_required
def admin_settings():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    # Implement settings logic here
    return render_template('admin_settings.html')






if __name__ == "__main__":
    app.run()