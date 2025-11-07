-- Script para actualizar citas antiguas que no tienen especialidad_id asignada
-- Asigna la primera especialidad de cada doctor a sus citas sin especialidad

-- Actualizar citas sin especialidad_id con la primera especialidad del doctor
UPDATE public.cita_medica cm
SET especialidad_id = (
    SELECT ed.especialidad_id
    FROM public.especialidades_doctor ed
    WHERE ed.usuario_sistema_id = cm.doctor_id
    ORDER BY ed.id ASC
    LIMIT 1
)
WHERE cm.especialidad_id IS NULL
  AND EXISTS (
    SELECT 1
    FROM public.especialidades_doctor ed
    WHERE ed.usuario_sistema_id = cm.doctor_id
  );

-- Verificar cuántas citas se actualizaron
SELECT 
    COUNT(*) as citas_actualizadas,
    'Citas actualizadas con especialidad del doctor' as descripcion
FROM public.cita_medica
WHERE especialidad_id IS NOT NULL;

-- Ver resumen de citas por especialidad
SELECT 
    e.nombre as especialidad,
    COUNT(cm.id) as cantidad_citas
FROM public.cita_medica cm
INNER JOIN public.especialidad e ON e.id = cm.especialidad_id
GROUP BY e.nombre
ORDER BY cantidad_citas DESC;
