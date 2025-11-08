-- Agregar campo 'activo' a la tabla usuario_sistema para implementar soft delete
-- Por defecto todos los usuarios existentes estarán activos

ALTER TABLE public.usuario_sistema
ADD COLUMN activo BOOLEAN NOT NULL DEFAULT TRUE;

-- Crear índice para mejorar performance en consultas filtradas por activo
CREATE INDEX idx_usuario_sistema_activo ON public.usuario_sistema(activo);

-- Comentario en la columna
COMMENT ON COLUMN public.usuario_sistema.activo IS 'Indica si el usuario está activo (TRUE) o ha sido eliminado lógicamente (FALSE)';
