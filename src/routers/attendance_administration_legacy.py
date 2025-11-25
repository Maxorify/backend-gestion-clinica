from fastapi import APIRouter, HTTPException, Query
from src.models.asistencia import RegistroAsistencia, ActualizarAsistencia
from src.utils.supabase import supabase_client
from datetime import datetime, date
from typing import Optional

attendance_router = APIRouter(tags=["Gestión de Asistencia"], prefix="/Asistencia")

@attendance_router.post("/registrar-entrada")
async def registrar_entrada(usuario_sistema_id: int):
    """
    Registra la entrada (inicio de turno) de un empleado.
    """
    try:
        # Verificar que el usuario existe
        usuario = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno")
            .eq("id", usuario_sistema_id)
            .execute()
        )
        if not usuario.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe el usuario con ID {usuario_sistema_id}."
            )

        # Verificar si ya tiene un turno activo (sin finalización)
        turno_activo = (
            supabase_client
            .table("asistencia")
            .select("id, inicio_turno")
            .eq("usuario_sistema_id", usuario_sistema_id)
            .is_("finalizacion_turno", "null")
            .execute()
        )

        if turno_activo.data:
            raise HTTPException(
                status_code=409,
                detail="El empleado ya tiene un turno activo sin finalizar."
            )

        # Registrar inicio de turno
        nuevo_registro = {
            "usuario_sistema_id": usuario_sistema_id,
            "inicio_turno": datetime.now().isoformat()
        }

        resultado = (
            supabase_client
            .table("asistencia")
            .insert(nuevo_registro)
            .execute()
        )

        if not resultado.data:
            raise HTTPException(status_code=500, detail="No se pudo registrar la entrada.")

        return {
            "mensaje": "Entrada registrada correctamente.",
            "asistencia": resultado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.post("/registrar-salida/{asistencia_id}")
async def registrar_salida(asistencia_id: int):
    """
    Registra la salida (finalización de turno) de un empleado.
    """
    try:
        # Verificar que existe el registro y no tiene salida
        registro = (
            supabase_client
            .table("asistencia")
            .select("id, inicio_turno, finalizacion_turno, usuario_sistema_id")
            .eq("id", asistencia_id)
            .execute()
        )

        if not registro.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe el registro de asistencia con ID {asistencia_id}."
            )

        if registro.data[0]["finalizacion_turno"]:
            raise HTTPException(
                status_code=409,
                detail="Este turno ya ha sido finalizado."
            )

        # Registrar finalización de turno
        resultado = (
            supabase_client
            .table("asistencia")
            .update({"finalizacion_turno": datetime.now().isoformat()})
            .eq("id", asistencia_id)
            .execute()
        )

        if not resultado.data:
            raise HTTPException(status_code=500, detail="No se pudo registrar la salida.")

        return {
            "mensaje": "Salida registrada correctamente.",
            "asistencia": resultado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.post("/registrar-asistencia")
async def registrar_asistencia(asistencia: RegistroAsistencia):
    """
    Registra la asistencia completa de un empleado con entrada y opcionalmente salida.
    """
    try:
        # Verificar que el usuario existe
        usuario = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno")
            .eq("id", asistencia.usuario_sistema_id)
            .execute()
        )
        if not usuario.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe el usuario con ID {asistencia.usuario_sistema_id}."
            )

        # Insertar nuevo registro
        nuevo_registro = {
            "usuario_sistema_id": asistencia.usuario_sistema_id,
            "inicio_turno": asistencia.inicio_turno.isoformat(),
        }

        if asistencia.finalizacion_turno:
            nuevo_registro["finalizacion_turno"] = asistencia.finalizacion_turno.isoformat()

        resultado = (
            supabase_client
            .table("asistencia")
            .insert(nuevo_registro)
            .execute()
        )

        if not resultado.data:
            raise HTTPException(status_code=500, detail="No se pudo registrar la asistencia.")

        return {
            "mensaje": "Asistencia registrada correctamente.",
            "asistencia": resultado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.get("/listar-asistencias")
async def listar_asistencias(
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    usuario_id: Optional[int] = Query(None, description="ID del usuario"),
    solo_activos: Optional[bool] = Query(False, description="Solo turnos activos (sin finalizar)")
):
    """
    Lista los registros de asistencia con filtros opcionales.
    Incluye información del usuario asociado.
    """
    try:
        query = (
            supabase_client
            .table("asistencia")
            .select("""
                id,
                usuario_sistema_id,
                inicio_turno,
                finalizacion_turno,
                usuario_sistema (
                    id,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    rut,
                    email,
                    rol_id,
                    rol (
                        nombre
                    )
                )
            """)
        )

        # Aplicar filtros
        if fecha_inicio:
            query = query.gte("inicio_turno", f"{fecha_inicio}T00:00:00")
        if fecha_fin:
            query = query.lte("inicio_turno", f"{fecha_fin}T23:59:59")
        if usuario_id:
            query = query.eq("usuario_sistema_id", usuario_id)
        if solo_activos:
            query = query.is_("finalizacion_turno", "null")

        resultado = query.order("inicio_turno", desc=True).execute()

        return {
            "total": len(resultado.data) if resultado.data else 0,
            "asistencias": resultado.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.get("/turnos-activos")
async def obtener_turnos_activos():
    """
    Obtiene todos los turnos activos (sin finalización).
    """
    try:
        resultado = (
            supabase_client
            .table("asistencia")
            .select("""
                id,
                usuario_sistema_id,
                inicio_turno,
                usuario_sistema (
                    id,
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    rut,
                    rol (
                        nombre
                    )
                )
            """)
            .is_("finalizacion_turno", "null")
            .order("inicio_turno", desc=False)
            .execute()
        )

        return {
            "total": len(resultado.data) if resultado.data else 0,
            "turnos_activos": resultado.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.get("/asistencia/{asistencia_id}")
async def obtener_asistencia(asistencia_id: int):
    """
    Obtiene un registro de asistencia específico por su ID.
    """
    try:
        resultado = (
            supabase_client
            .table("asistencia")
            .select("""
                id,
                usuario_sistema_id,
                inicio_turno,
                finalizacion_turno,
                usuario_sistema (
                    nombre,
                    apellido_paterno,
                    apellido_materno,
                    rut
                )
            """)
            .eq("id", asistencia_id)
            .execute()
        )

        if not resultado.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe el registro de asistencia con ID {asistencia_id}."
            )

        return resultado.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.put("/modificar-asistencia/{asistencia_id}")
async def modificar_asistencia(asistencia_id: int, datos: ActualizarAsistencia):
    """
    Modifica un registro de asistencia existente.
    Solo actualiza los campos proporcionados.
    """
    try:
        # Verificar que existe el registro
        existe = (
            supabase_client
            .table("asistencia")
            .select("id")
            .eq("id", asistencia_id)
            .execute()
        )

        if not existe.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe el registro de asistencia con ID {asistencia_id}."
            )

        # Construir objeto de actualización solo con campos proporcionados
        datos_actualizacion = {}

        if datos.inicio_turno is not None:
            datos_actualizacion["inicio_turno"] = datos.inicio_turno.isoformat()
        if datos.finalizacion_turno is not None:
            datos_actualizacion["finalizacion_turno"] = datos.finalizacion_turno.isoformat()

        if not datos_actualizacion:
            raise HTTPException(
                status_code=400,
                detail="No se proporcionaron campos para actualizar."
            )

        # Actualizar registro
        resultado = (
            supabase_client
            .table("asistencia")
            .update(datos_actualizacion)
            .eq("id", asistencia_id)
            .execute()
        )

        if not resultado.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar la asistencia.")

        return {
            "mensaje": "Asistencia actualizada correctamente.",
            "asistencia": resultado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.delete("/eliminar-asistencia/{asistencia_id}")
async def eliminar_asistencia(asistencia_id: int):
    """
    Elimina un registro de asistencia por su ID.
    """
    try:
        # Verificar que existe
        existe = (
            supabase_client
            .table("asistencia")
            .select("id, inicio_turno, usuario_sistema_id")
            .eq("id", asistencia_id)
            .execute()
        )

        if not existe.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe el registro de asistencia con ID {asistencia_id}."
            )

        # Eliminar registro
        resultado = (
            supabase_client
            .table("asistencia")
            .delete()
            .eq("id", asistencia_id)
            .execute()
        )

        return {
            "mensaje": "Registro de asistencia eliminado correctamente.",
            "registro_eliminado": existe.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.get("/listar-empleados")
async def listar_empleados():
    """
    Lista todos los empleados (usuarios del sistema) para el registro de asistencia.
    """
    try:
        resultado = (
            supabase_client
            .table("usuario_sistema")
            .select("""
                id,
                nombre,
                apellido_paterno,
                apellido_materno,
                rut,
                email,
                rol_id,
                rol (
                    nombre
                )
            """)
            .order("apellido_paterno")
            .execute()
        )

        return {
            "total": len(resultado.data) if resultado.data else 0,
            "empleados": resultado.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.get("/reporte-asistencia-empleado/{usuario_id}")
async def reporte_asistencia_empleado(
    usuario_id: int,
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)")
):
    """
    Genera un reporte de asistencia para un empleado específico.
    Opcionalmente filtra por rango de fechas.
    """
    try:
        # Verificar que el usuario existe
        usuario = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno, apellido_materno, rut")
            .eq("id", usuario_id)
            .execute()
        )

        if not usuario.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe el usuario con ID {usuario_id}."
            )

        # Construir query
        query = (
            supabase_client
            .table("asistencia")
            .select("*")
            .eq("usuario_sistema_id", usuario_id)
        )

        # Filtros de fecha
        if fecha_inicio:
            query = query.gte("inicio_turno", f"{fecha_inicio}T00:00:00")
        if fecha_fin:
            query = query.lte("inicio_turno", f"{fecha_fin}T23:59:59")

        resultado = query.order("inicio_turno", desc=False).execute()

        # Calcular estadísticas
        total_registros = len(resultado.data) if resultado.data else 0
        turnos_completos = len([r for r in (resultado.data or []) if r["finalizacion_turno"]])
        turnos_activos = total_registros - turnos_completos

        # Calcular horas trabajadas total
        horas_trabajadas = 0
        for registro in (resultado.data or []):
            if registro["finalizacion_turno"]:
                inicio = datetime.fromisoformat(registro["inicio_turno"].replace('Z', '+00:00'))
                fin = datetime.fromisoformat(registro["finalizacion_turno"].replace('Z', '+00:00'))
                horas_trabajadas += (fin - inicio).total_seconds() / 3600

        return {
            "empleado": usuario.data[0],
            "estadisticas": {
                "total_registros": total_registros,
                "turnos_completos": turnos_completos,
                "turnos_activos": turnos_activos,
                "horas_trabajadas_total": round(horas_trabajadas, 2)
            },
            "registros": resultado.data or []
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
