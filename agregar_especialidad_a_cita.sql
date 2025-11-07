-- Agregar columna especialidad_id a la tabla cita_medica
-- Esto permite guardar qué especialidad específica se reservó en cada cita

ALTER TABLE public.cita_medica 
ADD COLUMN especialidad_id bigint;

-- Agregar foreign key constraint
ALTER TABLE public.cita_medica
ADD CONSTRAINT cita_medica_especialidad_id_fkey 
FOREIGN KEY (especialidad_id) 
REFERENCES public.especialidad(id);

-- Comentario explicativo
COMMENT ON COLUMN public.cita_medica.especialidad_id IS 'Especialidad específica por la que se agendó la cita (importante cuando el doctor tiene múltiples especialidades)';
