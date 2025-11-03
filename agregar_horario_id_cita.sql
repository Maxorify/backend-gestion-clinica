-- Script para agregar la columna horario_id a la tabla cita_medica
-- Esto relaciona cada cita con un bloque de horario específico

-- Agregar la columna horario_id (nullable porque las citas existentes no tienen horario asignado)
ALTER TABLE public.cita_medica 
ADD COLUMN IF NOT EXISTS horario_id bigint;

-- Agregar la foreign key constraint
ALTER TABLE public.cita_medica 
ADD CONSTRAINT cita_medica_horario_id_fkey 
FOREIGN KEY (horario_id) 
REFERENCES public.horarios_personal(id)
ON DELETE SET NULL;

-- Crear índice para mejorar performance en consultas
CREATE INDEX IF NOT EXISTS idx_cita_medica_horario_id 
ON public.cita_medica(horario_id);

-- Verificar que se agregó correctamente
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'cita_medica' AND column_name = 'horario_id';
