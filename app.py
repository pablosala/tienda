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
import uuid
from datetime import datetime
from pytz import timezone
from sqlalchemy import func
import plotly.graph_objs as go
import plotly
import json


# Configurar la zona horaria de Madrid
madrid_tz = pytz.timezone('Europe/Madrid')


app = Flask(__name__)
app.config.from_object('config.Config')




app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
app.config['MODEL_UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'models')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'glb', 'stl'}
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
    apellidos = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), unique=True, nullable=False) 
    telefono = db.Column(db.String(20), nullable=False)  
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    is_confirmed = db.Column(db.Boolean, default=False)
    ordenes = db.relationship('Orden', backref='usuario', lazy=True)
    direcciones = db.relationship('Direccion', backref='usuario', lazy=True)
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
    precio_original = db.Column(db.Float, nullable=True)  # Campo para guardar el precio original
    descuento = db.Column(db.Integer, nullable=True, default=0)  # Campo para guardar el porcentaje de descuento
    fecha_fin_descuento = db.Column(db.DateTime, nullable=True)  # Campo para guardar la fecha y hora de fin del descuento
    stock = db.Column(db.Integer, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    modelo_3d = db.Column(db.String(255), nullable=True)
    ordenes = db.relationship('OrdenProducto', backref='producto', lazy=True)
    imagenes = db.relationship('Imagen', backref='producto', lazy=True, cascade="all, delete-orphan")
    valoraciones = db.relationship('Valoracion', backref='producto_valoraciones', lazy=True)
    especificaciones = db.relationship('Especificacion', backref='producto', lazy=True, cascade="all, delete-orphan")
    configuraciones_encimera = db.relationship('EncimeraConfiguracion', backref='producto', lazy=True, cascade="all, delete-orphan")
    configuraciones_lavabo = db.relationship('LavaboConfiguracion', backref='producto', lazy=True, cascade="all, delete-orphan")

    def verificar_descuento_expirado(self):
        madrid_tz = timezone('Europe/Madrid')
        now = datetime.now(madrid_tz)

        # Convertir self.fecha_fin_descuento a un datetime aware si no lo es
        if self.fecha_fin_descuento and self.fecha_fin_descuento.tzinfo is None:
            self.fecha_fin_descuento = madrid_tz.localize(self.fecha_fin_descuento)
        
        if self.fecha_fin_descuento and now > self.fecha_fin_descuento:
            self.precio = self.precio_original
            self.precio_original = None
            self.descuento = 0
            self.fecha_fin_descuento = None
            db.session.commit()


class Especificacion(db.Model):
    __tablename__ = 'especificacion'
    
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(255), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)


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
    metodo_pago = db.Column(db.String(50), nullable=False)
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
    ancho = db.Column(db.Float, nullable=True)
    largo = db.Column(db.Float, nullable=True)
    grosor = db.Column(db.Float, nullable=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material_encimera.id'), nullable=True)
    tipo_fregadero_id = db.Column(db.Integer, db.ForeignKey('tipo_fregadero.id'), nullable=True)
    tipo_lavabo_id = db.Column(db.Integer, db.ForeignKey('tipo_lavabo.id'), nullable=True)
    valvula_logo_id = db.Column(db.Integer, db.ForeignKey('valvula_logo.id'), nullable=True)
    agujero_grifo_id = db.Column(db.Integer, db.ForeignKey('agujero_grifo.id'), nullable=True)
    toalleros = db.relationship('Toallero', backref='orden_producto', lazy=True, cascade="all, delete-orphan")
    entrepanos = db.relationship('Entrepano', backref='orden_producto', lazy=True, cascade="all, delete-orphan")


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
    ancho = db.Column(db.Float, nullable=True)
    largo = db.Column(db.Float, nullable=True)
    grosor = db.Column(db.Float, nullable=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material_encimera.id'), nullable=True)
    tipo_fregadero_id = db.Column(db.Integer, db.ForeignKey('tipo_fregadero.id'), nullable=True)
    tipo_lavabo_id = db.Column(db.Integer, db.ForeignKey('tipo_lavabo.id'), nullable=True)
    valvula_logo_id = db.Column(db.Integer, db.ForeignKey('valvula_logo.id'), nullable=True)
    agujero_grifo_id = db.Column(db.Integer, db.ForeignKey('agujero_grifo.id'), nullable=True)
    
    # Relaciones con las tablas asociadas
    toalleros = db.relationship('Toallero', backref='carrito_item', lazy=True, cascade="all, delete-orphan")
    faldones = db.relationship('Faldon', backref='carrito_item', lazy=True, cascade="all, delete-orphan")
    entrepanos = db.relationship('Entrepano', backref='carrito_item', lazy=True, cascade="all, delete-orphan")
    
    # Relación con el producto
    producto = db.relationship('Producto', backref='carrito_items')


class Direccion(db.Model):
    __tablename__ = 'direccion'
    
    id = db.Column(db.Integer, primary_key=True)
    direccion = db.Column(db.String(200), nullable=False)
    ciudad = db.Column(db.String(100), nullable=False)
    provincia = db.Column(db.String(100), nullable=False)
    codigo_postal = db.Column(db.String(20), nullable=False)
    pais = db.Column(db.String(100), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    ordenes = db.relationship('Orden', backref='direccion_envio', lazy=True)


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


class MaterialEncimera(db.Model):
    __tablename__ = 'material_encimera'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    precio_por_m2 = db.Column(db.Float, nullable=False)
    configuraciones = db.relationship('EncimeraConfiguracion', backref='material', lazy=True)
    ordenes_producto = db.relationship('OrdenProducto', backref='material', lazy=True)


class TipoFregadero(db.Model):
    __tablename__ = 'tipo_fregadero'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    precio_adicional = db.Column(db.Float, nullable=False)
    ordenes_producto = db.relationship('OrdenProducto', backref='tipo_fregadero', lazy=True)


class EncimeraConfiguracion(db.Model):
    __tablename__ = 'encimera_configuracion'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material_encimera.id'), nullable=False)
    grosor = db.Column(db.Float, nullable=False)
    valvula_logo_id = db.Column(db.Integer, db.ForeignKey('valvula_logo.id'), nullable=True)
    agujero_grifo_id = db.Column(db.Integer, db.ForeignKey('agujero_grifo.id'), nullable=True)
    toalleros = db.relationship('Toallero', backref='encimera_configuracion', lazy=True, cascade="all, delete-orphan")
    faldones = db.relationship('Faldon', backref='encimera_configuracion', lazy=True, cascade="all, delete-orphan")
    entrepanos = db.relationship('Entrepano', backref='encimera_configuracion', lazy=True, cascade="all, delete-orphan")


class TipoLavabo(db.Model):
    __tablename__ = 'tipo_lavabo'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    precio_adicional = db.Column(db.Float, nullable=False)
    ordenes_producto = db.relationship('OrdenProducto', backref='tipo_lavabo', lazy=True)


class LavaboConfiguracion(db.Model):
    __tablename__ = 'lavabo_configuracion'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    largo = db.Column(db.Float, nullable=False)
    ancho = db.Column(db.Float, nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material_encimera.id'), nullable=False)  # Nueva relación
    tipo_lavabo_id = db.Column(db.Integer, db.ForeignKey('tipo_lavabo.id'), nullable=False)
    valvula_logo_id = db.Column(db.Integer, db.ForeignKey('valvula_logo.id'), nullable=True)
    agujero_grifo_id = db.Column(db.Integer, db.ForeignKey('agujero_grifo.id'), nullable=True)
    toalleros = db.relationship('Toallero', backref='lavabo_configuracion', lazy=True, cascade="all, delete-orphan")
    faldones = db.relationship('Faldon', backref='lavabo_configuracion', lazy=True, cascade="all, delete-orphan")
    material = db.relationship('MaterialEncimera', backref='lavabo_configuraciones', lazy=True)  # Relación con MaterialEncimera



class ValvulaLogo(db.Model):
    __tablename__ = 'valvula_logo'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    precio_adicional = db.Column(db.Float, nullable=False)
    encimera_configuraciones = db.relationship('EncimeraConfiguracion', backref='valvula_logo', lazy=True)
    lavabo_configuraciones = db.relationship('LavaboConfiguracion', backref='valvula_logo', lazy=True)


class AgujeroGrifo(db.Model):
    __tablename__ = 'agujero_grifo'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    precio_adicional = db.Column(db.Float, nullable=False)
    encimera_configuraciones = db.relationship('EncimeraConfiguracion', backref='agujero_grifo', lazy=True)
    lavabo_configuraciones = db.relationship('LavaboConfiguracion', backref='agujero_grifo', lazy=True)


class Toallero(db.Model):
    __tablename__ = 'toallero'
    id = db.Column(db.Integer, primary_key=True)
    posicion = db.Column(db.Enum('FRONTAL', 'LATERAL_DERECHO', 'LATERAL_IZQUIERDO'), nullable=False)
    precio_adicional = db.Column(db.Float, nullable=False)
    encimera_id = db.Column(db.Integer, db.ForeignKey('encimera_configuracion.id'), nullable=True)
    lavabo_id = db.Column(db.Integer, db.ForeignKey('lavabo_configuracion.id'), nullable=True)
    orden_producto_id = db.Column(db.Integer, db.ForeignKey('orden_producto.orden_id'), nullable=True)
    carrito_item_id = db.Column(db.Integer, db.ForeignKey('carrito_item.id'), nullable=True)


class Faldon(db.Model):
    __tablename__ = 'faldon'
    id = db.Column(db.Integer, primary_key=True)
    posicion = db.Column(db.Enum('FRONTAL', 'TRASERO', 'IZQUIERDO', 'DERECHO'), nullable=False)
    medida = db.Column(db.Float, nullable=False)
    precio_adicional = db.Column(db.Float, nullable=False)
    encimera_id = db.Column(db.Integer, db.ForeignKey('encimera_configuracion.id'), nullable=True)
    lavabo_id = db.Column(db.Integer, db.ForeignKey('lavabo_configuracion.id'), nullable=True)
    carrito_item_id = db.Column(db.Integer, db.ForeignKey('carrito_item.id'), nullable=True)


class Entrepano(db.Model):
    __tablename__ = 'entrepano'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Enum('RECTO', 'SANITARIO'), nullable=False)
    medida = db.Column(db.Float, nullable=False)
    precio_adicional = db.Column(db.Float, nullable=False)
    encimera_id = db.Column(db.Integer, db.ForeignKey('encimera_configuracion.id'), nullable=True)
    orden_producto_id = db.Column(db.Integer, db.ForeignKey('orden_producto.orden_id'), nullable=True)
    carrito_item_id = db.Column(db.Integer, db.ForeignKey('carrito_item.id'), nullable=True)


class Personalizacion(db.Model):
    __tablename__ = 'personalizacion'
    id = db.Column(db.Integer, primary_key=True)
    carrito_item_id = db.Column(db.Integer, db.ForeignKey('carrito_item.id'), nullable=False)
    largo = db.Column(db.Float, nullable=False)
    ancho = db.Column(db.Float, nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material_encimera.id'), nullable=False)
    precio_personalizado = db.Column(db.Float, nullable=False)

    # Relación con el carrito item
    carrito_item = db.relationship('CarritoItem', backref=db.backref('personalizaciones', uselist=True, cascade="all, delete-orphan"))


def obtener_fecha_madrid():
    madrid = timezone('Europe/Madrid')
    return datetime.now(madrid)


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
        
        # Primero, buscar en la tabla 'usuario'
        user = Usuario.query.filter_by(email=email).first()
        
        if user:
            # Verificar la contraseña en 'usuario'
            if not user.check_password(password):
                flash('Correo electrónico o contraseña incorrectos.', 'danger')
                return redirect(url_for('login'))
            
            # Verificar si el usuario ha confirmado su correo
            if not user.is_confirmed:
                flash('No has confirmado tu correo electrónico. Por favor, revisa tu bandeja de entrada o la carpeta de spam.', 'warning')
                return render_template('resend_confirmation.html', email=email)
            
            # Iniciar sesión si las credenciales son correctas y el correo está confirmado
            login_user(user)
            return redirect(url_for('index'))
        
        else:
            # Si no se encuentra en 'usuario', buscar en 'temp_usuario'
            temp_user = TempUsuario.query.filter_by(email=email).first()
            
            if temp_user:
                # Verificar la contraseña en 'temp_usuario'
                if temp_user.check_password(password):
                    flash('No has confirmado tu correo electrónico. Por favor, revisa tu bandeja de entrada o la carpeta de spam.', 'warning')
                    return render_template('resend_confirmation.html', email=email)
                else:
                    flash('Correo electrónico o contraseña incorrectos.', 'danger')
                    return redirect(url_for('login'))
            
            # Si no se encuentra en ninguna tabla
            flash('Correo electrónico o contraseña incorrectos.', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
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

@app.route('/model')
def model():
    return render_template('model.html')

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
    
    return render_template('detalles_cuenta.html', title='Detalles de la cuenta', user=current_user, ordenes=ordenes, direcciones=direcciones)


@app.route('/direccion/nueva', methods=['GET', 'POST'])
@login_required
def nueva_direccion():
    if request.method == 'POST':
        direccion = request.form['direccion']
        ciudad = request.form['ciudad']
        provincia = request.form['provincia']
        codigo_postal = request.form['codigo_postal']
        pais = request.form['pais']
        nueva_direccion = Direccion(direccion=direccion, ciudad=ciudad, provincia=provincia, codigo_postal=codigo_postal, pais=pais, usuario_id=current_user.id)
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

@app.template_filter('round2')
def round2(value):
    """Redondea un número a 2 decimales."""
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return value

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
        # Recoger y validar los nuevos campos del usuario
        nombre = request.form.get('nombre')
        apellidos = request.form.get('apellidos')
        dni = request.form.get('dni')
        telefono = request.form.get('telefono')

        if not all([nombre, apellidos, dni, telefono]):
            flash('Por favor, complete todos los campos personales.', 'danger')
            return redirect(url_for('checkout'))

        # Actualizar la información del usuario
        current_user.nombre = nombre
        current_user.apellidos = apellidos
        current_user.dni = dni
        current_user.telefono = telefono
        db.session.commit()

        direccion_envio_id = request.form.get('direccion_envio')
        metodo_pago = request.form.get('metodo_pago')
        tipo_entrega = request.form.get('tipo_entrega')  # Recoger en almacén o Envío

        # Validar si se selecciona una dirección existente o se crea una nueva (para envío)
        if tipo_entrega == 'envio':
            if direccion_envio_id == 'nueva':
                nueva_direccion = Direccion(
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
                db.session.commit()  # Confirmar la nueva dirección en la base de datos
            elif not direccion_envio_id or not Direccion.query.filter_by(id=direccion_envio_id, usuario_id=usuario_id).first():
                flash('Por favor seleccione una dirección válida o añada una nueva.', 'danger')
                return redirect(url_for('checkout'))

        if not metodo_pago:
            flash('Por favor seleccione un método de pago.', 'danger')
            return redirect(url_for('checkout'))

        # Calcular el total del pedido
        total_pedido = 0
        for item in carrito.items:
            if item.personalizaciones:
                # Si el producto tiene personalización, usa el precio personalizado
                total_pedido += sum(p.precio_personalizado for p in item.personalizaciones) * item.cantidad
            else:
                # Si no, usa el precio estándar del producto
                total_pedido += item.cantidad * item.producto.precio

        # Redondear el total a 2 decimales
        total_pedido = round(total_pedido, 2)

        # Calcular los gastos de envío si corresponde
        gastos_envio = 0
        if tipo_entrega == 'envio':
            gastos_envio = 5.99  # Ejemplo de tarifa fija de envío

        # Calcular el total a pagar
        total_a_pagar = total_pedido + gastos_envio

        # Redirigir a la pasarela de pago de Redsys
        order_id = f'{uuid.uuid4().hex[:6]}'  # Generar un identificador único para la orden

        # Preparar los datos para la petición al TPV
        merchant_parameters = {
            'DS_MERCHANT_AMOUNT': str(int(float(total_a_pagar) * 100)),
            'DS_MERCHANT_ORDER': order_id,
            'DS_MERCHANT_MERCHANTCODE': app.config['TPV_MERCHANT_CODE'],
            'DS_MERCHANT_CURRENCY': app.config['TPV_CURRENCY'],
            'DS_MERCHANT_TRANSACTIONTYPE': app.config['TPV_TRANSACTION_TYPE'],
            'DS_MERCHANT_TERMINAL': app.config['TPV_TERMINAL'],
            'DS_MERCHANT_MERCHANTURL': app.config['TPV_CALLBACK_URL'],
            'DS_MERCHANT_URLOK': url_for('callback_ok', _external=True),
            'DS_MERCHANT_URLKO': url_for('callback_ko', _external=True)
        }

        merchant_parameters_base64 = base64.b64encode(json.dumps(merchant_parameters).encode('utf-8')).decode('utf-8')
        key = encrypt_3DES(order_id, app.config['TPV_SECRET_KEY'])
        signature = calculate_hmac(key, merchant_parameters_base64)

        # Guardar datos temporales en la sesión
        session['order_data'] = {
            'usuario_id': usuario_id,
            'direccion_envio_id': direccion_envio_id,
            'metodo_pago': metodo_pago,
            'total': total_a_pagar,  # Se usa el total a pagar con los gastos de envío incluidos
            'order_id': order_id,
            'tipo_entrega': tipo_entrega
        }

        return render_template('tpv_form.html', merchant_parameters=merchant_parameters_base64, signature=signature)

    # Cargar las personalizaciones y sus relaciones asociadas
    carrito_items = CarritoItem.query.filter_by(carrito_id=carrito.id).all()
    for item in carrito_items:
        # Cargar las relaciones que se necesitan en la plantilla
        item.material = MaterialEncimera.query.get(item.material_id)
        item.tipo_lavabo = TipoLavabo.query.get(item.tipo_lavabo_id)
        item.valvula_logo = ValvulaLogo.query.get(item.valvula_logo_id)
        item.agujero_grifo = AgujeroGrifo.query.get(item.agujero_grifo_id)
        item.toalleros = Toallero.query.filter_by(carrito_item_id=item.id).all()
        item.faldones = Faldon.query.filter_by(carrito_item_id=item.id).all()

        for personalizacion in item.personalizaciones:
            personalizacion.material = MaterialEncimera.query.get(personalizacion.material_id)

    direcciones = Direccion.query.filter_by(usuario_id=usuario_id).all()

    total_pedido = 0
    for item in carrito_items:
        if item.personalizaciones:
            total_pedido += sum(p.precio_personalizado for p in item.personalizaciones) * item.cantidad
        else:
            total_pedido += item.cantidad * item.producto.precio

    gastos_envio = 5.99  # Tarifa fija de envío (por defecto, esto podría cambiar según el cálculo dinámico)
    total_a_pagar = total_pedido + gastos_envio

    return render_template('checkout.html', title='Finalizar Compra', carrito_items=carrito_items, direcciones=direcciones, user=current_user, total_pedido=total_pedido, gastos_envio=gastos_envio, total_a_pagar=total_a_pagar)

@app.route('/callback_ok', methods=['GET','POST'])
@login_required
def callback_ok():
    order_data = session.get('order_data')
    if not order_data:
        flash('Error en la confirmación del pago.', 'danger')
        return redirect(url_for('index'))

    usuario_id = order_data['usuario_id']
    direccion_envio_id = order_data['direccion_envio_id']
    metodo_pago = order_data['metodo_pago']
    total_pedido = order_data['total']

    # Crear un nuevo pedido
    pedido = Orden(
        usuario_id=usuario_id,
        direccion_envio_id=direccion_envio_id,
        metodo_pago=metodo_pago,
        total=total_pedido,
        status='Confirmed'
    )
    db.session.add(pedido)
    db.session.commit()

    carrito = Carrito.query.filter_by(usuario_id=usuario_id).first()

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

    # Vaciar el carrito del usuario
    carrito.items = []
    db.session.commit()

    usuario = Usuario.query.get(usuario_id)
    enviar_correo_pedido(usuario.email, pedido)

    flash('Pedido realizado con éxito.', 'success')
    return redirect(url_for('detalles_cuenta'))

@app.route('/callback_ko', methods=['GET','POST'])
@login_required
def callback_ko():
    flash('El pago no ha sido completado. Inténtelo nuevamente.', 'danger')
    return redirect(url_for('checkout'))


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


from datetime import datetime
from pytz import timezone

@app.route('/producto/<int:producto_id>', methods=['GET', 'POST'])
def producto_detalle(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    # Convertir datetime.now() a un objeto datetime aware
    madrid_tz = timezone('Europe/Madrid')
    now = datetime.now(madrid_tz)
    
    # Convertir fecha_fin_descuento a un datetime aware si no lo es
    if producto.fecha_fin_descuento and producto.fecha_fin_descuento.tzinfo is None:
        producto.fecha_fin_descuento = madrid_tz.localize(producto.fecha_fin_descuento)
    
    # Verificar si el descuento ha expirado
    if producto.fecha_fin_descuento and now > producto.fecha_fin_descuento:
        producto.precio = producto.precio_original
        producto.precio_original = None
        producto.descuento = 0
        producto.fecha_fin_descuento = None
        db.session.commit()  # Guardar cambios en la base de datos
    
    ha_comprado = []
    if current_user.is_authenticated:
        ha_comprado = Orden.query.filter_by(usuario_id=current_user.id).join(OrdenProducto).filter_by(producto_id=producto_id).all()

    especificaciones = Especificacion.query.filter_by(producto_id=producto_id).all()

    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Debes iniciar sesión para dejar una valoración.', 'danger')
            return redirect(url_for('login'))

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

    # Obtener los datos relacionados necesarios para la configuración dinámica de precios
    materiales = MaterialEncimera.query.all()
    tipos_lavabo = TipoLavabo.query.all()
    tipos_fregadero = TipoFregadero.query.all()
    valvula_logo = ValvulaLogo.query.all()
    agujero_grifo = AgujeroGrifo.query.all()
    toalleros = Toallero.query.all()
    faldon_precio = Faldon.query.all()
    tipos_entrepano = Entrepano.query.all()
    lavabo_configuracion = LavaboConfiguracion.query.filter_by(producto_id=producto_id).first()
    encimera_configuracion = EncimeraConfiguracion.query.filter_by(producto_id=producto_id).first()

    return render_template(
        'single.html', 
        producto=producto, 
        ha_comprado=ha_comprado, 
        especificaciones=especificaciones, 
        materiales=materiales, 
        tipos_lavabo=tipos_lavabo, 
        tipos_fregadero=tipos_fregadero,
        valvula_logo=valvula_logo,
        agujero_grifo=agujero_grifo,
        toalleros=toalleros,
        faldon_precio=faldon_precio,
        tipos_entrepano=tipos_entrepano,
        lavabo_configuracion=lavabo_configuracion,
        encimera_configuracion=encimera_configuracion
    )


@app.route('/agregar_carrito/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def agregar_carrito(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    # Establecer la cantidad en 1 si no se especifica en el formulario
    cantidad = int(request.form.get('cantidad', 1))

    # Recoger los datos del formulario
    largo = request.form.get('largo_lavabo')
    ancho = request.form.get('ancho_lavabo')
    material_id = request.form.get('material_id_lavabo')
    tipo_lavabo_id = request.form.get('tipo_lavabo_id')
    medida_faldon = request.form.get('medida_faldon_lavabo')
    lados_faldon = request.form.getlist('faldon_lados_lavabo[]')
    
    toallero_id = request.form.get('toallero_lavabo')
    valvula_id = request.form.get('valvula_logo_id')
    agujero_grifo_id = request.form.get('agujero_grifo_id')

    # Verificar si el producto es personalizado
    es_personalizado = bool(largo and ancho and material_id)

    carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if not carrito:
        carrito = Carrito(usuario_id=current_user.id)
        db.session.add(carrito)
        db.session.commit()

    if es_personalizado:
        # Convertir los valores del formulario a sus tipos correspondientes
        largo = float(largo) if largo else 0.0
        ancho = float(ancho) if ancho else 0.0
        material_id = int(material_id) if material_id else None
        tipo_lavabo_id = int(tipo_lavabo_id) if tipo_lavabo_id else None
        medida_faldon = float(medida_faldon) if medida_faldon else 0.0
        toallero_id = int(toallero_id) if toallero_id else None
        valvula_id = int(valvula_id) if valvula_id else None
        agujero_grifo_id = int(agujero_grifo_id) if agujero_grifo_id else None

        # Obtener los objetos relacionados
        material = MaterialEncimera.query.get(material_id) if material_id else None
        tipo_lavabo = TipoLavabo.query.get(tipo_lavabo_id) if tipo_lavabo_id else None
        toallero = Toallero.query.get(toallero_id) if toallero_id else None
        valvula = ValvulaLogo.query.get(valvula_id) if valvula_id else None
        agujero_grifo = AgujeroGrifo.query.get(agujero_grifo_id) if agujero_grifo_id else None

        # Calcular el precio personalizado
        precio_personalizado = 0

        # Sumar el precio adicional del tipo de lavabo
        if tipo_lavabo:
            precio_personalizado += tipo_lavabo.precio_adicional

        # Agregar el costo del material (largo * ancho * precio_m2)
        if material:
            precio_personalizado += largo * ancho * material.precio_por_m2 / 1000000

        # Calcular el precio del faldón y sumarlo al precio personalizado
        if medida_faldon > 0 and lados_faldon:
            # Precio por los lados izquierdo y derecho
            for lado in lados_faldon:
                if lado in ['IZQUIERDO', 'DERECHO']:
                    precio_faldon_lados = ancho * medida_faldon * material.precio_por_m2 / 1000000
                    precio_personalizado += precio_faldon_lados
                
            # Precio por el lado frontal
            if 'FRONTAL' in lados_faldon:
                precio_faldon_frontal = largo * medida_faldon * material.precio_por_m2 / 1000000
                precio_personalizado += precio_faldon_frontal

        # Sumar el precio del toallero seleccionado
        if toallero:
            precio_personalizado += toallero.precio_adicional

        # Sumar el precio de la válvula seleccionada
        if valvula:
            precio_personalizado += valvula.precio_adicional

        # Sumar el precio del agujero de grifo seleccionado
        if agujero_grifo:
            precio_personalizado += agujero_grifo.precio_adicional

        # Verificar si ya existe un item con la misma personalización en el carrito
        item = CarritoItem.query.filter_by(
            carrito_id=carrito.id,
            producto_id=producto_id,
            largo=largo,
            ancho=ancho,
            material_id=material_id,
            tipo_lavabo_id=tipo_lavabo_id,
            valvula_logo_id=valvula_id,
            agujero_grifo_id=agujero_grifo_id,
        ).first()

        if item:
            # Si la personalización es la misma, incrementar la cantidad
            if item.cantidad + cantidad > producto.stock:
                flash(f'Ya has añadido la cantidad máxima disponible de {producto.nombre}.', 'danger')
                return redirect(request.referrer)
            item.cantidad += cantidad
        else:
            # Crear un nuevo item con personalización si no existe
            if cantidad > producto.stock:
                flash(f'No hay suficiente stock disponible para {producto.nombre}.', 'danger')
                return redirect(request.referrer)

            item = CarritoItem(
                carrito_id=carrito.id,
                producto_id=producto_id,
                cantidad=cantidad,
                largo=largo,
                ancho=ancho,
                material_id=material_id,
                tipo_lavabo_id=tipo_lavabo_id,
                valvula_logo_id=valvula_id,
                agujero_grifo_id=agujero_grifo_id
            )
            db.session.add(item)
            db.session.commit()

            # Crear la personalización asociada
            nueva_personalizacion = Personalizacion(
                carrito_item_id=item.id,
                largo=largo,
                ancho=ancho,
                material_id=material_id,
                precio_personalizado=precio_personalizado
            )
            db.session.add(nueva_personalizacion)

            # Crear y asociar los faldones seleccionados
            if lados_faldon and medida_faldon > 0:
                for lado in lados_faldon:
                    faldon = Faldon(
                        carrito_item_id=item.id,
                        posicion=lado,
                        medida=medida_faldon,
                        precio_adicional=(ancho * medida_faldon if lado in ['izquierda', 'derecha'] else largo * medida_faldon) * material.precio_por_m2 / 1000000
                    )
                    db.session.add(faldon)

        db.session.commit()

    else:
        # Producto normal (sin personalización)
        item = CarritoItem.query.filter_by(carrito_id=carrito.id, producto_id=producto_id, material_id=None).first()
        if item:
            # Si ya existe el producto en el carrito, incrementar la cantidad
            if item.cantidad + cantidad > producto.stock:
                flash(f'Ya has añadido la cantidad máxima disponible de {producto.nombre}.', 'danger')
                return redirect(request.referrer)
            item.cantidad += cantidad
        else:
            # Si no existe el producto en el carrito, agregarlo
            if cantidad > producto.stock:
                flash(f'No hay suficiente stock disponible para {producto.nombre}.', 'danger')
                return redirect(request.referrer)

            item = CarritoItem(
                carrito_id=carrito.id,
                producto_id=producto_id,
                cantidad=cantidad
            )
            db.session.add(item)

    db.session.commit()
    flash(f'{producto.nombre} agregado al carrito', 'success')

    return redirect(request.referrer)





@app.route('/carrito')
@login_required
def carrito():
    carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
    items = carrito.items if carrito else []

    total = 0
    for item in items:
        if item.personalizaciones:
            # Sumar los precios personalizados para los productos personalizados
            for personalizacion in item.personalizaciones:
                total += item.cantidad * personalizacion.precio_personalizado
        else:
            # Sumar el precio normal para los productos sin personalización
            total += item.cantidad * item.producto.precio

    # Redondear el total a 2 decimales
    total = round(total, 2)

    hay_agotados = any(item.producto.stock <= 0 or item.cantidad > item.producto.stock for item in items)
    
    return render_template('carrito.html', items=items, total=total, hay_agotados=hay_agotados)






@app.route('/carrito/actualizar', methods=['POST'])
@login_required
def actualizar_carrito():
    carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if carrito:
        for item in carrito.items:
            producto_id = item.producto.id
            nueva_cantidad = request.form.get(f'cantidad_{producto_id}')
            if nueva_cantidad:
                nueva_cantidad = int(nueva_cantidad)
                
                # Validar stock y cantidad
                if nueva_cantidad > item.producto.stock:
                    flash(f'No puedes añadir más de {item.producto.stock} unidades de {item.producto.nombre}.', 'danger')
                elif nueva_cantidad <= 0:
                    db.session.delete(item)  # Eliminar el item si la cantidad es cero o menor
                else:
                    item.cantidad = nueva_cantidad

                    # Si hay personalizaciones, calcular el subtotal correctamente
                    if item.personalizaciones:
                        for personalizacion in item.personalizaciones:
                            # Mantener el precio unitario de la personalización y recalcular subtotal
                            subtotal_personalizado = personalizacion.precio_personalizado * item.cantidad
                            # Aquí puedes almacenar el subtotal si es necesario o solo calcularlo en la vista
                            # Si tienes que guardarlo en base de datos, puedes usar un campo para "subtotal_personalizado"
                            print(f"Subtotal personalizado para {item.producto.nombre}: {subtotal_personalizado}")
                    else:
                        # Si no tiene personalizaciones, el subtotal es solo la cantidad * precio del producto
                        subtotal = item.cantidad * item.producto.precio
                        print(f"Subtotal para {item.producto.nombre}: {subtotal}")

        # Confirmar los cambios en la base de datos
        db.session.commit()
        flash('Carrito actualizado con éxito', 'success')
    else:
        flash('No se encontró el carrito.', 'danger')
    return redirect(url_for('carrito'))





@app.route('/carrito/eliminar', methods=['POST'])
@login_required
def eliminar_del_carrito():
    producto_id = request.form.get('producto_id')
    carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if carrito:
        item = CarritoItem.query.filter_by(carrito_id=carrito.id, producto_id=producto_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            flash('Producto eliminado del carrito.', 'success')
        else:
            flash('El producto no se encontró en el carrito.', 'danger')
    else:
        flash('No se encontró el carrito.', 'danger')
    return redirect(url_for('carrito'))




@app.route('/realizar_pedido', methods=['POST'])
@login_required
def realizar_pedido():
    carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if not carrito or not carrito.items:
        flash('El carrito está vacío', 'danger')
        return redirect(url_for('index'))

    productos_agotados = [item.producto.nombre for item in carrito.items if item.producto.stock <= 0]
    if productos_agotados:
        flash(f'No puedes realizar el pedido. Los siguientes productos están agotados: {", ".join(productos_agotados)}.', 'danger')
        return redirect(url_for('carrito'))

    total = sum(item.cantidad * item.producto.precio for item in carrito.items)
    orden = Orden(usuario_id=current_user.id, total=total)
    db.session.add(orden)
    db.session.commit()

    for item in carrito.items:
        producto = Producto.query.get(item.producto_id)
        if producto.stock < item.cantidad:
            flash(f'No hay suficiente stock disponible para {producto.nombre}.', 'danger')
            return redirect(url_for('carrito'))
        producto.stock -= item.cantidad
        db.session.commit()

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
    # Total de Ventas
    total_ventas = db.session.query(func.sum(Orden.total)).scalar() or 0

    # Número de Clientes
    total_clientes = db.session.query(func.count(Usuario.id)).scalar()

    # Productos más vendidos
    mas_vendidos = db.session.query(
        Producto.nombre, 
        func.sum(OrdenProducto.cantidad).label('total_vendido')
    ).join(OrdenProducto.producto).group_by(Producto.id).order_by(func.sum(OrdenProducto.cantidad).desc()).limit(5).all()

    # Productos menos vendidos
    menos_vendidos = db.session.query(
        Producto.nombre, 
        func.sum(OrdenProducto.cantidad).label('total_vendido')
    ).join(OrdenProducto.producto).group_by(Producto.id).order_by(func.sum(OrdenProducto.cantidad)).limit(5).all()

    # Productos más vistos (esto dependerá de cómo almacenes las visitas)
    mas_vistos = db.session.query(
        Producto.nombre,
        func.count().label('total_vistos')
    ).group_by(Producto.id).order_by(func.count().desc()).limit(5).all()

    # Agrupar y sumar ventas por mes utilizando MySQL DATE_FORMAT
    ventas_por_mes = db.session.query(
        func.DATE_FORMAT(Orden.fecha, '%Y-%m').label('mes'),
        func.sum(Orden.total).label('total')
    ).group_by('mes').order_by('mes').all()

    # Generación de gráficos
    graficas = generar_graficas(mas_vendidos, menos_vendidos, ventas_por_mes, mas_vistos)

    return render_template(
        'admin_dashboard.html', 
        total_ventas=total_ventas,
        total_clientes=total_clientes,
        mas_vendidos=mas_vendidos,
        menos_vendidos=menos_vendidos,
        mas_vistos=mas_vistos,
        graficas=graficas
    )

def generar_graficas(mas_vendidos, menos_vendidos, ventas_por_mes, mas_vistos):
    # Gráfica de Productos Más Vendidos
    productos = [producto[0] for producto in mas_vendidos]
    ventas = [producto[1] for producto in mas_vendidos]
    fig_mas_vendidos = go.Figure([go.Bar(x=productos, y=ventas)])
    fig_mas_vendidos.update_layout(title='Productos Más Vendidos')

    # Gráfica de Productos Menos Vendidos
    productos = [producto[0] for producto in menos_vendidos]
    ventas = [producto[1] for producto in menos_vendidos]
    fig_menos_vendidos = go.Figure([go.Bar(x=productos, y=ventas)])
    fig_menos_vendidos.update_layout(title='Productos Menos Vendidos')

    # Gráfica de Evolución de Ventas
    meses = [venta[0] for venta in ventas_por_mes]
    total_ventas = [venta[1] for venta in ventas_por_mes]
    fig_ventas_mes = go.Figure([go.Scatter(x=meses, y=total_ventas, mode='lines+markers')])
    fig_ventas_mes.update_layout(title='Evolución de Ventas por Mes')

    # Gráfica de Productos Más Vistos
    productos = [producto[0] for producto in mas_vistos]
    vistos = [producto[1] for producto in mas_vistos]
    fig_mas_vistos = go.Figure([go.Bar(x=productos, y=vistos)])
    fig_mas_vistos.update_layout(title='Productos Más Vistos')

    # Convertir las gráficas a JSON para renderizar en el template
    graficas = {
        'mas_vendidos': json.dumps(fig_mas_vendidos, cls=plotly.utils.PlotlyJSONEncoder),
        'menos_vendidos': json.dumps(fig_menos_vendidos, cls=plotly.utils.PlotlyJSONEncoder),
        'ventas_mes': json.dumps(fig_ventas_mes, cls=plotly.utils.PlotlyJSONEncoder),
        'mas_vistos': json.dumps(fig_mas_vistos, cls=plotly.utils.PlotlyJSONEncoder),
    }

    return graficas

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
        # Capturar los datos principales del producto
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        stock = int(request.form['stock'])
        categoria_id = int(request.form['categoria_id'])
        especificaciones = request.form.getlist('especificaciones')

        # Crear el objeto Producto
        producto = Producto(
            nombre=nombre, 
            descripcion=descripcion, 
            precio=precio, 
            stock=stock, 
            categoria_id=categoria_id
        )
        db.session.add(producto)
        db.session.commit()

        # Guardar las especificaciones
        for especificacion in especificaciones:
            nueva_especificacion = Especificacion(descripcion=especificacion, producto_id=producto.id)
            db.session.add(nueva_especificacion)

        # Guardar la imagen
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen = Imagen(url=filename, producto_id=producto.id)
                db.session.add(imagen)

        # Guardar el modelo 3D
        if 'modelo_3d' in request.files:
            modelo_file = request.files['modelo_3d']
            if modelo_file.filename != '' and allowed_file(modelo_file.filename):
                modelo_filename = secure_filename(modelo_file.filename)
                modelo_file.save(os.path.join(app.config['MODEL_UPLOAD_FOLDER'], modelo_filename))
                producto.modelo_3d = modelo_filename

        # Manejar descuento
        descuento = request.form.get('descuento')
        if descuento and int(descuento) > 0:
            producto.descuento = int(descuento)
            producto.precio_original = precio
            producto.precio = precio * (1 - (producto.descuento / 100))

            # Establecer la fecha de fin de descuento
            fecha_fin_descuento_str = request.form.get('fecha_fin_descuento')
            if fecha_fin_descuento_str:
                madrid = timezone('Europe/Madrid')
                fecha_fin_descuento = datetime.strptime(fecha_fin_descuento_str, '%Y-%m-%dT%H:%M')
                producto.fecha_fin_descuento = madrid.localize(fecha_fin_descuento)
        else:
            producto.descuento = 0
            producto.precio_original = None
            producto.fecha_fin_descuento = None

        db.session.commit()

        # Manejar configuraciones de encimera o lavabo según el tipo de producto
        tipo_producto = request.form.get('tipo_producto')

        if tipo_producto == 'encimera':
            # Crear configuración de encimera
            material_id = int(request.form['material_id'])
            grosor = float(request.form['grosor']) if request.form['grosor'] else 0

            configuracion_encimera = EncimeraConfiguracion(
                producto_id=producto.id,
                material_id=material_id,
                grosor=grosor
            )
            db.session.add(configuracion_encimera)
            db.session.commit()

            # Agregar válvula con logo
            if 'valvula_logo_id' in request.form:
                valvula_logo_id = int(request.form['valvula_logo_id'])
                valvula_logo = ValvulaLogo.query.get(valvula_logo_id)
                configuracion_encimera.valvula_logo_id = valvula_logo.id

            # Agregar agujero para grifo
            if 'agujero_grifo_id' in request.form:
                agujero_grifo_id = int(request.form['agujero_grifo_id'])
                configuracion_encimera.agujero_grifo_id = agujero_grifo_id

            # Agregar toalleros
            toalleros_ids = request.form.getlist('toallero_ids')
            for toallero_id in toalleros_ids:
                toallero = Toallero.query.get(int(toallero_id))
                toallero.encimera_id = configuracion_encimera.id
                db.session.add(toallero)

            # Agregar faldones
            faldones_ids = request.form.getlist('faldon_ids')
            for faldon_id in faldones_ids:
                faldon = Faldon.query.get(int(faldon_id))
                faldon.encimera_id = configuracion_encimera.id
                db.session.add(faldon)

            # Agregar entrepaños
            entrepanos_ids = request.form.getlist('entrepano_ids')
            for entrepano_id in entrepanos_ids:
                entrepano = Entrepano.query.get(int(entrepano_id))
                entrepano.encimera_id = configuracion_encimera.id
                db.session.add(entrepano)

        elif tipo_producto == 'lavabo':
            # Crear la configuración del lavabo
            tipo_lavabo_id = int(request.form['tipo_lavabo_id'])
            material_id_lavabo = int(request.form['material_id_lavabo'])
            largo_lavabo = float(request.form['largo_lavabo'])
            ancho_lavabo = float(request.form['ancho_lavabo'])

            configuracion_lavabo = LavaboConfiguracion(
                producto_id=producto.id,
                tipo_lavabo_id=tipo_lavabo_id,
                material_id=material_id_lavabo,
                largo=largo_lavabo,
                ancho=ancho_lavabo
            )
            db.session.add(configuracion_lavabo)
            db.session.commit()

            # Agregar válvula con logo solo si se selecciona algo válido
            if 'valvula_logo_id' in request.form and request.form['valvula_logo_id']:
                try:
                    valvula_logo_id = int(request.form['valvula_logo_id_lavabo'])
                    configuracion_lavabo.valvula_logo_id = valvula_logo_id
                except ValueError:
                    configuracion_lavabo.valvula_logo_id = None
            else:
                configuracion_lavabo.valvula_logo_id = None  # No se seleccionó válvula

            # Agregar agujero para grifo solo si se selecciona algo válido
            if 'agujero_grifo_id' in request.form and request.form['agujero_grifo_id']:
                try:
                    agujero_grifo_id = int(request.form['agujero_grifo_id_lavabo'])
                    configuracion_lavabo.agujero_grifo_id = agujero_grifo_id
                except ValueError:
                    configuracion_lavabo.agujero_grifo_id = None
            else:
                configuracion_lavabo.agujero_grifo_id = None  # No se seleccionó agujero de grifo

            db.session.commit()

            # Agregar toalleros
            toallero_lavabo = request.form.getlist('toallero_lavabo')
            for toallero_id in toallero_lavabo:
                toallero = Toallero.query.get(int(toallero_id))
                toallero.lavabo_id = configuracion_lavabo.id
                db.session.add(toallero)

            # Cálculo del precio adicional de faldón
            if 'faldon_lavabo' in request.form:
                lados_faldon = request.form.getlist('faldon_lados_lavabo[]')
                medida_faldon = float(request.form['medida_faldon_lavabo'])

                if medida_faldon > 0 and lados_faldon:
                    # Obtener el precio del material
                    material = MaterialEncimera.query.get(material_id_lavabo)
                    precio_faldon_total = 0

                    # Precio por los lados izquierdo y derecho
                    for lado in lados_faldon:
                        if lado in ['IZQUIERDO', 'DERECHO']:
                            precio_faldon_lados = ancho_lavabo * medida_faldon * material.precio_por_m2 / 1000000
                            precio_faldon_total += precio_faldon_lados

                    # Precio por el lado frontal
                    if 'FRONTAL' in lados_faldon:
                        precio_faldon_frontal = largo_lavabo * medida_faldon * material.precio_por_m2 / 1000000
                        precio_faldon_total += precio_faldon_frontal

                    # Guardar los faldones en la base de datos
                    for lado_faldon in lados_faldon:
                        nuevo_faldon = Faldon(
                            posicion=lado_faldon,
                            medida=medida_faldon,
                            precio_adicional=precio_faldon_total,
                            lavabo_id=configuracion_lavabo.id
                        )
                        db.session.add(nuevo_faldon)

        db.session.commit()

        flash('Producto agregado con éxito', 'success')
        return redirect(url_for('admin_products'))

    # Renderizar el formulario para agregar el producto
    categorias = Categoria.query.all()
    materiales = MaterialEncimera.query.all()
    tipos_lavabo = TipoLavabo.query.all()
    tipos_fregadero = TipoFregadero.query.all()
    valvulas_logo = ValvulaLogo.query.all()
    agujeros_grifo = AgujeroGrifo.query.all()
    toalleros = Toallero.query.all()
    faldones = Faldon.query.all()
    entrepanos = Entrepano.query.all()

    return render_template('agregar_producto.html', 
                           categorias=categorias, 
                           materiales=materiales, 
                           tipos_lavabo=tipos_lavabo, 
                           tipos_fregadero=tipos_fregadero,
                           valvulas_logo=valvulas_logo,
                           agujeros_grifo=agujeros_grifo,
                           toalleros=toalleros,
                           faldones=faldones,
                           entrepanos=entrepanos)




@app.route('/admin/editar_producto/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def editar_producto(producto_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    producto = Producto.query.get_or_404(producto_id)
    producto.verificar_descuento_expirado()

    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.descripcion = request.form['descripcion']
        producto.precio = float(request.form['precio'])
        producto.stock = int(request.form['stock'])
        producto.categoria_id = int(request.form['categoria_id'])
        
        # Actualizar las especificaciones
        especificaciones = request.form.getlist('especificaciones')
        Especificacion.query.filter_by(producto_id=producto.id).delete()
        for descripcion in especificaciones:
            nueva_especificacion = Especificacion(descripcion=descripcion, producto_id=producto.id)
            db.session.add(nueva_especificacion)
        
        # Guardar la imagen
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen = Imagen(url=filename, producto_id=producto.id)
                db.session.add(imagen)
        
        # Guardar el modelo 3D
        if 'modelo_3d' in request.files:
            modelo_file = request.files['modelo_3d']
            if modelo_file.filename != '' and allowed_file(modelo_file.filename):  # Reutiliza allowed_file si aplica
                modelo_filename = secure_filename(modelo_file.filename)
                modelo_file.save(os.path.join(app.config['MODEL_UPLOAD_FOLDER'], modelo_filename))
                producto.modelo_3d = modelo_filename  # Guardar la ruta relativa
        
        # Actualizar el descuento y la fecha de fin de descuento
        descuento = request.form.get('descuento')
        if descuento and int(descuento) > 0:
            producto.descuento = int(descuento)
            producto.precio_original = float(request.form['precio_original']) if request.form.get('precio_original') else producto.precio
            producto.precio = producto.precio_original * (1 - (producto.descuento / 100))

            # Establecer la fecha de fin de descuento con la zona horaria de Madrid
            fecha_fin_descuento_str = request.form.get('fecha_fin_descuento')
            if fecha_fin_descuento_str:
                madrid = timezone('Europe/Madrid')
                fecha_fin_descuento = datetime.strptime(fecha_fin_descuento_str, '%Y-%m-%dT%H:%M')
                producto.fecha_fin_descuento = madrid.localize(fecha_fin_descuento)
        else:
            # Si no hay descuento, resetear los valores
            producto.descuento = 0
            producto.precio = producto.precio_original if producto.precio_original else producto.precio
            producto.precio_original = None
            producto.fecha_fin_descuento = None

        db.session.commit()
        flash('Producto editado con éxito', 'success')
        return redirect(url_for('admin_products'))
    
    imagenes = producto.imagenes
    categorias = Categoria.query.all()
    especificaciones = Especificacion.query.filter_by(producto_id=producto.id).all()
    return render_template('editar_producto.html', producto=producto, categorias=categorias, especificaciones=especificaciones, imagenes=imagenes)



@app.route('/admin/eliminar_especificacion/<int:especificacion_id>', methods=['POST'])
@login_required
def eliminar_especificacion(especificacion_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    especificacion = Especificacion.query.get_or_404(especificacion_id)
    producto_id = especificacion.producto_id
    db.session.delete(especificacion)
    db.session.commit()
    flash('Especificación eliminada con éxito', 'success')
    return redirect(url_for('editar_producto', producto_id=producto_id))


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
        flash('No tienes permiso para realizar esta acción.', 'danger')
        return redirect(url_for('index'))
    
    producto = Producto.query.get_or_404(producto_id)
    imagenes = Imagen.query.filter_by(producto_id=producto.id).all()
    valoraciones = Valoracion.query.filter_by(producto_id=producto.id).all()  # Ajuste para manejar valoraciones

    try:
        # Eliminar imágenes asociadas
        for imagen in imagenes:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], imagen.url))
            except Exception as e:
                flash(f'Error al eliminar la imagen del sistema de archivos: {str(e)}', 'danger')
            db.session.delete(imagen)
        
        # Eliminar valoraciones asociadas
        for valoracion in valoraciones:
            db.session.delete(valoracion)
        
        # Eliminar el producto
        db.session.delete(producto)
        db.session.commit()
        flash('Producto, sus imágenes y valoraciones eliminados con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el producto: {str(e)}', 'danger')
    
    return redirect(url_for('admin_products'))


# Vista para administrar tipos de lavabos
@app.route('/admin/tipos_lavabo', methods=['GET'])
@login_required
def admin_tipos_lavabo():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    tipos_lavabo = TipoLavabo.query.all()
    return render_template('admin_tipo_lavabo.html', tipos_lavabo=tipos_lavabo)

# Vista para agregar un nuevo tipo de lavabo
@app.route('/admin/agregar_tipo_lavabo', methods=['GET', 'POST'])
@login_required
def agregar_tipo_lavabo():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        precio_adicional = float(request.form['precio_adicional'])

        nuevo_tipo_lavabo = TipoLavabo(nombre=nombre, precio_adicional=precio_adicional)
        db.session.add(nuevo_tipo_lavabo)
        db.session.commit()

        flash('Tipo de Lavabo agregado con éxito', 'success')
        return redirect(url_for('admin_tipos_lavabo'))

    return render_template('agregar_tipo_lavabo.html')

# Vista para administrar tipos de fregaderos
@app.route('/admin/tipos_fregadero', methods=['GET'])
@login_required
def admin_tipos_fregadero():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    tipos_fregadero = TipoFregadero.query.all()
    return render_template('admin_tipo_fregadero.html', tipos_fregadero=tipos_fregadero)

# Vista para agregar un nuevo tipo de fregadero
@app.route('/admin/agregar_tipo_fregadero', methods=['GET', 'POST'])
@login_required
def agregar_tipo_fregadero():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        precio_adicional = float(request.form['precio_adicional'])

        nuevo_tipo_fregadero = TipoFregadero(nombre=nombre, precio_adicional=precio_adicional)
        db.session.add(nuevo_tipo_fregadero)
        db.session.commit()

        flash('Tipo de Fregadero agregado con éxito', 'success')
        return redirect(url_for('admin_tipos_fregadero'))

    return render_template('agregar_tipo_fregadero.html')

# Función para eliminar tipos de lavabos
@app.route('/admin/eliminar_tipo_lavabo/<int:tipo_id>', methods=['POST'])
@login_required
def eliminar_tipo_lavabo(tipo_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    tipo_lavabo = TipoLavabo.query.get_or_404(tipo_id)
    db.session.delete(tipo_lavabo)
    db.session.commit()

    flash('Tipo de Lavabo eliminado con éxito', 'success')
    return redirect(url_for('admin_tipos_lavabo'))

# Función para eliminar tipos de fregaderos
@app.route('/admin/eliminar_tipo_fregadero/<int:tipo_id>', methods=['POST'])
@login_required
def eliminar_tipo_fregadero(tipo_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    tipo_fregadero = TipoFregadero.query.get_or_404(tipo_id)
    db.session.delete(tipo_fregadero)
    db.session.commit()

    flash('Tipo de Fregadero eliminado con éxito', 'success')
    return redirect(url_for('admin_tipos_fregadero'))

@app.route('/admin/editar_tipo_lavabo/<int:tipo_id>', methods=['GET', 'POST'])
@login_required
def editar_tipo_lavabo(tipo_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    tipo_lavabo = TipoLavabo.query.get_or_404(tipo_id)

    if request.method == 'POST':
        tipo_lavabo.nombre = request.form['nombre']
        tipo_lavabo.precio_adicional = float(request.form['precio_adicional'])
        db.session.commit()

        flash('Tipo de Lavabo actualizado con éxito', 'success')
        return redirect(url_for('admin_tipos_lavabo'))

    return render_template('editar_tipo_lavabo.html', tipo_lavabo=tipo_lavabo)

@app.route('/admin/editar_tipo_fregadero/<int:tipo_id>', methods=['GET', 'POST'])
@login_required
def editar_tipo_fregadero(tipo_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    tipo_fregadero = TipoFregadero.query.get_or_404(tipo_id)

    if request.method == 'POST':
        tipo_fregadero.nombre = request.form['nombre']
        tipo_fregadero.precio_adicional = float(request.form['precio_adicional'])
        db.session.commit()

        flash('Tipo de Fregadero actualizado con éxito', 'success')
        return redirect(url_for('admin_tipos_fregadero'))

    return render_template('editar_tipo_fregadero.html', tipo_fregadero=tipo_fregadero)


@app.route('/admin/materiales')
@login_required
def admin_materiales():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    materiales = MaterialEncimera.query.all()
    return render_template('admin_materiales.html', materiales=materiales)

@app.route('/admin/materiales/agregar', methods=['GET', 'POST'])
@login_required
def agregar_material():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio_por_m2 = float(request.form['precio_por_m2'])
        
        nuevo_material = MaterialEncimera(nombre=nombre, precio_por_m2=precio_por_m2)
        db.session.add(nuevo_material)
        db.session.commit()
        flash('Material agregado con éxito', 'success')
        return redirect(url_for('admin_materiales'))
    
    return render_template('agregar_material.html')

@app.route('/admin/materiales/editar/<int:material_id>', methods=['GET', 'POST'])
@login_required
def editar_material(material_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    material = MaterialEncimera.query.get_or_404(material_id)
    
    if request.method == 'POST':
        material.nombre = request.form['nombre']
        material.precio_por_m2 = float(request.form['precio_por_m2'])
        db.session.commit()
        flash('Material actualizado con éxito', 'success')
        return redirect(url_for('admin_materiales'))
    
    return render_template('editar_material.html', material=material)

@app.route('/admin/materiales/eliminar/<int:material_id>', methods=['POST'])
@login_required
def eliminar_material(material_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    material = MaterialEncimera.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    flash('Material eliminado con éxito', 'success')
    return redirect(url_for('admin_materiales'))

# Ruta para mostrar el panel de control de los campos de configuración
@app.route('/admin/campos_configuracion')
@login_required
def admin_campos_configuracion():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    valvulas = ValvulaLogo.query.all()
    agujeros = AgujeroGrifo.query.all()
    toalleros = Toallero.query.all()
    faldones = Faldon.query.all()
    entrepanos = Entrepano.query.all()

    return render_template('campos_configuracion.html', valvulas=valvulas, agujeros=agujeros, toalleros=toalleros, faldones=faldones, entrepanos=entrepanos)

# CRUD para ValvulaLogo
@app.route('/admin/agregar_valvula_logo', methods=['GET', 'POST'])
@login_required
def agregar_valvula_logo():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        precio_adicional = float(request.form['precio_adicional'])
        valvula = ValvulaLogo(nombre=nombre, precio_adicional=precio_adicional)
        db.session.add(valvula)
        db.session.commit()
        flash('Válvula con Logo agregada con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('agregar_valvula_logo.html')

@app.route('/admin/editar_valvula_logo/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_valvula_logo(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    valvula = ValvulaLogo.query.get_or_404(id)

    if request.method == 'POST':
        valvula.nombre = request.form['nombre']
        valvula.precio_adicional = float(request.form['precio_adicional'])
        db.session.commit()
        flash('Válvula con Logo actualizada con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('editar_valvula_logo.html', valvula=valvula)

@app.route('/admin/eliminar_valvula_logo/<int:id>', methods=['POST'])
@login_required
def eliminar_valvula_logo(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    valvula = ValvulaLogo.query.get_or_404(id)
    db.session.delete(valvula)
    db.session.commit()
    flash('Válvula con Logo eliminada con éxito', 'success')
    return redirect(url_for('admin_campos_configuracion'))

@app.route('/admin/agregar_agujero_grifo', methods=['GET', 'POST'])
@login_required
def agregar_agujero_grifo():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        precio_adicional = float(request.form['precio_adicional'])
        agujero = AgujeroGrifo(nombre=nombre, precio_adicional=precio_adicional)
        db.session.add(agujero)
        db.session.commit()
        flash('Agujero para Grifo agregado con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('agregar_agujero_grifo.html')


@app.route('/admin/editar_agujero_grifo/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_agujero_grifo(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    agujero = AgujeroGrifo.query.get_or_404(id)

    if request.method == 'POST':
        agujero.nombre = request.form['nombre']
        agujero.precio_adicional = float(request.form['precio_adicional'])
        db.session.commit()
        flash('Agujero para Grifo actualizado con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('editar_agujero_grifo.html', agujero=agujero)


@app.route('/admin/eliminar_agujero_grifo/<int:id>', methods=['POST'])
@login_required
def eliminar_agujero_grifo(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    agujero = AgujeroGrifo.query.get_or_404(id)
    db.session.delete(agujero)
    db.session.commit()
    flash('Agujero para Grifo eliminado con éxito', 'success')
    return redirect(url_for('admin_campos_configuracion'))

# CRUD for Toallero
@app.route('/admin/agregar_toallero', methods=['GET', 'POST'])
@login_required
def agregar_toallero():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        posicion = request.form['posicion']
        precio_adicional = float(request.form['precio_adicional'])
        toallero = Toallero(posicion=posicion, precio_adicional=precio_adicional)
        db.session.add(toallero)
        db.session.commit()
        flash('Toallero agregado con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('agregar_toallero.html')


@app.route('/admin/editar_toallero/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_toallero(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    toallero = Toallero.query.get_or_404(id)

    if request.method == 'POST':
        toallero.posicion = request.form['posicion']
        toallero.precio_adicional = float(request.form['precio_adicional'])
        db.session.commit()
        flash('Toallero actualizado con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('editar_toallero.html', toallero=toallero)


@app.route('/admin/eliminar_toallero/<int:id>', methods=['POST'])
@login_required
def eliminar_toallero(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    toallero = Toallero.query.get_or_404(id)
    db.session.delete(toallero)
    db.session.commit()
    flash('Toallero eliminado con éxito', 'success')
    return redirect(url_for('admin_campos_configuracion'))

# CRUD for Faldon
@app.route('/admin/agregar_faldon', methods=['GET', 'POST'])
@login_required
def agregar_faldon():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        posicion = request.form['posicion']
        medida = float(request.form['medida'])
        precio_adicional = float(request.form['precio_adicional'])
        faldon = Faldon(posicion=posicion, medida=medida, precio_adicional=precio_adicional)
        db.session.add(faldon)
        db.session.commit()
        flash('Faldón agregado con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('agregar_faldon.html')


@app.route('/admin/editar_faldon/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_faldon(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    faldon = Faldon.query.get_or_404(id)

    if request.method == 'POST':
        faldon.posicion = request.form['posicion']
        faldon.medida = float(request.form['medida'])
        faldon.precio_adicional = float(request.form['precio_adicional'])
        db.session.commit()
        flash('Faldón actualizado con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('editar_faldon.html', faldon=faldon)


@app.route('/admin/eliminar_faldon/<int:id>', methods=['POST'])
@login_required
def eliminar_faldon(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    faldon = Faldon.query.get_or_404(id)
    db.session.delete(faldon)
    db.session.commit()
    flash('Faldón eliminado con éxito', 'success')
    return redirect(url_for('admin_campos_configuracion'))

# CRUD for Entrepano
@app.route('/admin/agregar_entrepano', methods=['GET', 'POST'])
@login_required
def agregar_entrepano():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        tipo = request.form['tipo']
        medida = float(request.form['medida'])
        precio_adicional = float(request.form['precio_adicional'])
        entrepano = Entrepano(tipo=tipo, medida=medida, precio_adicional=precio_adicional)
        db.session.add(entrepano)
        db.session.commit()
        flash('Entrepano agregado con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('agregar_entrepano.html')


@app.route('/admin/editar_entrepano/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_entrepano(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    entrepano = Entrepano.query.get_or_404(id)

    if request.method == 'POST':
        entrepano.tipo = request.form['tipo']
        entrepano.medida = float(request.form['medida'])
        entrepano.precio_adicional = float(request.form['precio_adicional'])
        db.session.commit()
        flash('Entrepano actualizado con éxito', 'success')
        return redirect(url_for('admin_campos_configuracion'))

    return render_template('editar_entrepano.html', entrepano=entrepano)


@app.route('/admin/eliminar_entrepano/<int:id>', methods=['POST'])
@login_required
def eliminar_entrepano(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    entrepano = Entrepano.query.get_or_404(id)
    db.session.delete(entrepano)
    db.session.commit()
    flash('Entrepano eliminado con éxito', 'success')
    return redirect(url_for('admin_campos_configuracion'))

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


@app.route('/resend_confirmation', methods=['POST'])
def resend_confirmation():
    email = request.form['email']
    temp_user = TempUsuario.query.filter_by(email=email).first()
    
    if temp_user:
        try:
            # Generar el token de confirmación y enviar el correo
            token = generate_confirmation_token(temp_user.email)
            confirm_url = url_for('confirm_email', token=token, _external=True)
            html_content = render_template('email_confirmation.html', confirm_url=confirm_url)
            send_email(temp_user.email, 'Reenvío de confirmación de correo electrónico', html_content)
            
            flash('Se ha reenviado el correo de confirmación. Por favor, revisa tu bandeja de entrada o la carpeta de spam.', 'success')
        except Exception as e:
            flash(f'Error al reenviar el correo de confirmación: {str(e)}', 'danger')
    else:
        flash('No se encontró un usuario con ese correo electrónico.', 'danger')
    
    return redirect(url_for('login'))



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

    part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(part)

    try:
        server = smtplib.SMTP('localhost', 25)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print(f'Correo enviado a {to_email}')
    except Exception as e:
        print(f'Error al enviar correo: {e}')

def enviar_correo_pedido(email, pedido):
    items = OrdenProducto.query.filter_by(orden_id=pedido.id).all()

    # Construir el cuerpo del correo electrónico en HTML
    html_content = f"""
    <html>
        <body>
            <p>Hola {pedido.usuario.nombre},</p>
            <p>Gracias por tu compra. Aquí están los detalles de tu pedido:</p>
            <p><strong>Pedido ID:</strong> {pedido.id}</p>
            <p><strong>Total:</strong> {pedido.total} €</p>
            <p><strong>Método de Pago:</strong> {pedido.metodo_pago}</p>
            <p><strong>Dirección de Envío:</strong> {pedido.direccion_envio_id}</p>
            <h4>Productos:</h4>
            <ul>
    """
    for item in items:
        html_content += f"<li>{item.producto.nombre}: {item.cantidad} x {item.precio} €</li>"

    html_content += """
            </ul>
            <p>Gracias por comprar con nosotros.</p>
            <p>Atentamente,</p>
            <p>Tu Equipo de Ventas</p>
        </body>
    </html>
    """

    # Usar la función personalizada para enviar el correo
    subject = 'Detalles de tu pedido'
    send_email(to_email=email, subject=subject, html_content=html_content)

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
            user = Usuario(nombre=temp_user.nombre, email=temp_user.email, password_hash=temp_user.password_hash,is_confirmed=True)
            db.session.add(user)
            db.session.flush()  # Obtener el ID del usuario antes de hacer commit
            
            # Crear un carrito para el usuario recién registrado
            carrito = Carrito(usuario_id=user.id)
            db.session.add(carrito)
            db.session.delete(temp_user)  # Eliminar el usuario temporal
            db.session.commit()  # Hacer commit para todos los cambios
            
            send_welcome_email(user.email)
            
            flash('Tu cuenta ha sido confirmada y registrada con éxito. Por favor, inicia sesión.', 'success')
            session['email_confirmed'] = True  # Establecer estado de confirmación en la sesión
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
    user = Usuario.query.filter_by(email=email).first()
    if user and user.is_confirmed:
        flash('Tu cuenta ya ha sido confirmada. Por favor, inicia sesión.', 'success')
        return redirect(url_for('login'))
    
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