-- Script para eliminar diagnósticos duplicados
-- Ejecutar en Supabase SQL Editor

-- Este script mantiene solo el registro con el ID más bajo de cada enfermedad duplicada
-- y elimina el resto

DELETE FROM diagnosticos
WHERE id IN (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY nombre_enfermedad ORDER BY id) AS rn
        FROM diagnosticos
    ) AS duplicados
    WHERE rn > 1
);

-- Verificar cuántos diagnósticos únicos quedaron
SELECT COUNT(*) as total_diagnosticos FROM diagnosticos;

-- Ver si aún hay duplicados (debe devolver 0 filas)
SELECT nombre_enfermedad, COUNT(*) as cantidad
FROM diagnosticos
GROUP BY nombre_enfermedad
HAVING COUNT(*) > 1
ORDER BY cantidad DESC;
