-- Crear tabla de configuración del sistema
CREATE TABLE IF NOT EXISTS configuracion_sistema (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT,
    tipo VARCHAR(50) NOT NULL DEFAULT 'texto', -- texto, numero, booleano, json
    categoria VARCHAR(100) NOT NULL DEFAULT 'general', -- general, clinica, citas, notificaciones, sistema
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear índices
CREATE INDEX idx_configuracion_clave ON configuracion_sistema(clave);
CREATE INDEX idx_configuracion_categoria ON configuracion_sistema(categoria);

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION update_configuracion_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar updated_at
CREATE TRIGGER trigger_update_configuracion_updated_at
    BEFORE UPDATE ON configuracion_sistema
    FOR EACH ROW
    EXECUTE FUNCTION update_configuracion_updated_at();

-- Insertar configuraciones por defecto
INSERT INTO configuracion_sistema (clave, valor, tipo, categoria, descripcion) VALUES
-- Información de la Clínica
('clinica_nombre', 'Clínica Medical Center', 'texto', 'clinica', 'Nombre de la clínica'),
('clinica_ruc', '1234567890001', 'texto', 'clinica', 'RUC de la clínica'),
('clinica_telefono', '(555) 123-4567', 'texto', 'clinica', 'Teléfono de contacto'),
('clinica_email', 'info@clinica.com', 'texto', 'clinica', 'Email de contacto'),
('clinica_direccion', 'Av. Principal 123, Ciudad', 'texto', 'clinica', 'Dirección física'),

-- Configuración de Citas
('cita_duracion_minutos', '30', 'numero', 'citas', 'Duración de cada cita en minutos'),
('cita_por_hora', '2', 'numero', 'citas', 'Cantidad de citas por hora'),
('cita_hora_inicio', '08:00', 'texto', 'citas', 'Hora de inicio de atención'),
('cita_hora_fin', '18:00', 'texto', 'citas', 'Hora de fin de atención'),

-- Configuración de Notificaciones
('notificacion_email_activo', 'true', 'booleano', 'notificaciones', 'Activar notificaciones por email'),
('notificacion_sms_activo', 'false', 'booleano', 'notificaciones', 'Activar notificaciones por SMS'),

-- Configuración del Sistema
('sistema_modo_mantenimiento', 'false', 'booleano', 'sistema', 'Activar modo mantenimiento')
ON CONFLICT (clave) DO NOTHING;

-- Comentarios
COMMENT ON TABLE configuracion_sistema IS 'Tabla para almacenar configuraciones del sistema de la clínica';
COMMENT ON COLUMN configuracion_sistema.clave IS 'Clave única de la configuración';
COMMENT ON COLUMN configuracion_sistema.valor IS 'Valor de la configuración';
COMMENT ON COLUMN configuracion_sistema.tipo IS 'Tipo de dato: texto, numero, booleano, json';
COMMENT ON COLUMN configuracion_sistema.categoria IS 'Categoría de la configuración';
