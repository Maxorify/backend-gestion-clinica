-- Script para refrescar automáticamente la vista materializada
-- Ejecutar este SQL en Supabase después de crear la vista

-- Función que refresca la vista materializada
CREATE OR REPLACE FUNCTION refrescar_estadisticas_diarias()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY vista_estadisticas_diarias;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger en la tabla cita_medica (cuando se crea/actualiza/elimina una cita)
DROP TRIGGER IF EXISTS trigger_actualizar_estadisticas_cita ON cita_medica;
CREATE TRIGGER trigger_actualizar_estadisticas_cita
AFTER INSERT OR UPDATE OR DELETE ON cita_medica
FOR EACH STATEMENT
EXECUTE FUNCTION refrescar_estadisticas_diarias();

-- Trigger en la tabla estado (cuando cambia el estado de una cita)
DROP TRIGGER IF EXISTS trigger_actualizar_estadisticas_estado ON estado;
CREATE TRIGGER trigger_actualizar_estadisticas_estado
AFTER INSERT OR UPDATE OR DELETE ON estado
FOR EACH STATEMENT
EXECUTE FUNCTION refrescar_estadisticas_diarias();

-- Refrescar la vista ahora mismo
REFRESH MATERIALIZED VIEW CONCURRENTLY vista_estadisticas_diarias;
