from fastapi import APIRouter, HTTPException, Query
from src.models.diagnosticos import Diagnostico
from src.utils.supabase import supabase_client

diagnostico_router = APIRouter(tags=["Funciones de diagnósticos"], prefix="/Diagnosticos")


@diagnostico_router.post("/crear-diagnostico")
async def crear_diagnostico(diagnostico: Diagnostico):
    """
    Crea un nuevo diagnóstico/enfermedad en la tabla diagnosticos.
    Lanza error 409 si el nombre ya está registrado.
    """
    try:
        # Verificar si ya existe
        existe = (
            supabase_client
            .table("diagnosticos")
            .select("id, nombre_enfermedad")
            .eq("nombre_enfermedad", diagnostico.nombre_enfermedad)
            .execute()
        )
        if existe.data:
            raise HTTPException(
                status_code=409,
                detail=f"La enfermedad '{diagnostico.nombre_enfermedad}' ya existe en el sistema."
            )

        # Insertar nuevo diagnóstico
        nuevo = (
            supabase_client
            .table("diagnosticos")
            .insert({
                "nombre_enfermedad": diagnostico.nombre_enfermedad,
                "descripcion_enfermedad": diagnostico.descripcion_enfermedad
            })
            .execute()
        )
        if not nuevo.data:
            raise HTTPException(status_code=500, detail="No se pudo insertar el diagnóstico.")

        return {
            "mensaje": f"Diagnóstico '{diagnostico.nombre_enfermedad}' creado correctamente.",
            "diagnostico": nuevo.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@diagnostico_router.put("/modificar-diagnostico/{diagnostico_id}")
async def modificar_diagnostico(diagnostico_id: int, diagnostico: Diagnostico):
    """
    Modifica un diagnóstico existente según su ID.
    Lanza 404 si no existe el diagnóstico.
    Lanza 409 si se intenta cambiar a un nombre ya usado.
    """
    try:
        # Verificar existencia
        existente = (
            supabase_client
            .table("diagnosticos")
            .select("id, nombre_enfermedad")
            .eq("id", diagnostico_id)
            .execute()
        )

        if not existente.data:
            raise HTTPException(status_code=404, detail=f"No existe el diagnóstico con ID {diagnostico_id}.")

        # Verificar duplicado de nombre (otro diagnóstico con mismo nombre)
        duplicado = (
            supabase_client
            .table("diagnosticos")
            .select("id")
            .eq("nombre_enfermedad", diagnostico.nombre_enfermedad)
            .neq("id", diagnostico_id)
            .execute()
        )
        if duplicado.data:
            raise HTTPException(
                status_code=409, 
                detail=f"Ya existe otro diagnóstico con nombre '{diagnostico.nombre_enfermedad}'."
            )

        # Actualizar datos
        actualizado = (
            supabase_client
            .table("diagnosticos")
            .update({
                "nombre_enfermedad": diagnostico.nombre_enfermedad,
                "descripcion_enfermedad": diagnostico.descripcion_enfermedad
            })
            .eq("id", diagnostico_id)
            .execute()
        )

        if not actualizado.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el diagnóstico.")

        return {
            "mensaje": f"Diagnóstico '{diagnostico.nombre_enfermedad}' modificado correctamente.",
            "diagnostico": actualizado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@diagnostico_router.delete("/eliminar-diagnostico/{diagnostico_id}")
async def eliminar_diagnostico(diagnostico_id: int):
    """
    Elimina un diagnóstico existente por su ID.
    Lanza 404 si el diagnóstico no existe.
    Lanza 409 si el diagnóstico está siendo usado en alguna cita médica.
    """
    try:
        # Verificar existencia
        existe = (
            supabase_client
            .table("diagnosticos")
            .select("id, nombre_enfermedad")
            .eq("id", diagnostico_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail=f"No existe el diagnóstico con ID {diagnostico_id}.")

        nombre = existe.data[0]["nombre_enfermedad"]

        # Verificar si está siendo usado en informacion_cita
        usado = (
            supabase_client
            .table("informacion_cita")
            .select("id")
            .eq("diagnostico_id", diagnostico_id)
            .limit(1)
            .execute()
        )
        if usado.data:
            raise HTTPException(
                status_code=409,
                detail=f"No se puede eliminar '{nombre}' porque está siendo usado en citas médicas."
            )

        # Eliminar el diagnóstico
        eliminado = (
            supabase_client
            .table("diagnosticos")
            .delete()
            .eq("id", diagnostico_id)
            .execute()
        )

        if not eliminado.data:
            raise HTTPException(status_code=500, detail="No se pudo eliminar el diagnóstico.")

        return {"mensaje": f"Diagnóstico '{nombre}' eliminado correctamente."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@diagnostico_router.get("/listar-diagnosticos")
async def listar_diagnosticos(
    page: int = Query(1, ge=1, description="Número de página (mínimo 1)"),
    limit: int = Query(6, ge=1, le=50, description="Cantidad de diagnósticos por página (máximo 50)"),
    search: str = Query(None, description="Buscar por nombre de enfermedad o descripción")
):
    """
    Devuelve diagnósticos paginados de la tabla 'diagnosticos'.
    
    Parámetros:
    - page: Número de página (empieza en 1)
    - limit: Cantidad de diagnósticos por página (default: 6, máximo: 50)
    - search: Buscar por nombre de enfermedad o descripción (opcional)
    """
    try:
        # Construir query base
        query = supabase_client.table("diagnosticos").select("*", count="exact")
        
        # Aplicar búsqueda si se especifica
        if search and search.strip():
            search_term = search.strip()
            # Buscar en nombre y descripción
            query = query.or_(
                f"nombre_enfermedad.ilike.%{search_term}%,"
                f"descripcion_enfermedad.ilike.%{search_term}%"
            )
        
        # Calcular offset para la paginación
        offset = (page - 1) * limit
        
        # Ejecutar query con paginación
        res = (
            query
            .order("id", desc=False)
            .range(offset, offset + limit - 1)
            .execute()
        )
        
        diagnosticos = res.data or []
        total_count = res.count if hasattr(res, 'count') else len(diagnosticos)
        
        # Calcular total de páginas
        total_pages = (total_count + limit - 1) // limit
        
        return {
            "diagnosticos": diagnosticos,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@diagnostico_router.get("/estadisticas-diagnosticos")
async def estadisticas_diagnosticos():
    """
    Obtiene estadísticas generales de los diagnósticos.
    """
    try:
        # Total de diagnósticos
        total = (
            supabase_client
            .table("diagnosticos")
            .select("id", count="exact")
            .execute()
        )
        total_diagnosticos = total.count if hasattr(total, 'count') else 0
        
        # Diagnósticos más usados (top 5)
        diagnosticos_usados = (
            supabase_client
            .table("informacion_cita")
            .select("diagnostico_id")
            .execute()
        )
        
        # Contar cuántas veces se usa cada diagnóstico
        uso_diagnosticos = {}
        for item in (diagnosticos_usados.data or []):
            diag_id = item.get("diagnostico_id")
            if diag_id:
                uso_diagnosticos[diag_id] = uso_diagnosticos.get(diag_id, 0) + 1
        
        total_usos = sum(uso_diagnosticos.values())
        diagnosticos_con_uso = len(uso_diagnosticos)
        diagnosticos_sin_uso = total_diagnosticos - diagnosticos_con_uso
        
        return {
            "total_diagnosticos": total_diagnosticos,
            "diagnosticos_con_uso": diagnosticos_con_uso,
            "diagnosticos_sin_uso": diagnosticos_sin_uso,
            "total_usos": total_usos
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
