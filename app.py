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
from jinja2 import Environment, FileSystemLoader
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer
import requests
import math
import json
import base64
from Crypto.Cipher import DES3
import hmac
import hashlib
# Configurar la zona horaria de Madrid
madrid_tz = pytz.timezone('Europe/Madrid')


app = Flask(__name__)
app.config.from_object('config.Config')




app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024  # 16 MB limit
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://sammy:password@localhost/tienda_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'



app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'
app.config['SECURITY_PASSWORD_SALT'] = 'your-password-salt'



# Inicializar la base de datos
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'



class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    is_confirmed = db.Column(db.Boolean, default=False)
    ordenes = db.relationship('Orden', backref='usuario', lazy=True)
    direcciones = db.relationship('Direccion', backref='usuario', lazy=True)
    metodos_pago = db.relationship('MetodoPago', backref='usuario', lazy=True)
    carrito = db.relationship('Carrito', backref='usuario', uselist=False)
    valoraciones = db.relationship('Valoracion', backref='autor', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class TempUsuario(db.Model):
    __tablename__ = 'temp_usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Categoria(db.Model):
    __tablename__ = 'categoria'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)
    productos = db.relationship('Producto', backref='categoria', lazy=True)


class Producto(db.Model):
    __tablename__ = 'producto'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    ordenes = db.relationship('OrdenProducto', backref='producto', lazy=True)
    imagenes = db.relationship('Imagen', backref='producto', lazy=True, cascade="all, delete-orphan")
    valoraciones = db.relationship('Valoracion', backref='producto_valoraciones', lazy=True)


class Imagen(db.Model):
    __tablename__ = 'imagen'
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)


class Orden(db.Model):
    __tablename__ = 'orden'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    direccion_envio_id = db.Column(db.Integer, db.ForeignKey('direccion.id'), nullable=False)
    metodo_pago_id = db.Column(db.Integer, db.ForeignKey('metodo_pago.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    notas = db.Column(db.Text, nullable=True)
    productos = db.relationship('OrdenProducto', backref='orden', lazy=True, cascade="all, delete-orphan")


class OrdenProducto(db.Model):
    __tablename__ = 'orden_producto'
    
    orden_id = db.Column(db.Integer, db.ForeignKey('orden.id'), primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), primary_key=True)
    cantidad = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Float, nullable=False)


class Carrito(db.Model):
    __tablename__ = 'carrito'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    items = db.relationship('CarritoItem', backref='carrito', lazy=True)


class CarritoItem(db.Model):
    __tablename__ = 'carrito_item'
    
    id = db.Column(db.Integer, primary_key=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey('carrito.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    producto = db.relationship('Producto', backref='carrito_items')


class Direccion(db.Model):
    __tablename__ = 'direccion'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    ciudad = db.Column(db.String(100), nullable=False)
    provincia = db.Column(db.String(100), nullable=False)
    codigo_postal = db.Column(db.String(20), nullable=False)
    pais = db.Column(db.String(100), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    ordenes = db.relationship('Orden', backref='direccion_envio', lazy=True)


class MetodoPago(db.Model):
    __tablename__ = 'metodo_pago'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    numero = db.Column(db.String(20), nullable=False)
    expiracion = db.Column(db.String(7), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    ordenes = db.relationship('Orden', backref='metodo_pago', lazy=True)


class Valoracion(db.Model):
    __tablename__ = 'valoracion'
    
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    puntuacion = db.Column(db.Integer, nullable=False)
    comentario = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref='valoraciones_usuario', lazy=True)
    producto = db.relationship('Producto', backref='valoraciones_producto', lazy=True)



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
        
        # Verificar si el correo ya está registrado en la tabla temporal o principal
        user = Usuario.query.filter_by(email=email).first() or TempUsuario.query.filter_by(email=email).first()
        if user:
            flash('El correo electrónico ya está registrado. Por favor, inicia sesión.', 'warning')
            return redirect(url_for('login'))

        # Crear el usuario temporal
        temp_user = TempUsuario(nombre=nombre, email=email)
        temp_user.set_password(password)
        
        try:
            db.session.add(temp_user)
            db.session.commit()
            
            # Generar token de confirmación y enviar correo
            token = generate_confirmation_token(email)
            confirm_url = url_for('confirm_email', token=token, _external=True)
            html_content = render_template('email_confirmation.html', confirm_url=confirm_url)
            send_email(email, 'Confirma tu correo electrónico', html_content)
            
            flash('Se ha enviado un correo electrónico para confirmar tu dirección de correo.', 'success')
            return redirect(url_for('waiting_confirmation', email=email))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el usuario: {str(e)}', 'danger')
    
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
    for producto in productos:
        producto.imagen_principal = producto.imagenes[0].url if producto.imagenes else 'default.jpg'
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

@app.route('/detalles_cuenta', methods=['GET', 'POST'])
@login_required
def detalles_cuenta():
    if request.method == 'POST':
        current_user.nombre = request.form['nombre']
        current_user.email = request.form['email']
        db.session.commit()
        flash('Tu cuenta ha sido actualizada!', 'success')
        return redirect(url_for('detalles_cuenta'))
    
    ordenes = Orden.query.filter_by(usuario_id=current_user.id).all()
    direcciones = Direccion.query.filter_by(usuario_id=current_user.id).all()
    metodos_pago = MetodoPago.query.filter_by(usuario_id=current_user.id).all()
    
    return render_template('detalles_cuenta.html', title='Detalles de la cuenta', user=current_user, ordenes=ordenes, direcciones=direcciones, metodos_pago=metodos_pago)


@app.route('/direccion/nueva', methods=['GET', 'POST'])
@login_required
def nueva_direccion():
    if request.method == 'POST':
        nombre = request.form['nombre']
        direccion = request.form['direccion']
        ciudad = request.form['ciudad']
        provincia = request.form['provincia']
        codigo_postal = request.form['codigo_postal']
        pais = request.form['pais']
        nueva_direccion = Direccion(nombre=nombre, direccion=direccion, ciudad=ciudad, provincia=provincia, codigo_postal=codigo_postal, pais=pais, usuario_id=current_user.id)
        db.session.add(nueva_direccion)
        db.session.commit()
        flash('Dirección añadida con éxito!', 'success')
        return redirect(url_for('detalles_cuenta'))
    return render_template('nueva_direccion.html')

@app.route('/direccion/editar/<int:direccion_id>', methods=['GET', 'POST'])
@login_required
def editar_direccion(direccion_id):
    direccion = Direccion.query.get_or_404(direccion_id)
    if request.method == 'POST':
        direccion.nombre = request.form['nombre']
        direccion.direccion = request.form['direccion']
        direccion.ciudad = request.form['ciudad']
        direccion.provincia = request.form['provincia']
        direccion.codigo_postal = request.form['codigo_postal']
        direccion.pais = request.form['pais']
        db.session.commit()
        flash('Dirección actualizada con éxito!', 'success')
        return redirect(url_for('detalles_cuenta'))
    return render_template('editar_direccion.html', direccion=direccion)

@app.route('/direccion/eliminar/<int:direccion_id>', methods=['POST'])
@login_required
def eliminar_direccion(direccion_id):
    direccion = Direccion.query.get_or_404(direccion_id)
    db.session.delete(direccion)
    db.session.commit()
    flash('Dirección eliminada con éxito!', 'success')
    return redirect(url_for('detalles_cuenta'))

@app.route('/nuevo_metodo_pago', methods=['GET', 'POST'])
@login_required
def nuevo_metodo_pago():
    if request.method == 'POST':
        tipo = request.form['tipo']
        numero = request.form['numero']
        expiracion = request.form['expiracion']
        
        nuevo_metodo = MetodoPago(tipo=tipo, numero=numero, expiracion=expiracion, usuario_id=current_user.id)
        db.session.add(nuevo_metodo)
        db.session.commit()
        
        flash('Nuevo método de pago añadido con éxito', 'success')
        return redirect(url_for('detalles_cuenta'))
    
    return render_template('nuevo_metodo_pago.html')


@app.route('/metodo_pago/editar/<int:metodo_id>', methods=['GET', 'POST'])
@login_required
def editar_metodo_pago(metodo_id):
    metodo = MetodoPago.query.get_or_404(metodo_id)
    if request.method == 'POST':
        metodo.tipo = request.form['tipo']
        metodo.numero = request.form['numero']
        metodo.expiracion = request.form['expiracion']
        db.session.commit()
        flash('Método de pago actualizado con éxito!', 'success')
        return redirect(url_for('detalles_cuenta'))
    return render_template('editar_metodo_pago.html', metodo=metodo)

@app.route('/metodo_pago/eliminar/<int:metodo_id>', methods=['POST'])
@login_required
def eliminar_metodo_pago(metodo_id):
    metodo = MetodoPago.query.get_or_404(metodo_id)
    db.session.delete(metodo)
    db.session.commit()
    flash('Método de pago eliminado con éxito!', 'success')
    return redirect(url_for('detalles_cuenta'))


def encrypt_3DES(message, key):
    key = base64.b64decode(key)
    des3 = DES3.new(key, DES3.MODE_CBC, b'\0\0\0\0\0\0\0\0')
    padded_message = message + (8 - len(message) % 8) * '\0'
    encrypted_message = des3.encrypt(padded_message.encode('utf-8'))
    return base64.b64encode(encrypted_message).decode('utf-8')

def calculate_hmac(key, data):
    key = base64.b64decode(key)
    data = data.encode('utf-8')
    return base64.b64encode(hmac.new(key, data, hashlib.sha256).digest()).decode('utf-8')

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    usuario_id = current_user.id
    carrito = Carrito.query.filter_by(usuario_id=usuario_id).first()

    if not carrito or not carrito.items:
        flash('No hay productos en el carrito', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        direccion_envio_id = request.form.get('direccion_envio')
        metodo_pago_id = request.form.get('metodo_pago')

        # Validar y manejar nueva dirección
        if direccion_envio_id == 'nueva':
            nueva_direccion = Direccion(
                nombre=request.form['nombre_direccion'],
                direccion=request.form['direccion'],
                ciudad=request.form['ciudad'],
                provincia=request.form['provincia'],
                codigo_postal=request.form['codigo_postal'],
                pais=request.form['pais'],
                usuario_id=usuario_id
            )
            db.session.add(nueva_direccion)
            db.session.flush()
            direccion_envio_id = nueva_direccion.id
        elif not direccion_envio_id:
            flash('Por favor seleccione o añada una dirección de envío.', 'danger')
            return redirect(url_for('checkout'))

        # Validar y manejar nuevo método de pago
        if metodo_pago_id == 'nuevo':
            nuevo_metodo_pago = MetodoPago(
                tipo=request.form['tipo_pago'],
                numero=request.form['numero_pago'],
                expiracion=request.form['expiracion_pago'],
                usuario_id=usuario_id
            )
            db.session.add(nuevo_metodo_pago)
            db.session.flush()
            metodo_pago_id = nuevo_metodo_pago.id
        elif not metodo_pago_id:
            flash('Por favor seleccione o añada un método de pago.', 'danger')
            return redirect(url_for('checkout'))

        # Crear un nuevo pedido
        pedido = Orden(
            usuario_id=usuario_id,
            direccion_envio_id=direccion_envio_id,
            metodo_pago_id=metodo_pago_id,
            total=sum(item.cantidad * item.producto.precio for item in carrito.items),
            status='Pending'
        )
        db.session.add(pedido)
        db.session.commit()

        # Mover los items del carrito al pedido
        for item in carrito.items:
            orden_producto = OrdenProducto(
                orden_id=pedido.id,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                precio=item.producto.precio
            )
            db.session.add(orden_producto)
            db.session.delete(item)  # Eliminar los items del carrito
        db.session.commit()

        # Redirigir a la pasarela de pago de Redsys
        amount = pedido.total
        order_id = f'{pedido.id:06d}'  # Asegúrate de que el ID del pedido tiene 6 dígitos

        # Preparar los datos para la petición al TPV
        merchant_parameters = {
            'DS_MERCHANT_AMOUNT': str(int(float(amount) * 100)),
            'DS_MERCHANT_ORDER': order_id,
            'DS_MERCHANT_MERCHANTCODE': app.config['TPV_MERCHANT_CODE'],
            'DS_MERCHANT_CURRENCY': app.config['TPV_CURRENCY'],
            'DS_MERCHANT_TRANSACTIONTYPE': app.config['TPV_TRANSACTION_TYPE'],
            'DS_MERCHANT_TERMINAL': app.config['TPV_TERMINAL'],
            'DS_MERCHANT_MERCHANTURL': app.config['TPV_CALLBACK_URL'],
            'DS_MERCHANT_URLOK': url_for('callback', _external=True),
            'DS_MERCHANT_URLKO': url_for('callback', _external=True)
        }

        # Debug: Imprimir merchant_parameters
        print("Merchant Parameters:", merchant_parameters)

        merchant_parameters_base64 = base64.b64encode(json.dumps(merchant_parameters).encode('utf-8')).decode('utf-8')
        key = encrypt_3DES(order_id, app.config['TPV_SECRET_KEY'])
        signature = calculate_hmac(key, merchant_parameters_base64)

        return render_template('tpv_form.html', merchant_parameters=merchant_parameters_base64, signature=signature)

    direcciones = Direccion.query.filter_by(usuario_id=usuario_id).all()
    metodos_pago = MetodoPago.query.filter_by(usuario_id=usuario_id).all()
    carrito_items = CarritoItem.query.filter_by(carrito_id=carrito.id).all()
    return render_template('checkout.html', title='Finalizar Compra', carrito_items=carrito_items, direcciones=direcciones, metodos_pago=metodos_pago, user=current_user)

@app.route('/callback', methods=['POST'])
def callback():
    data = request.form
    # Manejar la respuesta del TPV (ej. confirmar el pago, actualizar el estado del pedido, etc.)
    return '', 200
def calcular_total_carrito(carrito_id):
    carrito_items = CarritoItem.query.filter_by(carrito_id=carrito_id).all()
    total = sum(item.cantidad * item.producto.precio for item in carrito_items)
    return total

def calcular_total_carrito(usuario_id):
    carrito_items = CarritoItem.query.filter_by(carrito_id=usuario_id).all()
    total = sum(item.cantidad * item.producto.precio for item in carrito_items)
    return total


@app.route('/categoria/<int:categoria_id>')
def categoria_productos(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    productos = Producto.query.filter_by(categoria_id=categoria.id).all()
    for producto in productos:
        producto.imagen_principal = producto.imagenes[0].url if producto.imagenes else 'default.jpg'
    return render_template('categoria_productos.html', categoria=categoria, productos=productos)

@app.route('/buscar', methods=['GET'])
def buscar():
    query = request.args.get('q', '')
    if query:
        productos = Producto.query.filter(Producto.nombre.like(f'%{query}%')).all()
    else:
        productos = []
    return render_template('resultados_busqueda.html', productos=productos, query=query)

@app.context_processor
def inject_categories():
    categorias = Categoria.query.all()
    return dict(categorias=categorias)


@app.route('/category/<int:category_id>')
def category_products(category_id):
    categoria = Categoria.query.get_or_404(category_id)
    productos = Producto.query.filter_by(categoria_id=category_id).all()
    return render_template('category_products.html', categoria=categoria, productos=productos)


@app.route('/producto/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def producto_detalle(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    ha_comprado = Orden.query.filter_by(usuario_id=current_user.id).join(OrdenProducto).filter_by(producto_id=producto_id).all()

    if request.method == 'POST':
        puntuacion = int(request.form['puntuacion'])
        comentario = request.form['comentario']

        if not (1 <= puntuacion <= 5):
            flash('La puntuación debe estar entre 1 y 5 estrellas.', 'danger')
            return redirect(url_for('producto_detalle', producto_id=producto_id))

        if not ha_comprado:
            flash('Solo puedes valorar productos que hayas comprado.', 'danger')
            return redirect(url_for('producto_detalle', producto_id=producto_id))

        valoracion = Valoracion(producto_id=producto_id,
                                usuario_id=current_user.id,
                                puntuacion=puntuacion,
                                comentario=comentario)

        db.session.add(valoracion)
        db.session.commit()

        flash('Gracias por tu valoración!', 'success')
        return redirect(url_for('producto_detalle', producto_id=producto_id))

    return render_template('single.html', producto=producto, ha_comprado=ha_comprado)


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

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/producto/<int:producto_id>/valorar', methods=['GET', 'POST'])
@login_required
def valorar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    if request.method == 'POST':
        puntuacion = int(request.form['puntuacion'])
        comentario = request.form['comentario']
        
        if not (1 <= puntuacion <= 5):
            flash('La puntuación debe estar entre 1 y 5 estrellas.', 'danger')
            return redirect(url_for('valorar_producto', producto_id=producto_id))
        
        # Verificar si el usuario ha comprado este producto
        ordenes = Orden.query.filter_by(usuario_id=current_user.id)\
                             .join(OrdenProducto)\
                             .filter_by(producto_id=producto_id)\
                             .all()
        
        if not ordenes:
            flash('Solo puedes valorar productos que hayas comprado.', 'danger')
            return redirect(url_for('producto_detalle', producto_id=producto_id))
        
        valoracion = Valoracion(producto_id=producto_id,
                                usuario_id=current_user.id,
                                puntuacion=puntuacion,
                                comentario=comentario)
        
        db.session.add(valoracion)
        db.session.commit()
        
        flash('Gracias por tu valoración!', 'success')
        return redirect(url_for('producto_detalle', producto_id=producto_id))
    
    return render_template('valorar_producto.html', producto=producto)













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

@app.route('/admin/eliminar_imagen/<int:imagen_id>', methods=['POST'])
@login_required
def eliminar_imagen(imagen_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    imagen = Imagen.query.get_or_404(imagen_id)
    producto_id = request.form['producto_id']
    
    try:
        # Eliminar archivo de imagen del sistema de archivos si es necesario
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], imagen.url)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Eliminar registro de la base de datos
        db.session.delete(imagen)
        db.session.commit()
        flash('Imagen eliminada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la imagen: {str(e)}', 'danger')
    
    return redirect(url_for('editar_producto', producto_id=producto_id))



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

@app.route('/admin/correo')
@login_required
def admin_correo():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    return render_template('enviar_correo.html')

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




@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        user = Usuario.query.filter_by(email=email).first()
        if user:
            token = generate_confirmation_token(user.email)
            send_reset_email(user.email, token)
            flash('Se ha enviado un correo electrónico con instrucciones para restablecer la contraseña.', 'success')
            return redirect(url_for('login'))
        else:
            flash('No se encontró una cuenta con ese correo electrónico.', 'danger')
            return redirect(url_for('reset_password'))
    return render_template('reset_password.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    try:
        email = confirm_token(token)
    except:
        flash('El enlace para restablecer la contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('reset_password'))

    if request.method == 'POST':
        password = request.form['password']
        user = Usuario.query.filter_by(email=email).first_or_404()
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        flash('Tu contraseña ha sido actualizada.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_with_token.html', token=token)

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=expiration)
    except:
        return False
    return email

def send_reset_email(to_email, token):
    subject = "Restablecer tu contraseña"
    html_content = render_template('reset_password_email.html', token=token, _external=True)
    send_email(to_email, subject, html_content)

def send_email(to_email, subject, html_content):
    from_email = 'salasaxsolidsurface@gmail.com'

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    try:
        server = smtplib.SMTP('localhost', 25)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print(f'Correo enviado a {to_email}')
    except Exception as e:
        print(f'Error al enviar correo: {e}')

@app.route('/send_email_test', methods=['POST'])
def send_email_test():
    to_email = request.form['email']
    nombre = request.form['nombre']
    subject = 'Prueba de correo desde Sala Sax'
    message = 'Este es un mensaje de prueba.'

    html_content = render_template('email_template.html', nombre=nombre, subject=subject, message=message)
    send_email(to_email, subject, html_content)
    flash('Correo enviado con éxito', 'success')
    return redirect(url_for('index'))


def send_welcome_email(to_email):
    subject = 'Bienvenido a Sala Sax'
    html_content = render_template('welcome_email.html')
    send_email(to_email, subject, html_content)

@app.route('/waiting_confirmation')
def waiting_confirmation():
    return render_template('waiting_confirmation.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('El enlace de confirmación es inválido o ha expirado.', 'danger')
        return redirect(url_for('index'))
    
    temp_user = TempUsuario.query.filter_by(email=email).first()
    if temp_user:
        try:
            # Crear el usuario en la tabla principal
            user = Usuario(nombre=temp_user.nombre, email=temp_user.email, password_hash=temp_user.password_hash)
            db.session.add(user)
            db.session.flush()  # Obtener el ID del usuario antes de hacer commit
            
            # Crear un carrito para el usuario recién registrado
            carrito = Carrito(usuario_id=user.id)
            db.session.add(carrito)
            db.session.delete(temp_user)  # Eliminar el usuario temporal
            db.session.commit()  # Hacer commit para todos los cambios
            
            send_welcome_email(user.email)
            
            flash('Tu cuenta ha sido confirmada y registrada con éxito. Por favor, inicia sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al confirmar el usuario: {str(e)}', 'danger')
    
    flash('Ocurrió un error al confirmar tu cuenta. Por favor, inténtalo de nuevo.', 'danger')
    return redirect(url_for('index'))


@app.route('/check_confirmation_status', methods=['POST'])
def check_confirmation_status():
    email = request.form['email']
    user = Usuario.query.filter_by(email=email).first()
    if user and user.is_confirmed:
        return jsonify({'confirmed': True})
    return jsonify({'confirmed': False})

@app.route('/await_confirmation/<email>')
def await_confirmation(email):
    return render_template('await_confirmation.html', email=email)





@app.route('/customize_countertop', methods=['GET', 'POST'])
def customize_countertop():
    if request.method == 'POST':
        # Obtener los datos del formulario
        length = request.form['length']
        width = request.form['width']
        sink = request.form['sink']
        color = request.form['color']
        edge = request.form['edge']
        backsplash = request.form['backsplash']

        # Aquí puedes agregar la lógica para procesar los datos,
        # como guardarlos en una base de datos o realizar cálculos.

        flash('Encimera personalizada creada con éxito!', 'success')
        return redirect(url_for('index'))

    return render_template('customize_countertop.html')
















#------------------------------------- PRESUAPP ----------------------------------






try:
    with open('config.json', 'r') as config_file:
        app.config['configuracion'] = json.load(config_file)
except FileNotFoundError:
    # Si el archivo no existe, crea una configuración inicial vacía
    app.config['configuracion'] = {}


@app.route('/admin/presuapp')
def presuapp():
    return render_template('presuapp.html', configuracion=app.config['configuracion'])


@app.route('/fijar_precios', methods=['POST'])
def fijar_precios():
    if request.is_json:
        # Obtén los precios del cuerpo JSON de la solicitud
        precios = request.get_json()
        
        # Actualiza la configuración en la aplicación
        app.config['configuracion'].update(precios)
    
        # Guarda la configuración en el archivo JSON
        with open('config.json', 'w') as config_file:
            json.dump(app.config['configuracion'], config_file)

        # Puedes devolver una respuesta JSON para confirmar el éxito
        return jsonify({'message': 'Precios guardados exitosamente'})
    
    # En caso contrario, si la solicitud no es JSON, puedes devolver una respuesta de error
    return jsonify({'error': 'Solicitud no válida'}), 400


@app.route('/calcular', methods=['POST'])
def calcular():
    #################### CARGA DE PRECIOS DESDE config.json ##########################
    with open('config.json', 'r') as config_file:
        precios_config = json.load(config_file)

    solid_costo_unitario = float(precios_config.get('solid_costo_unitario', 120.0))
    precio_lija = float(precios_config.get('precio_lija', 5.0))
    precio_pegamento = float(precios_config.get('precio_pegamento', 12.0))
    precio_p404 = float(precios_config.get('precio_p404', 9.0))
    precio_mecanizado = float(precios_config.get('precio_mecanizado', 75.0))
    precio_mecanizado_peon = float(precios_config.get('precio_mecanizado_peon', 75.0))

    # Obtener el tipo de presupuesto
    tipo_presupuesto = request.form['tipo_presupuesto']

    # Obtener listas de ancho y largo de Solid
    solid_ancho_list = [float(x) if x else 0.0 for x in request.form.getlist('solid_ancho[]')]
    solid_largo_list = [float(x) if x else 0.0 for x in request.form.getlist('solid_largo[]')]

    # Sumar todas las áreas de "Solid"
    total_m2_decimal = sum([ancho * largo for ancho, largo in zip(solid_ancho_list, solid_largo_list)])
    total_m2 = math.ceil(total_m2_decimal)#Redondeado al alza
    area_solid = total_m2 * solid_costo_unitario


    # Obtener los valores de los otros atributos comunes
    pegamento = float(request.form['pegamento']) if 'pegamento' in request.form and request.form['pegamento'] else 0.0
    lijas = float(request.form['lijas']) if 'lijas' in request.form and request.form['lijas'] else 0.0
    p404 = float(request.form['p404']) if 'p404' in request.form and request.form['p404'] else 0.0
    mecanizado = float(request.form['mecanizado']) if 'mecanizado' in request.form and request.form['mecanizado'] else 0.0
    peon = float(request.form['peon']) if 'peon' in request.form and request.form['peon'] else 0.0
    fregadero = float(request.form['fregadero']) if 'fregadero' in request.form and request.form['fregadero'] else 0.0
    valvula = float(request.form['valvula']) if 'valvula' in request.form and request.form['valvula'] else 0.0
    colocacion = float(request.form['colocacion']) if 'colocacion' in request.form and request.form['colocacion'] else 0.0
    desplazamiento = float(request.form['desplazamiento']) if 'desplazamiento' in request.form and request.form['desplazamiento'] else 0.0

    # Inicializa las variables con valores predeterminados de 0.0
    mano_obra_solid = 0.0
    mano_obra_acero = 0.0

    # Verifica si se proporcionan los valores en el formulario y asigna los valores correspondientes
    if 'mano_obra_solid' in request.form and request.form['mano_obra_solid']:
        mano_obra_solid = float(request.form['mano_obra_solid'])

    if 'mano_obra_acero' in request.form and request.form['mano_obra_acero']:
        mano_obra_acero = float(request.form['mano_obra_acero'])

    # Obtener listas de ancho y largo para calcular lijas
    solid_ancho_list = request.form.getlist('solid_ancho[]')
    solid_largo_list = request.form.getlist('solid_largo[]')

    solid_ancho_list = [float(ancho) for ancho in solid_ancho_list if ancho]
    solid_largo_list = [float(largo) for largo in solid_largo_list if largo]

    # Calcula el costo de las lijas
    lijas = sum([ancho * largo for ancho, largo in zip(solid_ancho_list, solid_largo_list)]) * precio_lija

    # Agrega el campo "Costado" solo si es "Isla"
    costado = float(request.form['costado']) if tipo_presupuesto == 'isla' and 'costado' in request.form and request.form['costado'] else 0.0

    tipo_fregadero = request.form.get('tipo_fregadero_solid')
    tipo = request.form.get('tipo')
    precio_solid_fregadero = 0.0
    precio_solid_lavabo = 0.0
    mecanizado_solid = 0.0
    copete = request.form.get('copete')
    fabricable = request.form.get('fabricable', '')
    entrepano = request.form.get('entrepaño')


    if tipo_fregadero == 'Fregadero':
        precio_solid_fregadero = float(request.form['precio_solid_fregadero']) if 'precio_solid_fregadero' in request.form and request.form['precio_solid_fregadero'] else 0.0
        mecanizado_solid = float(request.form.get('mecanizado_solid', 0.0))
        mano_obra_solid = float(request.form.get('mano_obra_solid_fregadero', 0.0))
    elif tipo_fregadero == 'Lavabo':
        precio_solid_lavabo = float(request.form['precio_solid_lavabo']) if 'precio_solid_lavabo' in request.form and request.form['precio_solid_lavabo'] else 0.0
        mecanizado_solid = float(request.form.get('mecanizado_solid', 0.0))
        mano_obra_solid = float(request.form.get('mano_obra_solid_lavabo', 0.0))
    elif tipo_fregadero == 'acero':
        mano_obra_acero = float(request.form.get('mano_obra_acero', 0.0))

    tipo_canto = request.form.get('tipo_canto', 'recto')  # Valor predeterminado si no se selecciona tipo de canto

    precios_canto = {
        'recto': {
            'hasta_2_4': 40,
            '3_a_6': 60,
            '8_o_mas': 70
        },
        'redondo': {
            'hasta_2_4': 50,
            '3_a_6': 70,
            '8_o_mas': 80
        }
    }

    if tipo_canto == '-':
        costo_canto = 0.0
        medida_canto = ''
    else:
        medida_canto = request.form.get(f'medida_canto_{tipo_canto}', 'hasta_2_4')  # Valor predeterminado si no se selecciona medida de canto
        costo_canto = precios_canto.get(tipo_canto, {}).get(medida_canto, 0.0)

    metros_canto = float(request.form.get('metros_canto', 0.0))

    # Calcula el costo del pegamento para cantos
    costo_pegamento_cantos = (metros_canto / 3) * precio_pegamento

    # Calcula el costo de las lijas para cantos
    costo_lijas_cantos = metros_canto * precio_lija

    # Calcula el presupuesto total
    costo_pegamento = pegamento * precio_pegamento
    cantidad_pegamento = pegamento * 3

    costo_p404 = p404 * precio_p404
    cantidad_p404 = p404 * 3
    costo_desplazamiento = 0

    # Mecanizado
    costo_mecanizado = mecanizado * precio_mecanizado
    costo_mecanizado_peon = peon * precio_mecanizado_peon

    presupuesto_total = calcular_presupuesto(
        tipo_presupuesto, area_solid, costo_pegamento + costo_pegamento_cantos, lijas, p404, mecanizado, peon, fregadero,
        valvula, colocacion, costo_desplazamiento, costado, tipo_canto, medida_canto, metros_canto, costo_canto,
        costo_pegamento_cantos, costo_lijas_cantos, tipo_fregadero, precio_solid_fregadero if tipo_fregadero == 'Fregadero' else precio_solid_lavabo,
        mecanizado_solid, mano_obra_solid, mano_obra_acero
    )

    return render_template('factura.html', area_solid=area_solid, total_m2=total_m2, pegamento=pegamento, precio_pegamento=precio_pegamento,
                           costo_pegamento=costo_pegamento, cantidad_pegamento=cantidad_pegamento, lijas=lijas, precio_lija=precio_lija,
                           p404=p404, costo_p404=costo_p404, cantidad_p404=cantidad_p404, precio_p404=precio_p404, mecanizado=mecanizado,
                           precio_mecanizado=precio_mecanizado, costo_mecanizado=costo_mecanizado, peon=peon, precio_mecanizado_peon=precio_mecanizado_peon,
                           costo_mecanizado_peon=costo_mecanizado_peon, fregadero=fregadero, valvula=valvula, colocacion=colocacion, desplazamiento=desplazamiento,
                           presupuesto=presupuesto_total, solid_costo_unitario=solid_costo_unitario, tipo_presupuesto=tipo_presupuesto,
                           costado=costado, costo_desplazamiento=costo_desplazamiento, tipo_canto=tipo_canto, medida_canto=medida_canto, metros_canto=metros_canto,
                           costo_canto=costo_canto, costo_pegamento_cantos=costo_pegamento_cantos, costo_lijas_cantos=costo_lijas_cantos, tipo_fregadero=tipo_fregadero, tipo=request.form.get('tipo'),
                           precio_solid_fregadero=precio_solid_fregadero, precio_solid_lavabo=precio_solid_lavabo, mecanizado_solid=mecanizado_solid, mano_obra_solid=mano_obra_solid, mano_obra_acero=mano_obra_acero,
                           copete=copete, fabricable=fabricable, entrepano=entrepano)

# Implementa la lógica de cálculo del presupuesto aquí
def calcular_presupuesto(
    tipo_presupuesto, 
    area_solid, 
    costo_pegamento, #+ costo_pegamento_cantos,
    lijas, 
    p404, 
    mecanizado, 
    peon, 
    fregadero,  # Campo de fregadero
    valvula, 
    colocacion, 
    costo_desplazamiento, 
    costado, 
    tipo_canto, 
    medida_canto, 
    metros_canto, 
    costo_canto, 
    costo_pegamento_cantos, 
    costo_lijas_cantos, 
    tipo_fregadero,  # Campo de tipo de fregadero
    precio_solid, 
    mecanizado_solid, 
    mano_obra_solid, 
    mano_obra_acero):    # Realiza los cálculos según los valores ingresados
    # Puedes usar if/else para distinguir entre "Isla" y "Encimera" y realizar los cálculos correspondientes
    #
    #krion= multiplicar ancho * largo y sumar todos y multiplicar 150€/m2
    #pegamento= 13€/tubo/3m
    #Lijas= 5€/m2
    #P404= 12€/tubo/3m
    #Fregadero= -->Comprar-->krion(modelos.pvp)
    #                        Valvula logo=60€
    #                        Mecanizado= 100€
    #                        Mano Obra = 150€
    #
    #              Acero -->acero.pvp
    #                       fresado=x€
    #                       pegado=x€
    #
    #Mecanizado= Maquina=80€/h
    #            Hombre=20€/h
    #
    #Cantos-->tipos-->hasta 2,4cm=40€       de 3cm a 6cm= 60€      de 8cm o más=70€   metro lineal/€
    #                 
    #
    #Tabla-->(Mano obra de lijado)= m2 krion * 35€m2
    #
    #Instalacion---->Desplazamiento
    #                Tiempo=20h/€ por persona
    
    precio_pegamento = 13.0
    precio_p404 = 12.0
    p_pegamento = (costo_pegamento * precio_pegamento) / 3
    p_p404 = (p404 * precio_p404) / 3    

    # Realiza otros cálculos según sea necesario
    # ...
    
    # Cálculos específicos para fregaderos y lavabos
    if tipo_fregadero == 'Fregadero':
        costo_fregadero = precio_solid
    elif tipo_fregadero == 'Lavabo':
        costo_fregadero = precio_solid
    else:
        costo_fregadero = 0.0


    if tipo_presupuesto == 'isla':
        otro_calculo = 0
    else:
        otro_calculo = 0
    
    # Calcular el presupuesto total
    presupuesto_total = (area_solid + costo_pegamento + costo_pegamento_cantos + lijas + p404 + mecanizado + peon + valvula +
                         colocacion + costo_desplazamiento + costado + metros_canto + costo_canto + costo_pegamento_cantos +
                         costo_lijas_cantos + mecanizado_solid + mano_obra_solid + mano_obra_acero + costo_fregadero)
    
    return presupuesto_total




if __name__ == "__main__":
    app.run()