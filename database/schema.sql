-- --------------------------------------------------------
-- Base de datos: healthy feet
-- --------------------------------------------------------

CREATE DATABASE IF NOT EXISTS `healthy feet`
DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `healthy feet`;

-- --------------------------------------------------------
-- Tabla: usuarios
-- --------------------------------------------------------
CREATE TABLE `usuarios` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `nombre` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('admin', 'user', 'staff') DEFAULT 'user',
  `fecha_creacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `ultimo_login` TIMESTAMP NULL,
  INDEX `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Tabla: empleados
-- --------------------------------------------------------
CREATE TABLE `empleados` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `usuario_id` INT NULL,
  `nombre` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) NOT NULL,
  `telefono` VARCHAR(10) NOT NULL,
  `foto` VARCHAR(255) NULL,
  `estado` ENUM('activo', 'inactivo') DEFAULT 'activo',
  `fecha_contratacion` DATE DEFAULT (CURDATE()),
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`id`) ON DELETE SET NULL,
  INDEX `idx_nombre` (`nombre`),
  INDEX `idx_email` (`email`),
  INDEX `idx_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Tabla: clientes
-- --------------------------------------------------------
CREATE TABLE `clientes` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `nombre` VARCHAR(100) NOT NULL,
  `telefono` VARCHAR(10) NOT NULL,
  `email` VARCHAR(100) NULL,
  `direccion` TEXT NULL,
  `notas` TEXT NULL,
  `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `ultima_visita` DATE NULL,
  UNIQUE KEY `unique_telefono` (`telefono`),
  INDEX `idx_nombre` (`nombre`),
  INDEX `idx_telefono` (`telefono`),
  INDEX `idx_ultima_visita` (`ultima_visita`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Tabla: servicios
-- --------------------------------------------------------
CREATE TABLE `servicios` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `nombre_servicio` VARCHAR(100) NOT NULL,
  `descripcion` TEXT NULL,
  `precio` DECIMAL(10,2) NOT NULL,
  `duracion` INT NOT NULL COMMENT 'Duración en minutos',
  `categoria` VARCHAR(50) NULL,
  `estado` ENUM('activo', 'inactivo') DEFAULT 'activo',
  `fecha_creacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `unique_nombre` (`nombre_servicio`),
  INDEX `idx_categoria` (`categoria`),
  INDEX `idx_precio` (`precio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Tabla: citas
-- --------------------------------------------------------
CREATE TABLE `citas` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `id_cliente` INT NOT NULL,
  `id_empleado` INT NOT NULL,
  `id_servicio` INT NOT NULL,
  `fecha` DATE NOT NULL,
  `hora` TIME NOT NULL,
  `notas` TEXT NULL,
  `estado` ENUM('pendiente', 'confirmada', 'cancelada', 'finalizada') DEFAULT 'pendiente',
  `fecha_creacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`id_cliente`) REFERENCES `clientes`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`id_empleado`) REFERENCES `empleados`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`id_servicio`) REFERENCES `servicios`(`id`) ON DELETE CASCADE,
  UNIQUE KEY `unique_empleado_hora` (`id_empleado`, `fecha`, `hora`),
  UNIQUE KEY `unique_cliente_hora` (`id_cliente`, `fecha`, `hora`),
  INDEX `idx_fecha` (`fecha`),
  INDEX `idx_estado` (`estado`),
  INDEX `idx_cliente_fecha` (`id_cliente`, `fecha`),
  INDEX `idx_empleado_fecha` (`id_empleado`, `fecha`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Tabla: citas_historial
-- --------------------------------------------------------
CREATE TABLE `citas_historial` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `id_cliente` INT NOT NULL,
  `id_empleado` INT NOT NULL,
  `id_servicio` INT NOT NULL,
  `fecha` DATE NOT NULL,
  `hora` TIME NOT NULL,
  `estado` ENUM('finalizada', 'cancelada', 'no_show') NOT NULL,
  `notas` TEXT NULL,
  `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_cliente` (`id_cliente`),
  INDEX `idx_fecha` (`fecha`),
  INDEX `idx_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Tabla: ventas
-- --------------------------------------------------------
CREATE TABLE `ventas` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `id_cliente` INT NOT NULL,
  `id_empleado` INT NOT NULL,
  `id_servicio` INT NOT NULL,
  `fecha` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `total` DECIMAL(10,2) NOT NULL,
  `metodo_pago` ENUM('efectivo', 'tarjeta', 'transferencia') DEFAULT 'efectivo',
  `notas` TEXT NULL,
  FOREIGN KEY (`id_cliente`) REFERENCES `clientes`(`id`),
  FOREIGN KEY (`id_empleado`) REFERENCES `empleados`(`id`),
  FOREIGN KEY (`id_servicio`) REFERENCES `servicios`(`id`),
  INDEX `idx_fecha` (`fecha`),
  INDEX `idx_cliente` (`id_cliente`),
  INDEX `idx_empleado` (`id_empleado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Tabla: productos
-- --------------------------------------------------------
CREATE TABLE `productos` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `nombre` VARCHAR(100) NOT NULL,
  `descripcion` TEXT NULL,
  `precio_compra` DECIMAL(10,2) NOT NULL,
  `precio_venta` DECIMAL(10,2) NOT NULL,
  `stock` INT DEFAULT 0,
  `stock_minimo` INT DEFAULT 5,
  `categoria` VARCHAR(50) NULL,
  `proveedor` VARCHAR(100) NULL,
  `estado` ENUM('activo', 'inactivo') DEFAULT 'activo',
  `fecha_creacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_nombre` (`nombre`),
  INDEX `idx_categoria` (`categoria`),
  INDEX `idx_stock` (`stock`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- USUARIOS INICIALES
-- --------------------------------------------------------

INSERT INTO `usuarios` (`nombre`, `email`, `password_hash`, `role`)
VALUES (
  'Administrador',
  'admin@healthyfeet.com',
  'pbkdf2:sha256:600000$Qvs3IZHv1q9zmayI$f4aa27db925e4b8b6e5b05c2579524a5e4519698a83298ef00927f323010a21b',
  'admin'
);

INSERT INTO `usuarios` (`nombre`, `email`, `password_hash`, `role`)
VALUES (
  'Staff Member',
  'staff@healthyfeet.com',
  'pbkdf2:sha256:600000$Qvs3IZHv1q9zmayI$f4aa27db925e4b8b6e5b05c2579524a5e4519698a83298ef00927f323010a21b',
  'staff'
);

-- --------------------------------------------------------
-- VISTAS
-- --------------------------------------------------------

CREATE OR REPLACE VIEW vista_citas_hoy AS
SELECT 
    c.id,
    cl.nombre AS cliente,
    e.nombre AS empleado,
    s.nombre_servicio AS servicio,
    c.fecha,
    c.hora,
    c.estado,
    s.precio,
    cl.telefono
FROM citas c
JOIN clientes cl ON c.id_cliente = cl.id
JOIN empleados e ON c.id_empleado = e.id
JOIN servicios s ON c.id_servicio = s.id
WHERE c.fecha = CURDATE()
ORDER BY c.hora ASC;

CREATE OR REPLACE VIEW vista_ventas_mensuales AS
SELECT 
    YEAR(fecha) AS ano,
    MONTH(fecha) AS mes,
    COUNT(*) AS total_ventas,
    SUM(total) AS ingresos_totales,
    AVG(total) AS promedio_venta
FROM ventas
GROUP BY YEAR(fecha), MONTH(fecha)
ORDER BY ano DESC, mes DESC;

CREATE OR REPLACE VIEW vista_top_clientes AS
SELECT 
    cl.id,
    cl.nombre,
    cl.telefono,
    COUNT(v.id) AS total_compras,
    SUM(v.total) AS total_gastado,
    MAX(v.fecha) AS ultima_compra
FROM clientes cl
LEFT JOIN ventas v ON cl.id = v.id_cliente
GROUP BY cl.id
ORDER BY total_gastado DESC;

-- --------------------------------------------------------
-- ÍNDICES EXTRA
-- --------------------------------------------------------

CREATE INDEX idx_ventas_fecha_cliente ON ventas(fecha, id_cliente);
CREATE INDEX idx_citas_fecha_hora ON citas(fecha, hora);
CREATE INDEX idx_clientes_nombre_telefono ON clientes(nombre, telefono);

-- --------------------------------------------------------
-- Tabla: plantillas
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `plantillas` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `nombre` VARCHAR(100) NOT NULL,
  `descripcion` TEXT NULL,
  `contenido` TEXT NOT NULL,
  `tipo` ENUM('cita', 'recordatorio', 'promocion', 'general') DEFAULT 'general',
  `estado` ENUM('activo', 'inactivo') DEFAULT 'activo',
  `fecha_creacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_nombre` (`nombre`),
  INDEX `idx_tipo` (`tipo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `plantillas` (`nombre`, `descripcion`, `contenido`, `tipo`) VALUES
('Confirmación de Cita', 'Plantilla para confirmar citas', 'Estimado/a [CLIENTE],\n\nSu cita ha sido confirmada para el [FECHA] a las [HORA].\n\nServicio: [SERVICIO]\nEmpleado: [EMPLEADO]\n\nPor favor, llegar 10 minutos antes.\n\nSaludos,\nHealthy Feet', 'cita'),
('Recordatorio de Cita', 'Recordatorio 24h antes', 'Hola [CLIENTE],\n\nLe recordamos su cita mañana [FECHA] a las [HORA].\n\nNo olvide traer [REQUISITOS].\n\nSaludos,\nHealthy Feet', 'recordatorio'),
('Promoción Mensual', 'Oferta especial del mes', '¡Oferta especial!\n\nEste mes tenemos 20% de descuento en [SERVICIO].\n\nVálido hasta [FECHA_LIMITE].\n\nReserve su cita al [TELEFONO].', 'promocion');
