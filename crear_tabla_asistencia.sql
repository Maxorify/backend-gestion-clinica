-- Crear tabla de asistencia para empleados
CREATE TABLE IF NOT EXISTS asistencia (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario_sistema(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    hora_entrada TIME,
    hora_salida TIME,
    estado VARCHAR(50) NOT NULL CHECK (estado IN ('Presente', 'Ausente', 'Tardanza', 'Permiso')),
    observaciones TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(usuario_id, fecha)
);

-- Crear índices para mejorar el rendimiento
CREATE INDEX idx_asistencia_usuario_id ON asistencia(usuario_id);
CREATE INDEX idx_asistencia_fecha ON asistencia(fecha);
CREATE INDEX idx_asistencia_estado ON asistencia(estado);

-- Crear función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_asistencia_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger para actualizar updated_at
CREATE TRIGGER trigger_update_asistencia_updated_at
    BEFORE UPDATE ON asistencia
    FOR EACH ROW
    EXECUTE FUNCTION update_asistencia_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE asistencia IS 'Tabla para registrar la asistencia diaria de los empleados del sistema';
COMMENT ON COLUMN asistencia.usuario_id IS 'ID del empleado (referencia a usuario_sistema)';
COMMENT ON COLUMN asistencia.fecha IS 'Fecha del registro de asistencia';
COMMENT ON COLUMN asistencia.hora_entrada IS 'Hora de entrada del empleado';
COMMENT ON COLUMN asistencia.hora_salida IS 'Hora de salida del empleado';
COMMENT ON COLUMN asistencia.estado IS 'Estado de asistencia: Presente, Ausente, Tardanza, Permiso';
COMMENT ON COLUMN asistencia.observaciones IS 'Notas adicionales sobre la asistencia';
