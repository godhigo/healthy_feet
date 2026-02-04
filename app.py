from flask import Flask, render_template, request, redirect, send_from_directory, flash, jsonify, abort
import os
import platform
import psutil
from datetime import date, datetime, timedelta, time
import uuid
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from functools import wraps
import pymysql
from pymysql import Connection
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.datastructures import FileStorage
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from dotenv import load_dotenv

# ============================================================================
# CONFIGURACIÓN Y SETUP
# ============================================================================

load_dotenv()

class Config:
    """Configuración centralizada de la aplicación"""
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-key-change-in-production")
    ADMIN_REGISTER_PASSWORD = os.getenv("ADMIN_REGISTER_PASSWORD", "admin123")
    
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "healthy feet")
    
    # Uploads
    BASE_DIR = Path(__file__).parent
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    SESSION_COOKIE_SAMESITE = 'Lax'

# Inicializar Flask con configuración
app = Flask(__name__)
app.config.from_object(Config)

# Asegurar que la carpeta de uploads existe
app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

# ============================================================================
# CONFIGURACIÓN LOGIN
# ============================================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Por favor inicia sesión para acceder a esta página."
login_manager.login_message_category = "warning"

# ============================================================================
# SERVICIOS DE VALIDACIÓN
# ============================================================================

class Validator:
    """Clase para validaciones centralizadas"""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Valida formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not email or not re.match(pattern, email):
            return False, "Email inválido"
        return True, ""
    
    @staticmethod
    def validate_phone(telefono: str) -> Tuple[bool, str]:
        """Valida número de teléfono (10 dígitos)"""
        if not telefono or not telefono.isdigit() or len(telefono) != 10:
            return False, "El teléfono debe tener exactamente 10 dígitos"
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """Valida fortaleza de contraseña"""
        if not password or len(password) < 8:
            return False, "La contraseña debe tener al menos 8 caracteres"
        if not any(c.isupper() for c in password):
            return False, "La contraseña debe tener al menos una mayúscula"
        if not any(c.isdigit() for c in password):
            return False, "La contraseña debe tener al menos un número"
        return True, ""
    
    @staticmethod
    def validate_file(file: Optional[FileStorage]) -> Tuple[bool, str]:
        """Valida archivo subido"""
        if not file or not file.filename:
            return True, ""  # Archivo opcional
        
        allowed_extensions = app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})
        if '.' not in file.filename:
            return False, "El archivo debe tener una extensión"
        
        extension = file.filename.rsplit('.', 1)[1].lower()
        
        if extension not in allowed_extensions:
            return False, f"Extensión '{extension}' no permitida. Use: {', '.join(allowed_extensions)}"
        
        max_size = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        file.seek(0, 2)  # Ir al final del archivo
        size = file.tell()
        file.seek(0)  # Volver al inicio
        
        if size > max_size:
            mb_size = max_size // (1024 * 1024)
            return False, f"Archivo demasiado grande. Máximo: {mb_size}MB"
        
        return True, ""

# ============================================================================
# SERVICIOS DE BASE DE DATOS
# ============================================================================

def get_connection() -> Connection:
    """Obtiene una conexión a la base de datos"""
    conn = pymysql.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        charset='utf8mb4',
        use_unicode=True
    )
    return conn

class DatabaseService:
    """Servicio para operaciones de base de datos"""
    
    @staticmethod
    def execute_query(query: str, params: Tuple = None, fetch_one: bool = False):
        """Ejecuta consultas de forma segura"""
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                if fetch_one:
                    return cursor.fetchone()
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def execute_insert(query: str, params: Tuple = None) -> int:
        """Ejecuta INSERT y retorna ID"""
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()
    
    @staticmethod
    def execute_update(query: str, params: Tuple = None) -> int:
        """Ejecuta UPDATE y retorna filas afectadas"""
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.rowcount
        finally:
            conn.close()
    
    @staticmethod
    def execute_delete(query: str, params: Tuple = None) -> int:
        """Ejecuta DELETE y retorna filas afectadas"""
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.rowcount
        finally:
            conn.close()

# ============================================================================
# SERVICIOS DE ARCHIVOS
# ============================================================================

class FileService:
    """Servicio para manejo de archivos"""
    
    @staticmethod
    def save_profile_picture(file: Optional[FileStorage]) -> Optional[str]:
        """Guarda una imagen de perfil y retorna el nombre del archivo"""
        if not file or not file.filename:
            return None
        
        # Validar archivo
        is_valid, error = Validator.validate_file(file)
        if not is_valid:
            raise ValueError(error)
        
        # Generar nombre único
        extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{extension}"
        filepath = app.config['UPLOAD_FOLDER'] / filename
        
        # Guardar archivo
        file.save(str(filepath))
        return filename
    
    @staticmethod
    def delete_file(filename: str) -> bool:
        """Elimina un archivo del sistema"""
        if not filename:
            return False
        
        filepath = app.config['UPLOAD_FOLDER'] / filename
        try:
            if filepath.exists():
                filepath.unlink()
                return True
        except Exception:
            pass
        return False

# ============================================================================
# MODELO USUARIO MEJORADO
# ============================================================================

class Usuario(UserMixin):
    """Modelo de usuario con métodos de clase"""
    
    def __init__(self, id: int, nombre: str, email: str, password_hash: str, role: str = 'user', **kwargs):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.password_hash = password_hash
        self.role = role
        
        # Campos adicionales
        self.fecha_creacion = kwargs.get('fecha_creacion')
        self.ultimo_login = kwargs.get('ultimo_login')
    
    @classmethod
    def get_by_id(cls, user_id: int) -> Optional['Usuario']:
        """Obtener usuario por ID"""
        conn = get_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM usuarios WHERE id = %s",
                    (user_id,)
                )
                usuario = cursor.fetchone()
                return cls(**usuario) if usuario else None
        finally:
            conn.close()
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['Usuario']:
        """Obtener usuario por email"""
        conn = get_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM usuarios WHERE email = %s",
                    (email,)
                )
                usuario = cursor.fetchone()
                return cls(**usuario) if usuario else None
        finally:
            conn.close()
    
    def verify_password(self, password: str) -> bool:
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def create(nombre: str, email: str, password: str, role: str = 'user') -> int:
        """Crear nuevo usuario"""
        password_hash = generate_password_hash(password)
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO usuarios (nombre, email, password_hash, role) 
                    VALUES (%s, %s, %s, %s)""",
                    (nombre, email, password_hash, role)
                )
                conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

@login_manager.user_loader
def load_user(user_id: str) -> Optional[Usuario]:
    """Cargar usuario para Flask-Login"""
    return Usuario.get_by_id(int(user_id))

# ============================================================================
# DECORADORES PERSONALIZADOS
# ============================================================================

def admin_required(f):
    """Decorador para requerir rol de administrador"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or getattr(current_user, 'role', 'user') != 'admin':
            flash("Acceso restringido a administradores", "error")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def handle_db_errors(f):
    """Decorador para manejar errores de base de datos"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except pymysql.Error as e:
            app.logger.error(f"Database error in {f.__name__}: {str(e)}")
            flash(f"Error de base de datos: {str(e)}", "error")
            return redirect(request.referrer or "/")
    return decorated_function

# ============================================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión"""
    if request.method == "GET":
        return render_template("login.html")
    
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    
    if not email or not password:
        flash("Email y contraseña son requeridos", "error")
        return render_template("login.html")
    
    usuario = Usuario.get_by_email(email)
    
    if not usuario or not usuario.verify_password(password):
        flash("Email o contraseña incorrectos", "error")
        return render_template("login.html")
    
    login_user(usuario)
    flash(f"Bienvenido(a) {usuario.nombre}!", "success")
    
    # Redirigir según rol
    next_page = request.args.get('next')
    if next_page:
        return redirect(next_page)
    
    return redirect("/")

@app.route("/logout")
@login_required
def logout():
    """Cierre de sesión"""
    logout_user()
    flash("Sesión cerrada correctamente", "info")
    return redirect("/login")

# ============================================================================
# RUTA PARA SERVIR IMÁGENES
# ============================================================================

@app.route('/uploads/<filename>')
def uploads(filename):
    """Servir archivos subidos"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============================================================================
# RUTAS DEL DASHBOARD
# ============================================================================

@app.route('/')
@login_required
def index():
    """Página principal del dashboard"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Citas del día
            cursor.execute("SELECT COUNT(*) as count FROM citas WHERE fecha = CURDATE()")
            citas_dia = cursor.fetchone()['count']
            
            # Total clientes
            cursor.execute("SELECT COUNT(*) as count FROM clientes")
            clientes = cursor.fetchone()['count']
            
            # Empleados activos
            cursor.execute("SELECT COUNT(*) as count FROM empleados WHERE estado = 'activo'")
            empleados = cursor.fetchone()['count']
            
            # Ventas de la semana
            cursor.execute("""
                SELECT IFNULL(SUM(total), 0) as total
                FROM ventas
                WHERE YEARWEEK(fecha, 1) = YEARWEEK(CURDATE(), 1)
            """)
            ventas_semana = cursor.fetchone()['total']
    finally:
        conn.close()
    
    return render_template(
        'index.html',
        citas_dia=citas_dia,
        clientes=clientes,
        empleados=empleados,
        ventas_semana=ventas_semana,
        current_user=current_user
    )

@app.route('/api/dashboard')
@login_required
def dashboard_data():
    """Datos para gráficos del dashboard"""
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Ventas últimos 7 días
            cursor.execute("""
                SELECT DATE(fecha) AS dia, SUM(total) AS total
                FROM ventas
                WHERE fecha >= CURDATE() - INTERVAL 6 DAY
                GROUP BY DATE(fecha)
                ORDER BY dia
            """)
            ventas_dias = cursor.fetchall()
            
            # Servicios más vendidos
            cursor.execute("""
                SELECT s.nombre_servicio, COUNT(*) AS cantidad
                FROM ventas v
                JOIN servicios s ON v.id_servicio = s.id
                GROUP BY s.nombre_servicio
                ORDER BY cantidad DESC
                LIMIT 5
            """)
            servicios = cursor.fetchall()
    finally:
        conn.close()
    
    return jsonify({
        "ventas_dias": ventas_dias,
        "servicios": servicios
    })

# ============================================================================
# RUTAS DE EMPLEADOS
# ============================================================================

@app.route('/empleados')
@login_required
def empleados():
    """Lista de empleados"""
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT e.* 
                FROM empleados e
                ORDER BY e.nombre
            """)
            empleados = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template("empleados.html", empleados=empleados)

@app.route('/actualizar_empleado', methods=['POST'])
@login_required
@handle_db_errors
def actualizar_empleado():
    """Actualizar información de empleado"""
    id_empleado = request.form.get('id')
    nombre = request.form.get('nombre', '').strip()
    email = request.form.get('email', '').strip()
    telefono = request.form.get('telefono', '').strip()
    foto = request.files.get("foto")
    
    # Validaciones
    errors = []
    is_valid, msg = Validator.validate_email(email)
    if not is_valid:
        errors.append(msg)
    
    is_valid, msg = Validator.validate_phone(telefono)
    if not is_valid:
        errors.append(msg)
    
    is_valid, msg = Validator.validate_file(foto)
    if not is_valid:
        errors.append(msg)
    
    if errors:
        flash(" | ".join(errors), "error")
        return redirect("/empleados")
    
    try:
        # Actualizar foto si hay
        filename = None
        if foto and foto.filename:
            # Obtener foto anterior para eliminarla
            conn = get_connection()
            old_photo = None
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT foto FROM empleados WHERE id = %s", (id_empleado,))
                    result = cursor.fetchone()
                    if result and result['foto']:
                        old_photo = result['foto']
            finally:
                conn.close()
            
            if old_photo:
                FileService.delete_file(old_photo)
            
            filename = FileService.save_profile_picture(foto)
        
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                if filename:
                    cursor.execute("""
                        UPDATE empleados
                        SET nombre=%s, email=%s, telefono=%s, foto=%s
                        WHERE id=%s
                    """, (nombre, email, telefono, filename, id_empleado))
                else:
                    cursor.execute("""
                        UPDATE empleados
                        SET nombre=%s, email=%s, telefono=%s
                        WHERE id=%s
                    """, (nombre, email, telefono, id_empleado))
                
                # Actualizar también en usuarios si corresponde
                cursor.execute("""
                    UPDATE usuarios 
                    SET nombre=%s, email=%s 
                    WHERE id = (SELECT usuario_id FROM empleados WHERE id = %s)
                """, (nombre, email, id_empleado))
                
                conn.commit()
        finally:
            conn.close()
        
        flash("Empleado actualizado correctamente", "success")
        return redirect("/empleados")
        
    except Exception as e:
        app.logger.error(f"Error actualizando empleado: {str(e)}")
        flash(f"Error al actualizar empleado: {str(e)}", "error")
        return redirect("/empleados")

# ============================================================================
# RUTAS DE ADMINISTRACIÓN (SOLO SUPERADMIN)
# ============================================================================

def superadmin_required(f):
    """Decorador para requerir ser el superadmin principal"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.email != "admin@healthyfeet.com":
            flash("Acceso restringido al superadministrador", "error")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@superadmin_required
def admin_panel():
    """Panel de administración - Solo para superadmin"""
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Estadísticas básicas
            cursor.execute("SELECT COUNT(*) as total FROM usuarios")
            total_usuarios = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM empleados")
            total_empleados = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM clientes")
            total_clientes = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM citas WHERE fecha = CURDATE()")
            citas_hoy = cursor.fetchone()['total']
            
            cursor.execute("SELECT IFNULL(SUM(total), 0) as total FROM ventas WHERE DATE(fecha) = CURDATE()")
            ventas_hoy = cursor.fetchone()['total']
            
            # Últimas actividades (simplificado)
            cursor.execute("""
                SELECT 'Nuevo cliente' as tipo, nombre, fecha_registro as fecha 
                FROM clientes 
                ORDER BY fecha_registro DESC 
                LIMIT 5
                
                UNION
                
                SELECT 'Nueva cita' as tipo, CONCAT('Cita para ', c.nombre) as nombre, NOW() as fecha
                FROM citas ci
                JOIN clientes c ON ci.id_cliente = c.id
                WHERE ci.fecha = CURDATE()
                ORDER BY ci.hora DESC
                LIMIT 5
                
                ORDER BY fecha DESC
                LIMIT 10
            """)
            actividades = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template(
        'admin/panel.html',
        total_usuarios=total_usuarios,
        total_empleados=total_empleados,
        total_clientes=total_clientes,
        citas_hoy=citas_hoy,
        ventas_hoy=ventas_hoy,
        actividades=actividades
    )

@app.route('/admin/system_info')
@superadmin_required
def system_info():
    """Información del sistema"""
    
    system_info = {
        "python_version": platform.python_version(),
        "system": platform.system(),
        "processor": platform.processor(),
        "memory_used": f"{psutil.virtual_memory().percent}%",
        "disk_used": f"{psutil.disk_usage('/').percent}%",
        "uptime": str(datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())),
        "cpu_usage": f"{psutil.cpu_percent()}%"
    }
    
    return render_template('admin/system_info.html', system_info=system_info)

@app.route('/admin/backup')
@superadmin_required
def backup_database():
    """Crear respaldo de la base de datos"""
    import subprocess
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_healthy_feet_{timestamp}.sql"
    
    try:
        # Crear respaldo usando mysqldump
        command = [
            'mysqldump',
            '-u', 'root',
            f'-p{app.config["DB_PASSWORD"]}',
            'healthy feet'
        ]
        
        with open(backup_file, 'w') as f:
            subprocess.run(command, stdout=f, text=True)
        
        flash(f"Respaldo creado: {backup_file}", "success")
    except Exception as e:
        flash(f"Error creando respaldo: {e}", "error")
    
    return redirect("/admin")

# ============================================================================
# RUTAS DE CLIENTES
# ============================================================================

@app.route('/clientes')
@login_required
def clientes():
    """Lista de clientes con historial"""
    filtro = request.args.get('nombre', '').strip()
    
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Obtener clientes
            cursor.execute(
                "SELECT * FROM clientes WHERE nombre LIKE %s ORDER BY nombre",
                (f"%{filtro}%",)
            )
            clientes = cursor.fetchall()
            
            # Obtener historial para cada cliente
            historial = {}
            for cliente in clientes:
                cursor.execute("""
                    SELECT c.fecha, c.hora, s.nombre_servicio, e.nombre AS empleado, c.estado
                    FROM citas c
                    JOIN servicios s ON c.id_servicio = s.id
                    JOIN empleados e ON c.id_empleado = e.id
                    WHERE c.id_cliente = %s
                    ORDER BY fecha DESC, hora DESC
                    LIMIT 10
                """, (cliente['id'],))
                
                historial[cliente['id']] = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template(
        "clientes.html",
        clientes=clientes,
        historial=historial,
        filtro=filtro
    )

# ============================================================================
# RUTAS DE CITAS
# ============================================================================

@app.route('/citas', methods=['GET', 'POST'])
@login_required
def citas():
    """Gestión de citas"""
    # Obtener fecha (del formulario o query string)
    fecha_str = request.form.get('fecha') or request.args.get('fecha')
    
    try:
        if fecha_str:
            fecha_actual = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        else:
            fecha_actual = date.today()
    except ValueError:
        fecha_actual = date.today()
    
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Citas del día
            cursor.execute("""
                SELECT ci.id, cl.nombre AS nombre_cliente, s.nombre_servicio,
                       e.nombre AS nombre_empleado, ci.fecha, ci.hora,
                       cl.telefono, s.precio, ci.estado
                FROM citas ci
                JOIN clientes cl ON ci.id_cliente = cl.id
                JOIN servicios s ON ci.id_servicio = s.id
                JOIN empleados e ON ci.id_empleado = e.id
                WHERE ci.fecha = %s
                ORDER BY ci.hora ASC
            """, (fecha_actual,))
            citas_dia = cursor.fetchall()
            
            # Datos para formularios
            cursor.execute("SELECT id, nombre FROM clientes ORDER BY nombre")
            clientes = cursor.fetchall()
            
            cursor.execute("SELECT id, nombre_servicio, precio, duracion FROM servicios ORDER BY nombre_servicio")
            servicios = cursor.fetchall()
            
            cursor.execute("SELECT id, nombre FROM empleados ORDER BY nombre")
            empleados = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template(
        "citas.html",
        citas_dia=citas_dia,
        clientes=clientes,
        servicios=servicios,
        empleados=empleados,
        fecha_actual=fecha_actual.strftime("%Y-%m-%d")
    )

@app.route('/agregar_cita', methods=['POST'])
@login_required
@handle_db_errors
def agregar_cita():
    """Agregar nueva cita"""
    # Datos del formulario
    nombre_cliente = request.form.get('cliente', '').strip()
    telefono = request.form.get('telefono', '').strip()
    id_servicio = request.form.get('servicio')
    id_empleado = request.form.get('empleado')
    fecha = request.form.get('fecha')
    hora = request.form.get('hora')
    
    # Validaciones básicas
    if not all([nombre_cliente, telefono, id_servicio, id_empleado, fecha, hora]):
        flash("Todos los campos son requeridos", "error")
        return redirect(f"/citas?fecha={fecha}")
    
    # Validar teléfono
    is_valid, msg = Validator.validate_phone(telefono)
    if not is_valid:
        flash(msg, "error")
        return redirect(f"/citas?fecha={fecha}")
    
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # --------------------------
            # CLIENTE
            # --------------------------
            cursor.execute(
                "SELECT id, nombre FROM clientes WHERE telefono = %s",
                (telefono, )
            )
            cliente_existente = cursor.fetchone()
            
            if cliente_existente:
                id_cliente = cliente_existente["id"]
            else:
                cursor.execute(
                    "INSERT INTO clientes (nombre, telefono) VALUES (%s, %s)",
                    (nombre_cliente, telefono)
                )
                conn.commit()
                id_cliente = cursor.lastrowid
            
            # --------------------------
            # VALIDAR CONFLICTO CLIENTE
            # --------------------------
            cursor.execute("""
                SELECT id FROM citas
                WHERE id_cliente = %s AND fecha = %s AND hora = %s
            """, (id_cliente, fecha, hora))
            
            if cursor.fetchone():
                flash(f"⚠ El cliente '{nombre_cliente}' ya tiene una cita el {fecha} a las {hora}.", "warning")
                return redirect(f"/citas?fecha={fecha}")
            
            # --------------------------
            # OBTENER DURACIÓN DEL SERVICIO
            # --------------------------
            cursor.execute(
                "SELECT duracion FROM servicios WHERE id = %s",
                (id_servicio,)
            )
            servicio = cursor.fetchone()
            if not servicio:
                flash("Servicio no encontrado", "error")
                return redirect(f"/citas?fecha={fecha}")
            
            duracion = servicio["duracion"]
            hora_inicio = datetime.strptime(hora, "%H:%M")
            hora_fin = hora_inicio + timedelta(minutes=duracion)
            
            # --------------------------
            # VALIDAR EMPALMES DEL EMPLEADO
            # --------------------------
            cursor.execute("""
                SELECT c.hora, s.duracion
                FROM citas c
                JOIN servicios s ON c.id_servicio = s.id
                WHERE c.id_empleado = %s AND c.fecha = %s
            """, (id_empleado, fecha))
            
            citas_empleado = cursor.fetchall()
            
            for c in citas_empleado:
                h_ini = datetime.strptime(str(c["hora"]), "%H:%M:%S")
                h_fin = h_ini + timedelta(minutes=c["duracion"])
                
                if hora_inicio < h_fin and hora_fin > h_ini:
                    flash("⚠ El empleado ya tiene una cita que se empalma con ese horario.", "warning")
                    return redirect(f"/citas?fecha={fecha}")
            
            # --------------------------
            # INSERTAR CITA
            # --------------------------
            cursor.execute("""
                INSERT INTO citas (id_cliente, id_empleado, id_servicio, fecha, hora)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_cliente, id_empleado, id_servicio, fecha, hora))
            
            conn.commit()
    finally:
        conn.close()
    
    flash("Cita agregada exitosamente", "success")
    return redirect(f"/citas?fecha={fecha}")

@app.route('/editar_cita', methods=['GET'])
@login_required
def editar_cita():
    """Formulario para editar cita"""
    id_cita = request.args.get('id')
    
    if not id_cita:
        flash("ID de cita no proporcionado", "error")
        return redirect("/citas")
    
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Obtener datos de la cita
            cursor.execute("""
                SELECT c.*, cl.nombre as cliente_nombre, cl.telefono
                FROM citas c
                JOIN clientes cl ON c.id_cliente = cl.id
                WHERE c.id = %s
            """, (id_cita,))
            cita = cursor.fetchone()
            
            if not cita:
                flash("Cita no encontrada", "error")
                return redirect("/citas")
            
            # VERIFICAR SI LA CITA ESTÁ FINALIZADA
            if cita.get('estado') == 'finalizada':
                flash("❌ No puedes editar una cita que ya ha sido finalizada", "error")
                return redirect(f"/citas?fecha={cita['fecha']}")
            
            # Obtener listas
            cursor.execute("SELECT id, nombre FROM clientes ORDER BY nombre")
            clientes = cursor.fetchall()
            
            cursor.execute("SELECT id, nombre_servicio FROM servicios ORDER BY nombre_servicio")
            servicios = cursor.fetchall()
            
            cursor.execute("SELECT id, nombre FROM empleados ORDER BY nombre")
            empleados = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template(
        'editar_cita.html',
        cita=cita,
        clientes=clientes,
        servicios=servicios,
        empleados=empleados
    )

@app.route('/actualizar_cita', methods=['POST'])
@login_required
@handle_db_errors
def actualizar_cita():
    """Actualizar cita existente"""
    id_cita = request.form.get('id')
    id_cliente = request.form.get('id_cliente')
    id_servicio = request.form.get('id_servicio')
    id_empleado = request.form.get('id_empleado')
    fecha = request.form.get('fecha')
    hora = request.form.get('hora')
    
    if not all([id_cita, id_cliente, id_servicio, id_empleado, fecha, hora]):
        flash("Todos los campos son requeridos", "error")
        return redirect(f"/editar_cita?id={id_cita}")
    
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:

            # Verificar si la cita está finalizada
            cursor.execute(
                "SELECT estado, fecha FROM citas WHERE id = %s",
                (id_cita,)
            )
            cita = cursor.fetchone()

            if not cita:
                flash("Cita no encontrada", "error")
                return redirect("/citas")

            if cita['estado'] == 'finalizada':
                flash("❌ No puedes editar una cita que ya fue finalizada", "error")
                return redirect(f"/citas?fecha={cita['fecha']}")

            # Verificar conflicto de cliente (hora exacta)
            cursor.execute("""
                SELECT id FROM citas
                WHERE id_cliente = %s 
                AND fecha = %s 
                AND hora = %s 
                AND id != %s
                AND estado != 'finalizada'
            """, (id_cliente, fecha, hora, id_cita))
            
            if cursor.fetchone():
                flash("⚠ El cliente ya tiene una cita en ese horario.", "warning")
                return redirect(f"/editar_cita?id={id_cita}")
            
            # Verificar conflicto de empleado (hora exacta)
            cursor.execute("""
                SELECT id FROM citas
                WHERE id_empleado = %s 
                AND fecha = %s 
                AND hora = %s 
                AND id != %s
                AND estado != 'finalizada'
            """, (id_empleado, fecha, hora, id_cita))
            
            if cursor.fetchone():
                flash("⚠ El empleado ya tiene una cita en ese horario.", "warning")
                return redirect(f"/editar_cita?id={id_cita}")
            
            # Actualizar cita
            cursor.execute("""
                UPDATE citas
                SET id_cliente=%s,
                    id_servicio=%s,
                    id_empleado=%s,
                    fecha=%s,
                    hora=%s
                WHERE id = %s
            """, (id_cliente, id_servicio, id_empleado, fecha, hora, id_cita))
            
            conn.commit()

    finally:
        conn.close()
    
    flash("✅ Cita actualizada exitosamente", "success")
    return redirect(f"/citas?fecha={fecha}")


@app.route('/finalizar_cita', methods=['POST'])
@login_required
@handle_db_errors
def finalizar_cita():
    """Finalizar cita y crear venta"""
    id_cita = request.form.get('id_cita')
    
    if not id_cita:
        flash("ID de cita no proporcionado", "error")
        return redirect("/citas")
    
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Obtener datos de la cita
            cursor.execute("""
                SELECT id_cliente, id_empleado, id_servicio, fecha, hora
                FROM citas
                WHERE id = %s
            """, (id_cita,))
            cita = cursor.fetchone()
            
            if not cita:
                flash("Cita no encontrada", "error")
                return redirect("/citas")
            
            # Obtener precio del servicio
            cursor.execute("SELECT precio FROM servicios WHERE id = %s", (cita['id_servicio'],))
            servicio = cursor.fetchone()
            precio = servicio['precio'] if servicio else 0
            
            # Crear venta
            cursor.execute("""
                INSERT INTO ventas (id_cliente, id_empleado, id_servicio, fecha, total)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                cita['id_cliente'],
                cita['id_empleado'],
                cita['id_servicio'],
                cita['fecha'],
                precio
            ))
            
            # Mover a historial
            cursor.execute("""
                INSERT INTO citas_historial (id_cliente, id_empleado, id_servicio, fecha, hora, estado)
                SELECT id_cliente, id_empleado, id_servicio, fecha, hora, 'finalizada'
                FROM citas
                WHERE id = %s
            """, (id_cita,))
            
            # Actualizar estado de la cita a 'finalizada' en lugar de eliminarla
            cursor.execute("""
                UPDATE citas
                SET estado = 'finalizada'
                WHERE id = %s
            """, (id_cita,))
            
            conn.commit()
    finally:
        conn.close()
    
    flash("Cita finalizada y venta registrada exitosamente", "success")
    return redirect(f"/citas?fecha={cita['fecha']}")

# ============================================================================
# RUTAS DE VENTAS
# ============================================================================

@app.route('/ventas', methods=['GET', 'POST'])
@login_required
def ventas():
    """Gestión de ventas con filtros"""
    filtro = request.form.get('filtro', 'dia') or request.args.get('filtro', 'dia')
    valor = request.form.get('valor_filtro') or request.args.get('valor_filtro')
    
    # Construir consulta base
    query_base = """
        SELECT v.id, c.nombre AS cliente, e.nombre AS empleado, 
               s.nombre_servicio AS servicio, v.fecha, v.total
        FROM ventas v
        JOIN clientes c ON v.id_cliente = c.id
        JOIN empleados e ON v.id_empleado = e.id
        JOIN servicios s ON v.id_servicio = s.id
    """
    
    filtro_query = ""
    params = ()
    
    if valor:
        if filtro == 'dia':
            filtro_query = "WHERE DATE(v.fecha) = %s"
            params = (valor,)
        elif filtro == 'semana':
            try:
                year, week = valor.split('-W')
                filtro_query = "WHERE YEAR(v.fecha) = %s AND WEEK(v.fecha, 1) = %s"
                params = (int(year), int(week))
            except ValueError:
                filtro_query = "WHERE DATE(v.fecha) = CURDATE()"
        elif filtro == 'mes':
            try:
                year, month = valor.split('-')
                filtro_query = "WHERE YEAR(v.fecha) = %s AND MONTH(v.fecha) = %s"
                params = (int(year), int(month))
            except ValueError:
                filtro_query = "WHERE DATE(v.fecha) = CURDATE()"
        elif filtro == 'ano':
            filtro_query = "WHERE YEAR(v.fecha) = %s"
            params = (int(valor),)
    else:
        filtro_query = "WHERE DATE(v.fecha) = CURDATE()"
    
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Obtener ventas
            cursor.execute(f"{query_base} {filtro_query} ORDER BY v.fecha DESC, v.id DESC", params)
            ventas = cursor.fetchall()
            
            # Calcular total
            cursor.execute(f"SELECT IFNULL(SUM(total),0) as total FROM ventas v {filtro_query}", params)
            total_ganancias = cursor.fetchone()['total']
    finally:
        conn.close()
    
    return render_template(
        'ventas.html',
        ventas=ventas,
        total_ganancias=total_ganancias,
        filtro=filtro,
        valor_filtro=valor or ""
    )

# ============================================================================
# FILTROS PERSONALIZADOS PARA TEMPLATES
# ============================================================================

@app.template_filter('format_currency')
def format_currency(value):
    """Formatear moneda"""
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return f"$0.00"

@app.template_filter('format_date')
def format_date(value, format='%d/%m/%Y'):
    """Formatear fecha"""
    if not value:
        return ''
    
    if isinstance(value, str):
        try:
            # Intentar diferentes formatos de fecha
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
        except:
            return value
    elif isinstance(value, date):
        value = datetime.combine(value, datetime.min.time())
    
    return value.strftime(format) if value else ''

@app.template_filter('format_time')
def format_time(value):
    """Formatear hora"""
    if not value:
        return ''
    
    if isinstance(value, str):
        try:
            # Intentar diferentes formatos de hora
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.strftime('%I:%M %p').lstrip('0')
                except ValueError:
                    continue
        except:
            return value
    return value


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'images/favicon.ico', mimetype='image/vnd.microsoft.icon')

# ============================================================================
# MANEJO DE ERRORES
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    """Página no encontrada"""
    return render_template(
        "mensaje.html",
        mensaje="❌ La página que buscas no existe",
        regresar="/"
    ), 404

@app.errorhandler(403)
def forbidden(e):
    """Acceso prohibido"""
    return render_template(
        "mensaje.html",
        mensaje="⛔ No tienes permiso para acceder a esta página",
        regresar="/"
    ), 403

@app.errorhandler(500)
def server_error(e):
    """Error interno del servidor"""
    app.logger.error(f"Server error: {str(e)}")
    return render_template(
        "mensaje.html",
        mensaje="⚠️ Ocurrió un error interno. Por favor, intenta más tarde.",
        regresar="/"
    ), 500

@app.errorhandler(413)
def request_entity_too_large(e):
    """Archivo demasiado grande"""
    return render_template(
        "mensaje.html",
        mensaje="📁 El archivo es demasiado grande. Máximo 16MB",
        regresar=request.referrer or "/"
    ), 413

# ============================================================================
# FILTROS PERSONALIZADOS PARA TEMPLATES
# ============================================================================

@app.template_filter('format_currency')
def format_currency(value):
    """Formatear moneda"""
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return f"$0.00"

@app.template_filter('format_date')
def format_date(value, format='%d/%m/%Y'):
    """Formatear fecha"""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value
    elif isinstance(value, date):
        value = datetime.combine(value, datetime.min.time())
    
    return value.strftime(format) if value else ''

@app.template_filter('format_time')
def format_time(value):
    """Formatear hora"""
    if isinstance(value, str):
        try:
            # Intentar diferentes formatos
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.strftime('%I:%M %p').lstrip('0')
                except ValueError:
                    continue
        except Exception:
            pass
    return value

# ============================================================================
# RUTAS DE PRUEBA Y SALUD
# ============================================================================

@app.route('/health')
def health_check():
    """Endpoint para verificar el estado de la aplicación"""
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        conn.close()
        db_status = "OK"
    except Exception as e:
        db_status = f"ERROR: {str(e)}"
    
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "uploads_folder": os.path.exists(app.config['UPLOAD_FOLDER'])
    })

# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == '__main__':
    # Configuración para desarrollo vs producción
    debug_mode = os.getenv("FLASK_ENV") != "production"
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=debug_mode,
        threaded=True  # Para manejar múltiples solicitudes simultáneas
    )
