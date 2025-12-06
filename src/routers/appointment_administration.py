from fastapi import APIRouter, HTTPException
from src.models.citas import (
    CrearCitaCompleta,
    ActualizarCita,
    ActualizarInformacionCita,
    CambiarEstado,
    CrearPago
)
from src.utils.supabase import supabase_client
from typing import Optional, List
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from datetime import datetime, date
from pydantic import BaseModel

appointment_router = APIRouter(tags=["Gestión de Citas Médicas"], prefix="/Citas")


# Modelos adicionales para recetas y diagnósticos
class RecetaMedicamento(BaseModel):
    nombre: str
    presentacion: Optional[str] = None
    dosis: Optional[str] = None
    duracion: Optional[str] = None
    cantidad: Optional[str] = None


class GuardarConsulta(BaseModel):
    motivo_consulta: Optional[str] = None
    antecedentes: Optional[str] = None
    dolores_sintomas: Optional[str] = None
    atenciones_quirurgicas: Optional[str] = None
    evaluacion_doctor: Optional[str] = None
    tratamiento: Optional[str] = None
    diagnostico_ids: Optional[List[int]] = None
    recetas: Optional[List[RecetaMedicamento]] = None


@appointment_router.post("/crear-cita")
async def crear_cita(cita_completa: CrearCitaCompleta):
    """
    Crea una nueva cita médica con su información y estado inicial.
    """
    try:
        # Verificar que el paciente existe
        paciente = (
            supabase_client
            .table("paciente")
            .select("id, nombre, apellido_paterno")
            .eq("id", cita_completa.cita.paciente_id)
            .execute()
        )
        if not paciente.data:
            raise HTTPException(status_code=404, detail="El paciente no existe.")

        # Verificar que el doctor existe y es médico
        doctor = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno, rol_id")
            .eq("id", cita_completa.cita.doctor_id)
            .execute()
        )
        if not doctor.data:
            raise HTTPException(status_code=404, detail="El doctor no existe.")

        if doctor.data[0].get("rol_id") != 2:
            raise HTTPException(status_code=400, detail="El usuario seleccionado no es un doctor.")

        # Verificar que el doctor tenga horarios disponibles en la fecha/hora seleccionada
        fecha_cita = cita_completa.cita.fecha_atencion

        # Buscar horarios del doctor que contengan esta fecha/hora
        horarios_doctor = (
            supabase_client
            .table("horarios_personal")
            .select("id, inicio_bloque, finalizacion_bloque")
            .eq("usuario_sistema_id", cita_completa.cita.doctor_id)
            .lte("inicio_bloque", fecha_cita.isoformat())
            .gte("finalizacion_bloque", fecha_cita.isoformat())
            .execute()
        )

        if not horarios_doctor.data:
            raise HTTPException(
                status_code=409,
                detail="El doctor no tiene horarios asignados para la fecha/hora seleccionada."
            )

        # Verificar que no exista otra cita en la misma fecha/hora para este doctor
        cita_existente = (
            supabase_client
            .table("cita_medica")
            .select("id, estado(estado)")
            .eq("doctor_id", cita_completa.cita.doctor_id)
            .eq("fecha_atencion", fecha_cita.isoformat())
            .execute()
        )

        # Verificar que no sea una cita cancelada
        for cita in (cita_existente.data or []):
            estado_list = cita.get("estado", [])
            if estado_list:
                estado_actual = estado_list[0].get("estado") if isinstance(estado_list, list) else estado_list.get("estado")
                if estado_actual != "Cancelada":
                    raise HTTPException(
                        status_code=409,
                        detail="Ya existe una cita para este doctor en la fecha/hora seleccionada."
                    )

        # Crear la cita médica
        nueva_cita = (
            supabase_client
            .table("cita_medica")
            .insert({
                "fecha_atencion": fecha_cita.isoformat(),
                "paciente_id": cita_completa.cita.paciente_id,
                "doctor_id": cita_completa.cita.doctor_id,
                "especialidad_id": cita_completa.cita.especialidad_id
            })
            .execute()
        )

        if not nueva_cita.data:
            raise HTTPException(status_code=500, detail="No se pudo crear la cita.")

        cita_id = nueva_cita.data[0]["id"]

        # Crear el estado inicial
        estado_inicial = (
            supabase_client
            .table("estado")
            .insert({
                "estado": cita_completa.estado_inicial,
                "cita_medica_id": cita_id
            })
            .execute()
        )

        if not estado_inicial.data:
            # Rollback: eliminar la cita creada
            supabase_client.table("cita_medica").delete().eq("id", cita_id).execute()
            raise HTTPException(status_code=500, detail="No se pudo crear el estado inicial.")

        # Crear la información de la cita
        info_cita = (
            supabase_client
            .table("informacion_cita")
            .insert({
                "cita_medica_id": cita_id,
                "motivo_consulta": cita_completa.informacion.motivo_consulta,
                "antecedentes": cita_completa.informacion.antecedentes,
                "dolores_sintomas": cita_completa.informacion.dolores_sintomas,
                "atenciones_quirurgicas": cita_completa.informacion.atenciones_quirurgicas,
                "evaluacion_doctor": cita_completa.informacion.evaluacion_doctor,
                "tratamiento": cita_completa.informacion.tratamiento,
                "diagnostico_id": cita_completa.informacion.diagnostico_id
            })
            .execute()
        )

        if not info_cita.data:
            # Rollback: eliminar cita y estado
            supabase_client.table("estado").delete().eq("id", estado_inicial.data[0]["id"]).execute()
            supabase_client.table("cita_medica").delete().eq("id", cita_id).execute()
            raise HTTPException(status_code=500, detail="No se pudo crear la información de la cita.")

        return {
            "mensaje": "Cita creada exitosamente.",
            "cita": nueva_cita.data[0],
            "estado": estado_inicial.data[0],
            "informacion": info_cita.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/listar-citas")
async def listar_citas(
    fecha: Optional[str] = None,
    doctor_id: Optional[int] = None,
    paciente_id: Optional[int] = None,
    estado: Optional[str] = None,
    limite: int = 100,
    offset: int = 0
):
    """
    Lista todas las citas con información del paciente, doctor y especialidad.
    Filtros opcionales: fecha, doctor_id, paciente_id, estado.
    OPTIMIZADO: Usa función SQL con JOINs y paginación (con fallback).
    """
    try:
        # Intentar usar la función SQL optimizada
        try:
            resultado = supabase_client.rpc(
                "listar_citas_con_estado",
                {
                    "fecha_filtro": fecha,
                    "p_doctor_id": doctor_id,
                    "p_paciente_id": paciente_id,
                    "estado_filtro": estado,
                    "limite": limite,
                    "offset": offset
                }
            ).execute()

            if resultado.data:
                # Obtener total
                total_resultado = supabase_client.rpc(
                    "listar_citas_con_estado",
                    {
                        "fecha_filtro": fecha,
                        "p_doctor_id": doctor_id,
                        "p_paciente_id": paciente_id,
                        "estado_filtro": estado,
                        "limite": 999999,
                        "offset": 0
                    }
                ).execute()

                total = len(total_resultado.data) if total_resultado.data else 0

                return {
                    "citas": resultado.data,
                    "total": total,
                    "limite": limite,
                    "offset": offset
                }
        except Exception as rpc_error:
            print(f"⚠️ RPC no disponible, usando fallback: {str(rpc_error)}")

        # FALLBACK: Query optimizada con bulk
        chile_tz = ZoneInfo("America/Santiago")
        
        # Query con JOINs para obtener todo de una vez
        query = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                doctor_id,
                especialidad_id,
                paciente:paciente_id(id, nombre, apellido_paterno, apellido_materno, telefono, rut),
                doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno),
                especialidad:especialidad_id(id, nombre)
            """)
        )

        # Aplicar filtros
        if fecha:
            query = query.gte("fecha_atencion", f"{fecha}T00:00:00-03:00").lte("fecha_atencion", f"{fecha}T23:59:59-03:00")
        
        if doctor_id:
            query = query.eq("doctor_id", doctor_id)
        if paciente_id:
            query = query.eq("paciente_id", paciente_id)

        citas_result = query.order("fecha_atencion", desc=False).execute()
        
        citas_filtradas = citas_result.data or []

        if not citas_filtradas:
            return {"citas": [], "total": 0}

        # Extraer IDs de citas para bulk queries
        citas_ids = [cita["id"] for cita in citas_filtradas]
        
        # Bulk query de TODOS los estados
        estados_response = (
            supabase_client
            .table("estado")
            .select("cita_medica_id, estado, id")
            .in_("cita_medica_id", citas_ids)
            .order("id", desc=True)
            .execute()
        )
        
        # Crear diccionario de estados (solo el más reciente por cita)
        estados_dict = {}
        if estados_response.data:
            for est in estados_response.data:
                cita_id = est["cita_medica_id"]
                if cita_id not in estados_dict:
                    estados_dict[cita_id] = est["estado"]
        
        # Bulk query de precios de especialidades únicas
        especialidad_ids = list(set(
            cita.get("especialidad_id") 
            for cita in citas_filtradas 
            if cita.get("especialidad_id")
        ))
        
        precios_dict = {}
        if especialidad_ids:
            precios_response = (
                supabase_client
                .table("costos_servicio")
                .select("especialidad_id, precio")
                .in_("especialidad_id", especialidad_ids)
                .execute()
            )
            
            if precios_response.data:
                for precio in precios_response.data:
                    precios_dict[precio["especialidad_id"]] = precio["precio"]
        
        # Construir respuesta usando datos pre-cargados
        citas_con_estado = []
        for cita in citas_filtradas:
            # Obtener estado del diccionario (O(1) lookup)
            estado_texto = estados_dict.get(cita["id"], "Sin estado")

            # Filtrar por estado si se especificó
            if estado and estado_texto != estado:
                continue

            # Obtener precio del diccionario (O(1) lookup)
            precio_especialidad = None
            if cita.get("especialidad_id"):
                precio_especialidad = precios_dict.get(cita["especialidad_id"])

            citas_con_estado.append({
                **cita,
                "estado_actual": estado_texto,
                "especialidad": cita.get("especialidad"),
                "precio_especialidad": precio_especialidad
            })

        # Aplicar paginación
        total = len(citas_con_estado)
        citas_paginadas = citas_con_estado[offset:offset+limite]

        return {
            "citas": citas_paginadas,
            "total": total,
            "limite": limite,
            "offset": offset
        }

    except Exception as e:
        import traceback
        print(f"ERROR en listar_citas: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/cita/{cita_id}")
async def obtener_cita(cita_id: int):
    """
    Obtiene el detalle completo de una cita específica.
    """
    try:
        # Obtener la cita con información del paciente y doctor
        cita = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                paciente:paciente_id(id, nombre, apellido_paterno, apellido_materno, telefono, rut, correo),
                doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno)
            """)
            .eq("id", cita_id)
            .execute()
        )

        if not cita.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Obtener el estado actual
        estado_actual = (
            supabase_client
            .table("estado")
            .select("estado")
            .eq("cita_medica_id", cita_id)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )

        # Obtener información de la cita
        info_cita = (
            supabase_client
            .table("informacion_cita")
            .select("*")
            .eq("cita_medica_id", cita_id)
            .execute()
        )

        return {
            "cita": cita.data[0],
            "estado_actual": estado_actual.data[0]["estado"] if estado_actual.data else "Sin estado",
            "informacion": info_cita.data[0] if info_cita.data else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.put("/modificar-cita/{cita_id}")
async def modificar_cita(cita_id: int, cita: ActualizarCita):
    """
    Modifica los datos básicos de una cita (fecha, paciente, doctor).
    """
    try:
        # Verificar que la cita existe
        existe = (
            supabase_client
            .table("cita_medica")
            .select("id")
            .eq("id", cita_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Preparar datos a actualizar (solo los que no son None)
        datos_actualizar = {}
        if cita.fecha_atencion:
            datos_actualizar["fecha_atencion"] = cita.fecha_atencion.isoformat()
        if cita.paciente_id:
            # Verificar que el paciente existe
            paciente = supabase_client.table("paciente").select("id").eq("id", cita.paciente_id).execute()
            if not paciente.data:
                raise HTTPException(status_code=404, detail="El paciente no existe.")
            datos_actualizar["paciente_id"] = cita.paciente_id
        if cita.doctor_id:
            # Verificar que el doctor existe
            doctor = supabase_client.table("usuario_sistema").select("id").eq("id", cita.doctor_id).execute()
            if not doctor.data:
                raise HTTPException(status_code=404, detail="El doctor no existe.")
            datos_actualizar["doctor_id"] = cita.doctor_id

        if not datos_actualizar:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar.")

        # Actualizar la cita
        actualizada = (
            supabase_client
            .table("cita_medica")
            .update(datos_actualizar)
            .eq("id", cita_id)
            .execute()
        )

        if not actualizada.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar la cita.")

        return {
            "mensaje": "Cita actualizada exitosamente.",
            "cita": actualizada.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.put("/modificar-informacion/{cita_id}")
async def modificar_informacion_cita(cita_id: int, informacion: ActualizarInformacionCita):
    """
    Modifica la información detallada de una cita.
    """
    try:
        # Verificar que la cita existe
        existe = (
            supabase_client
            .table("cita_medica")
            .select("id")
            .eq("id", cita_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Verificar si ya existe información de la cita
        info_existe = (
            supabase_client
            .table("informacion_cita")
            .select("id")
            .eq("cita_medica_id", cita_id)
            .execute()
        )

        # Preparar datos a actualizar (solo los que no son None)
        datos_actualizar = {}
        if informacion.motivo_consulta is not None:
            datos_actualizar["motivo_consulta"] = informacion.motivo_consulta
        if informacion.antecedentes is not None:
            datos_actualizar["antecedentes"] = informacion.antecedentes
        if informacion.dolores_sintomas is not None:
            datos_actualizar["dolores_sintomas"] = informacion.dolores_sintomas
        if informacion.atenciones_quirurgicas is not None:
            datos_actualizar["atenciones_quirurgicas"] = informacion.atenciones_quirurgicas
        if informacion.evaluacion_doctor is not None:
            datos_actualizar["evaluacion_doctor"] = informacion.evaluacion_doctor
        if informacion.tratamiento is not None:
            datos_actualizar["tratamiento"] = informacion.tratamiento
        if informacion.diagnostico_id is not None:
            datos_actualizar["diagnostico_id"] = informacion.diagnostico_id

        if not datos_actualizar:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar.")

        if info_existe.data:
            # Actualizar información existente
            actualizada = (
                supabase_client
                .table("informacion_cita")
                .update(datos_actualizar)
                .eq("cita_medica_id", cita_id)
                .execute()
            )
        else:
            # Crear nueva información
            datos_actualizar["cita_medica_id"] = cita_id
            actualizada = (
                supabase_client
                .table("informacion_cita")
                .insert(datos_actualizar)
                .execute()
            )

        if not actualizada.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar la información.")

        return {
            "mensaje": "Información de la cita actualizada exitosamente.",
            "informacion": actualizada.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.put("/cambiar-estado/{cita_id}")
async def cambiar_estado(cita_id: int, cambio: CambiarEstado):
    """
    Cambia el estado de una cita. Inserta un nuevo registro en el historial de estados.
    Estados válidos: Pendiente, Confirmada, En Consulta, Completada, Cancelada
    """
    try:
        # Verificar que la cita existe
        existe = (
            supabase_client
            .table("cita_medica")
            .select("id")
            .eq("id", cita_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Validar estado
        estados_validos = ["Pendiente", "Confirmada", "En Consulta", "Completada", "Cancelada"]
        if cambio.estado not in estados_validos:
            raise HTTPException(
                status_code=400, 
                detail=f"Estado inválido. Estados válidos: {', '.join(estados_validos)}"
            )

        # Insertar nuevo estado en el historial
        nuevo_estado = (
            supabase_client
            .table("estado")
            .insert({
                "estado": cambio.estado,
                "cita_medica_id": cita_id
            })
            .execute()
        )

        if not nuevo_estado.data:
            raise HTTPException(status_code=500, detail="No se pudo cambiar el estado.")

        return {
            "mensaje": f"Estado cambiado a '{cambio.estado}' exitosamente.",
            "estado": nuevo_estado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/historial-estados/{cita_id}")
async def obtener_historial_estados(cita_id: int):
    """
    Obtiene el historial completo de cambios de estado de una cita.
    """
    try:
        # Verificar que la cita existe
        existe = (
            supabase_client
            .table("cita_medica")
            .select("id")
            .eq("id", cita_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Obtener historial de estados
        historial = (
            supabase_client
            .table("estado")
            .select("*")
            .eq("cita_medica_id", cita_id)
            .order("id", desc=False)
            .execute()
        )

        if not historial.data:
            return {"historial": []}

        return {"historial": historial.data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.delete("/cancelar-cita/{cita_id}")
async def cancelar_cita(cita_id: int):
    """
    Cancela una cita cambiando su estado a 'Cancelada'.
    """
    try:
        # Verificar que la cita existe
        existe = (
            supabase_client
            .table("cita_medica")
            .select("id")
            .eq("id", cita_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Insertar estado 'Cancelada'
        cancelada = (
            supabase_client
            .table("estado")
            .insert({
                "estado": "Cancelada",
                "cita_medica_id": cita_id
            })
            .execute()
        )

        if not cancelada.data:
            raise HTTPException(status_code=500, detail="No se pudo cancelar la cita.")

        return {
            "mensaje": "Cita cancelada exitosamente.",
            "estado": cancelada.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/listar-especialidades")
async def listar_especialidades():
    """
    Lista todas las especialidades disponibles.
    """
    try:
        especialidades = (
            supabase_client
            .table("especialidad")
            .select("id, nombre, descripcion")
            .order("nombre", desc=False)
            .execute()
        )

        if not especialidades.data:
            return {"especialidades": []}

        return {"especialidades": especialidades.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/listar-doctores")
async def listar_doctores(especialidad_id: Optional[int] = None):
    """
    Lista todos los doctores disponibles para asignar a citas.
    Si se proporciona especialidad_id, filtra solo los doctores de esa especialidad.
    """
    try:
        if especialidad_id:
            # Obtener doctores filtrados por especialidad
            doctores_especialidad = (
                supabase_client
                .table("especialidades_doctor")
                .select("usuario_sistema_id")
                .eq("especialidad_id", especialidad_id)
                .execute()
            )

            if not doctores_especialidad.data:
                return {"doctores": []}

            # Extraer IDs de doctores
            doctor_ids = [item["usuario_sistema_id"] for item in doctores_especialidad.data]

            # Obtener información completa de los doctores
            doctores = (
                supabase_client
                .table("usuario_sistema")
                .select("id, nombre, apellido_paterno, apellido_materno, email")
                .in_("id", doctor_ids)
                .order("nombre", desc=False)
                .execute()
            )
        else:
            # Obtener todos los doctores
            doctores = (
                supabase_client
                .table("usuario_sistema")
                .select("id, nombre, apellido_paterno, apellido_materno, email")
                .order("nombre", desc=False)
                .execute()
            )

        if not doctores.data:
            return {"doctores": []}

        return {"doctores": doctores.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/estadisticas")
async def obtener_estadisticas(fecha: Optional[str] = None):
    """
    Obtiene estadísticas de citas (total, por estado).
    Si se proporciona fecha, filtra por ese día usando zona horaria de Chile.
    OPTIMIZADO: Usa vista materializada para estadísticas pre-calculadas.
    """
    try:
        from datetime import datetime
        import pytz

        # Si se proporciona fecha, usar vista materializada
        if fecha:
            # Consultar vista materializada directamente
            resultado = (
                supabase_client
                .table("vista_estadisticas_diarias")
                .select("*")
                .eq("fecha", fecha)
                .execute()
            )

            if resultado.data and len(resultado.data) > 0:
                stats = resultado.data[0]
                return {
                    "total": stats.get("total", 0),
                    "confirmadas": stats.get("confirmadas", 0),
                    "pendientes": stats.get("pendientes", 0),
                    "en_consulta": stats.get("en_consulta", 0),
                    "completadas": stats.get("completadas", 0),
                    "canceladas": stats.get("canceladas", 0)
                }
            else:
                # Fecha sin datos
                return {
                    "total": 0,
                    "confirmadas": 0,
                    "pendientes": 0,
                    "en_consulta": 0,
                    "completadas": 0,
                    "canceladas": 0
                }
        else:
            # Sin filtro de fecha, sumar todas las estadísticas de la vista
            resultado = (
                supabase_client
                .table("vista_estadisticas_diarias")
                .select("*")
                .execute()
            )

            if not resultado.data:
                return {
                    "total": 0,
                    "confirmadas": 0,
                    "pendientes": 0,
                    "en_consulta": 0,
                    "completadas": 0,
                    "canceladas": 0
                }

            # Sumar todas las filas de la vista
            estadisticas = {
                "total": sum(row.get("total", 0) for row in resultado.data),
                "confirmadas": sum(row.get("confirmadas", 0) for row in resultado.data),
                "pendientes": sum(row.get("pendientes", 0) for row in resultado.data),
                "en_consulta": sum(row.get("en_consulta", 0) for row in resultado.data),
                "completadas": sum(row.get("completadas", 0) for row in resultado.data),
                "canceladas": sum(row.get("canceladas", 0) for row in resultado.data)
            }

            return estadisticas

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.post("/procesar-pago")
async def procesar_pago(pago: CrearPago):
    """
    Procesa el pago de una cita médica.
    - Registra el pago en la tabla 'pagos'
    - Si hay descuento, registra el detalle
    - Cambia el estado de la cita a 'Confirmada'
    """
    try:
        # Verificar que la cita existe
        cita = (
            supabase_client
            .table("cita_medica")
            .select("id, doctor_id")
            .eq("id", pago.cita_medica_id)
            .execute()
        )
        if not cita.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Validar tipo de pago
        tipos_pago_validos = ["Efectivo", "Tarjeta de Débito", "Tarjeta de Crédito", "Transferencia"]
        if pago.tipo_pago not in tipos_pago_validos:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de pago inválido. Valores válidos: {', '.join(tipos_pago_validos)}"
            )

        # Verificar que no exista ya un pago para esta cita
        pago_existe = (
            supabase_client
            .table("pagos")
            .select("id")
            .eq("cita_medica_id", pago.cita_medica_id)
            .execute()
        )
        if pago_existe.data:
            raise HTTPException(status_code=409, detail="Ya existe un pago registrado para esta cita.")

        # Calcular el total después del descuento
        monto_final = pago.total
        if pago.descuento_aseguradora:
            if pago.descuento_aseguradora < 0 or pago.descuento_aseguradora > 100:
                raise HTTPException(status_code=400, detail="El descuento debe estar entre 0 y 100%")
            monto_final = pago.total * (1 - pago.descuento_aseguradora / 100)

        # Crear el registro de pago
        nuevo_pago = (
            supabase_client
            .table("pagos")
            .insert({
                "fecha_pago": datetime.now().isoformat(),
                "tipo_pago": pago.tipo_pago,
                "total": monto_final,
                "cita_medica_id": pago.cita_medica_id
            })
            .execute()
        )

        if not nuevo_pago.data:
            raise HTTPException(status_code=500, detail="No se pudo registrar el pago.")

        pago_id = nuevo_pago.data[0]["id"]

        # Si hay descuento, crear el registro de detalle
        if pago.descuento_aseguradora and pago.descuento_aseguradora > 0:
            # Obtener el doctor de la cita para obtener su especialidad
            doctor_id = cita.data[0]["doctor_id"]

            # Obtener la especialidad del doctor
            especialidad_doctor = (
                supabase_client
                .table("especialidades_doctor")
                .select("especialidad_id")
                .eq("usuario_sistema_id", doctor_id)
                .limit(1)
                .execute()
            )

            if especialidad_doctor.data:
                especialidad_id = especialidad_doctor.data[0]["especialidad_id"]

                # Obtener el costo_servicio_id de esta especialidad
                costo_servicio = (
                    supabase_client
                    .table("costos_servicio")
                    .select("id")
                    .eq("especialidad_id", especialidad_id)
                    .limit(1)
                    .execute()
                )

                if costo_servicio.data:
                    costo_servicio_id = costo_servicio.data[0]["id"]

                    # Crear el registro de detalle con el motivo del descuento
                    supabase_client.table("detalle").insert({
                        "descuento_aseguradora": pago.descuento_aseguradora,
                        "costo_servicio_id": costo_servicio_id,
                        "pago_id": pago_id
                    }).execute()

        # Cambiar el estado de la cita a "Confirmada"
        supabase_client.table("estado").insert({
            "estado": "Confirmada",
            "cita_medica_id": pago.cita_medica_id
        }).execute()

        return {
            "mensaje": "Pago procesado exitosamente.",
            "pago": nuevo_pago.data[0],
            "monto_original": pago.total,
            "descuento_aplicado": pago.descuento_aseguradora or 0,
            "monto_final": monto_final
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/listar-pagos")
async def listar_pagos():
    """
    Lista todos los pagos procesados con información completa de paciente, doctor, especialidad y cita.
    OPTIMIZADO: Usa JOINs y bulk queries para eliminar N+1.
    """
    try:
        # Query 1: Obtener todos los pagos con información de cita mediante JOIN
        pagos_response = (
            supabase_client
            .table("pagos")
            .select("""
                *,
                cita_medica:cita_medica_id(
                    id,
                    paciente_id,
                    doctor_id,
                    horario_id,
                    especialidad_id,
                    fecha_atencion
                )
            """)
            .order("fecha_pago", desc=True)
            .execute()
        )

        if not pagos_response.data:
            return {"pagos": []}

        # Extraer IDs únicos para bulk queries
        paciente_ids = set()
        doctor_ids = set()
        especialidad_ids = set()
        
        for pago in pagos_response.data:
            if pago.get("cita_medica"):
                cita = pago["cita_medica"]
                if cita.get("paciente_id"):
                    paciente_ids.add(cita["paciente_id"])
                if cita.get("doctor_id"):
                    doctor_ids.add(cita["doctor_id"])
                if cita.get("especialidad_id"):
                    especialidad_ids.add(cita["especialidad_id"])

        # Query 2: Bulk query para todos los pacientes
        pacientes_dict = {}
        if paciente_ids:
            pacientes_response = (
                supabase_client
                .table("paciente")
                .select("id, nombre, apellido_paterno, apellido_materno, rut, telefono, correo")
                .in_("id", list(paciente_ids))
                .execute()
            )
            pacientes_dict = {p["id"]: p for p in pacientes_response.data}

        # Query 3: Bulk query para todos los doctores
        doctores_dict = {}
        if doctor_ids:
            doctores_response = (
                supabase_client
                .table("usuario_sistema")
                .select("id, nombre, apellido_paterno, apellido_materno")
                .in_("id", list(doctor_ids))
                .execute()
            )
            doctores_dict = {d["id"]: d for d in doctores_response.data}

        # Query 4: Bulk query para todas las especialidades
        especialidades_dict = {}
        if especialidad_ids:
            especialidades_response = (
                supabase_client
                .table("especialidad")
                .select("id, nombre")
                .in_("id", list(especialidad_ids))
                .execute()
            )
            especialidades_dict = {e["id"]: e for e in especialidades_response.data}

        # Query 5: Bulk query para especialidades de doctores (si alguna cita no tiene especialidad)
        doctores_sin_especialidad = []
        for pago in pagos_response.data:
            if pago.get("cita_medica"):
                cita = pago["cita_medica"]
                if not cita.get("especialidad_id") and cita.get("doctor_id"):
                    doctores_sin_especialidad.append(cita["doctor_id"])

        doctor_especialidades_dict = {}
        if doctores_sin_especialidad:
            doctor_esp_response = (
                supabase_client
                .table("especialidades_doctor")
                .select("usuario_sistema_id, especialidad_id")
                .in_("usuario_sistema_id", list(set(doctores_sin_especialidad)))
                .execute()
            )
            
            # Mapear especialidades por doctor (primera especialidad encontrada)
            for de in doctor_esp_response.data:
                if de["usuario_sistema_id"] not in doctor_especialidades_dict:
                    doctor_especialidades_dict[de["usuario_sistema_id"]] = de["especialidad_id"]
            
            # Obtener los datos de esas especialidades si no las tenemos ya
            especialidad_ids_adicionales = set(doctor_especialidades_dict.values()) - especialidad_ids
            if especialidad_ids_adicionales:
                especialidades_adicionales_response = (
                    supabase_client
                    .table("especialidad")
                    .select("id, nombre")
                    .in_("id", list(especialidad_ids_adicionales))
                    .execute()
                )
                for e in especialidades_adicionales_response.data:
                    especialidades_dict[e["id"]] = e

        # Ensamblar respuesta usando los diccionarios
        pagos_completos = []
        for pago in pagos_response.data:
            if not pago.get("cita_medica"):
                continue

            cita = pago["cita_medica"]
            
            # Obtener paciente, doctor y especialidad de los diccionarios
            paciente = pacientes_dict.get(cita.get("paciente_id"))
            doctor = doctores_dict.get(cita.get("doctor_id"))
            
            # Obtener especialidad (de la cita o del doctor)
            especialidad = None
            if cita.get("especialidad_id"):
                especialidad = especialidades_dict.get(cita["especialidad_id"])
            elif cita.get("doctor_id") in doctor_especialidades_dict:
                esp_id = doctor_especialidades_dict[cita["doctor_id"]]
                especialidad = especialidades_dict.get(esp_id)

            if paciente and doctor:
                pagos_completos.append({
                    "pago": pago,
                    "cita_id": cita["id"],
                    "fecha_atencion": cita["fecha_atencion"],
                    "paciente": paciente,
                    "doctor": doctor,
                    "especialidad": especialidad
                })

        return {"pagos": pagos_completos}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar pagos: {str(e)}")


@appointment_router.get("/ingresos")
async def obtener_ingresos(fecha: Optional[str] = None):
    """
    Obtiene los ingresos totales.
    Si se proporciona fecha, filtra por ese día.
    """
    try:
        query = supabase_client.table("pagos").select("total, fecha_pago")

        if fecha:
            query = query.gte("fecha_pago", f"{fecha}T00:00:00").lte("fecha_pago", f"{fecha}T23:59:59")

        pagos = query.execute()

        if not pagos.data:
            return {
                "total_ingresos": 0,
                "cantidad_pagos": 0,
                "promedio_pago": 0
            }

        total_ingresos = sum(float(p["total"]) for p in pagos.data)
        cantidad_pagos = len(pagos.data)
        promedio_pago = total_ingresos / cantidad_pagos if cantidad_pagos > 0 else 0

        return {
            "total_ingresos": round(total_ingresos, 2),
            "cantidad_pagos": cantidad_pagos,
            "promedio_pago": round(promedio_pago, 2)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/precio-especialidad/{especialidad_id}")
async def obtener_precio_especialidad(especialidad_id: int):
    """
    Obtiene el precio de consulta de una especialidad.
    """
    try:
        costo = (
            supabase_client
            .table("costos_servicio")
            .select("id, servicio, precio")
            .eq("especialidad_id", especialidad_id)
            .execute()
        )

        if not costo.data:
            raise HTTPException(
                status_code=404,
                detail="No se encontró un precio para esta especialidad."
            )

        return {"costo_servicio": costo.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== NUEVOS ENDPOINTS PARA EL DOCTOR ==============

@appointment_router.get("/doctor/{doctor_id}/citas")
async def obtener_citas_doctor(
    doctor_id: int,
    fecha: Optional[str] = None,
    estados: Optional[str] = None
):
    """
    Obtiene las citas de un doctor específico filtradas por fecha y estados.
    estados: string separado por comas, ej: "Confirmada,En Consulta"
    """
    try:
        print(f"🔍 DEBUG - Doctor ID recibido: {doctor_id}")
        print(f"🔍 DEBUG - Fecha recibida: {fecha}")
        print(f"🔍 DEBUG - Estados recibidos: {estados}")
        
        # Construir query base
        query = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                paciente:paciente_id(
                    id, nombre, apellido_paterno, apellido_materno, 
                    fecha_nacimiento, telefono, rut, correo, sexo,
                    estado_civil, direccion, ocupacion, alergias
                )
            """)
            .eq("doctor_id", doctor_id)
        )

        # Filtrar por fecha si se proporciona
        if fecha:
            query = query.gte("fecha_atencion", f"{fecha}T00:00:00").lte("fecha_atencion", f"{fecha}T23:59:59")

        citas = query.order("fecha_atencion", desc=False).execute()
        
        print(f"🔍 DEBUG - Citas encontradas (antes de filtrar por estado): {len(citas.data) if citas.data else 0}")

        if not citas.data:
            return {"citas": []}

        # Obtener estados y filtrar
        lista_estados = estados.split(",") if estados else []
        print(f"🔍 DEBUG - Lista de estados para filtrar: {lista_estados}")
        citas_filtradas = []

        for cita in citas.data:
            # Obtener estado actual
            estado_actual = (
                supabase_client
                .table("estado")
                .select("estado")
                .eq("cita_medica_id", cita["id"])
                .order("id", desc=True)
                .limit(1)
                .execute()
            )

            estado_texto = estado_actual.data[0]["estado"] if estado_actual.data else "Sin estado"
            print(f"🔍 DEBUG - Cita ID {cita['id']}: Estado = {estado_texto}")

            # Filtrar por estados si se especificó
            if lista_estados and estado_texto not in lista_estados:
                continue

            # Obtener información de la cita si existe
            info_cita = (
                supabase_client
                .table("informacion_cita")
                .select("motivo_consulta")
                .eq("cita_medica_id", cita["id"])
                .execute()
            )

            citas_filtradas.append({
                **cita,
                "estado_actual": estado_texto,
                "motivo_consulta": info_cita.data[0]["motivo_consulta"] if info_cita.data else None
            })

        return {"citas": citas_filtradas}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/doctor/{doctor_id}/stats")
async def obtener_stats_doctor(doctor_id: int, fecha: Optional[str] = None):
    """
    Obtiene las estadísticas del dashboard del doctor.
    Si no se proporciona fecha, usa la fecha actual.
    OPTIMIZADO: Usa función SQL con agregaciones pre-calculadas (con fallback).
    """
    try:
        from datetime import date as date_module
        import calendar
        
        # Usar fecha actual si no se proporciona
        fecha_actual = fecha or date_module.today().isoformat()
        print(f"🔍 DEBUG Stats - Doctor ID: {doctor_id}, Fecha: {fecha_actual}")
        
        # Intentar usar la función SQL optimizada
        try:
            resultado = supabase_client.rpc(
                "obtener_stats_doctor",
                {
                    "p_doctor_id": doctor_id,
                    "fecha_filtro": fecha_actual
                }
            ).execute()

            if resultado.data and len(resultado.data) > 0:
                stats = resultado.data[0]
                print(f"🔍 DEBUG Stats - Resultado: {stats}")
                return stats
        except Exception as rpc_error:
            print(f"⚠️ RPC no disponible, usando fallback: {str(rpc_error)}")

        # FALLBACK: Query optimizada con bulk
        # Obtener todas las citas del día
        citas_hoy = (
            supabase_client
            .table("cita_medica")
            .select("id")
            .eq("doctor_id", doctor_id)
            .gte("fecha_atencion", f"{fecha_actual}T00:00:00-03:00")
            .lte("fecha_atencion", f"{fecha_actual}T23:59:59-03:00")
            .execute()
        )

        print(f"🔍 DEBUG Stats - Citas hoy: {len(citas_hoy.data) if citas_hoy.data else 0}")

        # Contar por estados con bulk query
        total_hoy = 0
        atendidos_hoy = 0
        pendientes_hoy = 0
        cancelados_hoy = 0

        if citas_hoy.data:
            citas_ids = [c["id"] for c in citas_hoy.data]
            
            # Bulk query de estados
            estados = (
                supabase_client
                .table("estado")
                .select("cita_medica_id, estado, id")
                .in_("cita_medica_id", citas_ids)
                .order("id", desc=True)
                .execute()
            )
            
            estados_dict = {}
            for est in (estados.data or []):
                if est["cita_medica_id"] not in estados_dict:
                    estados_dict[est["cita_medica_id"]] = est["estado"]
            
            for cita in citas_hoy.data:
                if cita["id"] in estados_dict:
                    estado_actual = estados_dict[cita["id"]]
                    total_hoy += 1
                    
                    if estado_actual == "Completada":
                        atendidos_hoy += 1
                    elif estado_actual in ["Pendiente", "Confirmada", "En Consulta"]:
                        pendientes_hoy += 1
                    elif estado_actual == "Cancelada":
                        cancelados_hoy += 1

        # Obtener total de pacientes del mes
        año_mes = fecha_actual[:7]  # YYYY-MM
        año = int(fecha_actual[:4])
        mes = int(fecha_actual[5:7])
        
        # Obtener el último día del mes
        ultimo_dia = calendar.monthrange(año, mes)[1]
        
        print(f"🔍 DEBUG Stats - Buscando citas del mes: {año_mes}-01 al {año_mes}-{ultimo_dia}")
        
        citas_mes = (
            supabase_client
            .table("cita_medica")
            .select("paciente_id")
            .eq("doctor_id", doctor_id)
            .gte("fecha_atencion", f"{año_mes}-01T00:00:00-03:00")
            .lte("fecha_atencion", f"{año_mes}-{ultimo_dia}T23:59:59-03:00")
            .execute()
        )

        print(f"🔍 DEBUG Stats - Citas del mes: {len(citas_mes.data) if citas_mes.data else 0}")

        # Contar pacientes únicos del mes
        pacientes_unicos = set()
        if citas_mes.data:
            for cita in citas_mes.data:
                pacientes_unicos.add(cita["paciente_id"])

        resultado = {
            "citas_hoy": total_hoy,
            "atendidos_hoy": atendidos_hoy,
            "pendientes_hoy": pendientes_hoy,
            "cancelados_hoy": cancelados_hoy,
            "total_pacientes_mes": len(pacientes_unicos)
        }
        
        print(f"🔍 DEBUG Stats - Resultado: {resultado}")
        
        return resultado

    except Exception as e:
        print(f"❌ ERROR en stats: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.put("/cita/{cita_id}/cambiar-estado")
async def cambiar_estado_cita(cita_id: int, cambio: CambiarEstado):
    """
    Cambia el estado de una cita.
    Estados válidos: Pendiente, Confirmada, En Consulta, Completada, Cancelada
    """
    try:
        # Verificar que la cita existe
        cita = (
            supabase_client
            .table("cita_medica")
            .select("id")
            .eq("id", cita_id)
            .execute()
        )

        if not cita.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Crear nuevo estado
        nuevo_estado = (
            supabase_client
            .table("estado")
            .insert({
                "estado": cambio.estado,
                "cita_medica_id": cita_id
            })
            .execute()
        )

        return {
            "mensaje": f"Estado cambiado a '{cambio.estado}' exitosamente.",
            "estado": nuevo_estado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/cita/{cita_id}/detalle-completo")
async def obtener_detalle_completo_cita(cita_id: int):
    """
    Obtiene toda la información de una cita incluyendo paciente, doctor, información de consulta y recetas.
    """
    try:
        # Obtener cita con información del paciente y doctor
        cita = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                doctor_id,
                paciente:paciente_id(
                    id, nombre, apellido_paterno, apellido_materno,
                    fecha_nacimiento, sexo, estado_civil, rut,
                    direccion, telefono, correo, ocupacion,
                    persona_responsable, alergias
                ),
                doctor:doctor_id(
                    id, nombre, apellido_paterno, apellido_materno, rut
                )
            """)
            .eq("id", cita_id)
            .execute()
        )

        if not cita.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Obtener estado actual
        estado = (
            supabase_client
            .table("estado")
            .select("estado")
            .eq("cita_medica_id", cita_id)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )

        # Obtener información de consulta
        info_cita = (
            supabase_client
            .table("informacion_cita")
            .select("*")
            .eq("cita_medica_id", cita_id)
            .execute()
        )

        # Obtener recetas si existen
        recetas = []
        if info_cita.data:
            recetas_data = (
                supabase_client
                .table("receta")
                .select("*")
                .eq("informacion_cita_id", info_cita.data[0]["id"])
                .execute()
            )
            recetas = recetas_data.data if recetas_data.data else []

        return {
            "cita": cita.data[0],
            "estado_actual": estado.data[0]["estado"] if estado.data else "Sin estado",
            "informacion_consulta": info_cita.data[0] if info_cita.data else None,
            "recetas": recetas
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/paciente/{paciente_id}/historial-medico")
async def obtener_historial_medico(paciente_id: int):
    """
    Obtiene el historial médico completo de un paciente.
    Retorna todas las consultas completadas con su información detallada.
    """
    try:
        # Obtener todas las citas del paciente ordenadas por fecha (más reciente primero)
        citas_response = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                doctor_id,
                especialidad_id,
                doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno),
                especialidad:especialidad_id(id, nombre)
            """)
            .eq("paciente_id", paciente_id)
            .order("fecha_atencion", desc=True)
            .execute()
        )

        if not citas_response.data:
            return {"historial": []}

        historial = []

        for cita in citas_response.data:
            # Obtener estado actual de la cita
            estado_response = (
                supabase_client
                .table("estado")
                .select("estado")
                .eq("cita_medica_id", cita["id"])
                .order("id", desc=True)
                .limit(1)
                .execute()
            )

            estado_actual = estado_response.data[0]["estado"] if estado_response.data else "Sin estado"

            # Solo incluir citas completadas en el historial
            if estado_actual != "Completada":
                continue

            # Obtener información de la consulta
            info_consulta_response = (
                supabase_client
                .table("informacion_cita")
                .select("*")
                .eq("cita_medica_id", cita["id"])
                .execute()
            )

            info_consulta = None
            diagnostico = None
            recetas = []

            if info_consulta_response.data:
                info_consulta = info_consulta_response.data[0]

                # Obtener diagnóstico si existe
                if info_consulta.get("diagnostico_id"):
                    diagnostico_response = (
                        supabase_client
                        .table("diagnosticos")
                        .select("id, nombre_enfermedad")
                        .eq("id", info_consulta["diagnostico_id"])
                        .execute()
                    )
                    if diagnostico_response.data:
                        diagnostico = diagnostico_response.data[0]

                # Obtener recetas
                recetas_response = (
                    supabase_client
                    .table("receta")
                    .select("*")
                    .eq("informacion_cita_id", info_consulta["id"])
                    .execute()
                )
                recetas = recetas_response.data if recetas_response.data else []

            # Construir objeto de consulta
            consulta_data = {
                "cita_id": cita["id"],
                "fecha_atencion": cita["fecha_atencion"],
                "doctor": cita.get("doctor"),
                "especialidad": cita.get("especialidad"),
                "informacion_consulta": {
                    "motivo_consulta": info_consulta.get("motivo_consulta") if info_consulta else None,
                    "antecedentes": info_consulta.get("antecedentes") if info_consulta else None,
                    "dolores_sintomas": info_consulta.get("dolores_sintomas") if info_consulta else None,
                    "atenciones_quirurgicas": info_consulta.get("atenciones_quirurgicas") if info_consulta else None,
                    "evaluacion_doctor": info_consulta.get("evaluacion_doctor") if info_consulta else None,
                    "tratamiento": info_consulta.get("tratamiento") if info_consulta else None,
                    "diagnostico": diagnostico
                },
                "recetas": recetas
            }

            historial.append(consulta_data)

        return {"historial": historial}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.put("/cita/{cita_id}/guardar-consulta")
async def guardar_consulta(cita_id: int, consulta: GuardarConsulta):
    """
    Guarda o actualiza la información de una consulta (borrador o final).
    """
    try:
        # Verificar que la cita existe
        cita = (
            supabase_client
            .table("cita_medica")
            .select("id")
            .eq("id", cita_id)
            .execute()
        )

        if not cita.data:
            raise HTTPException(status_code=404, detail="La cita no existe.")

        # Verificar si ya existe información de la cita
        info_existente = (
            supabase_client
            .table("informacion_cita")
            .select("id")
            .eq("cita_medica_id", cita_id)
            .execute()
        )

        # Preparar datos para información de cita
        datos_info = {
            "cita_medica_id": cita_id,
            "motivo_consulta": consulta.motivo_consulta,
            "antecedentes": consulta.antecedentes,
            "dolores_sintomas": consulta.dolores_sintomas or "No aplica dolor",
            "atenciones_quirurgicas": consulta.atenciones_quirurgicas or "No aplica",
            "evaluacion_doctor": consulta.evaluacion_doctor,
            "tratamiento": consulta.tratamiento
        }

        # Manejar diagnósticos (tomar el primero si hay varios)
        if consulta.diagnostico_ids and len(consulta.diagnostico_ids) > 0:
            datos_info["diagnostico_id"] = consulta.diagnostico_ids[0]

        info_cita_id = None

        if info_existente.data:
            # Actualizar información existente
            info_actualizada = (
                supabase_client
                .table("informacion_cita")
                .update(datos_info)
                .eq("id", info_existente.data[0]["id"])
                .execute()
            )
            info_cita_id = info_existente.data[0]["id"]

            # Eliminar recetas anteriores
            supabase_client.table("receta").delete().eq("informacion_cita_id", info_cita_id).execute()
        else:
            # Crear nueva información de cita
            nueva_info = (
                supabase_client
                .table("informacion_cita")
                .insert(datos_info)
                .execute()
            )
            info_cita_id = nueva_info.data[0]["id"]

        # Guardar recetas si existen
        if consulta.recetas:
            for receta in consulta.recetas:
                supabase_client.table("receta").insert({
                    "nombre": receta.nombre,
                    "presentacion": receta.presentacion,
                    "dosis": receta.dosis,
                    "duracion": receta.duracion,
                    "cantidad": receta.cantidad,
                    "informacion_cita_id": info_cita_id
                }).execute()

        return {
            "mensaje": "Consulta guardada exitosamente.",
            "informacion_cita_id": info_cita_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/diagnosticos")
async def listar_diagnosticos():
    """
    Lista todos los diagnósticos disponibles.
    """
    try:
        diagnosticos = (
            supabase_client
            .table("diagnosticos")
            .select("id, nombre_enfermedad")
            .order("nombre_enfermedad", desc=False)
            .execute()
        )

        return {"diagnosticos": diagnosticos.data if diagnosticos.data else []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/doctor/{doctor_id}/cita-en-consulta")
async def obtener_cita_en_consulta(doctor_id: int):
    """
    Obtiene la cita que está actualmente en consulta para un doctor.
    Retorna None si no hay ninguna cita en consulta.
    """
    try:
        # Obtener todas las citas del doctor
        citas = (
            supabase_client
            .table("cita_medica")
            .select("id, fecha_atencion")
            .eq("doctor_id", doctor_id)
            .execute()
        )

        if not citas.data:
            return {"cita_en_consulta": None}

        # Buscar la que esté en consulta
        for cita in citas.data:
            estado = (
                supabase_client
                .table("estado")
                .select("estado")
                .eq("cita_medica_id", cita["id"])
                .order("id", desc=True)
                .limit(1)
                .execute()
            )

            if estado.data and estado.data[0]["estado"] == "En Consulta":
                return {"cita_en_consulta": cita["id"]}

        return {"cita_en_consulta": None}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        costo = (
            supabase_client
            .table("costos_servicio")
            .select("precio, servicio")
            .eq("especialidad_id", especialidad_id)
            .execute()
        )

        if not costo.data:
            raise HTTPException(status_code=404, detail="No se encontró el precio para esta especialidad.")

        return {
            "precio": costo.data[0]["precio"],
            "servicio": costo.data[0]["servicio"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/doctor/{doctor_id}/pacientes-atendidos")
async def obtener_pacientes_atendidos(doctor_id: int):
    """
    Obtiene la lista de pacientes únicos que un doctor ha atendido (consultas completadas).
    Retorna información básica del paciente y la fecha de última atención.
    """
    try:
        # Obtener todas las citas completadas del doctor
        citas_response = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                paciente_id,
                paciente:paciente_id(id, nombre, apellido_paterno, apellido_materno, rut, fecha_nacimiento)
            """)
            .eq("doctor_id", doctor_id)
            .order("fecha_atencion", desc=True)
            .execute()
        )

        if not citas_response.data:
            return {"pacientes": []}

        # Diccionario para almacenar pacientes únicos con su última consulta
        pacientes_map = {}

        for cita in citas_response.data:
            # Verificar que la cita esté completada
            estado_response = (
                supabase_client
                .table("estado")
                .select("estado")
                .eq("cita_medica_id", cita["id"])
                .order("id", desc=True)
                .limit(1)
                .execute()
            )

            if not estado_response.data or estado_response.data[0]["estado"] != "Completada":
                continue

            paciente = cita.get("paciente")
            if not paciente:
                continue

            paciente_id = paciente["id"]

            # Si el paciente no está en el map o esta cita es más reciente, actualizar
            if paciente_id not in pacientes_map:
                # Calcular edad
                edad = None
                if paciente.get("fecha_nacimiento"):
                    try:
                        fecha_nac = datetime.strptime(str(paciente["fecha_nacimiento"]), "%Y-%m-%d")
                        hoy = datetime.now()
                        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
                    except:
                        edad = None

                pacientes_map[paciente_id] = {
                    "id": paciente["id"],
                    "nombre": paciente.get("nombre", ""),
                    "apellido_paterno": paciente.get("apellido_paterno", ""),
                    "apellido_materno": paciente.get("apellido_materno", ""),
                    "nombre_completo": f"{paciente.get('nombre', '')} {paciente.get('apellido_paterno', '')} {paciente.get('apellido_materno', '')}".strip(),
                    "rut": paciente.get("rut", ""),
                    "edad": edad,
                    "ultima_atencion": cita["fecha_atencion"]
                }

        # Convertir a lista y ordenar por última atención (más reciente primero)
        pacientes_list = list(pacientes_map.values())
        pacientes_list.sort(key=lambda x: x["ultima_atencion"], reverse=True)

        return {"pacientes": pacientes_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== ENDPOINTS PARA SECRETARIA ==============

@appointment_router.get("/hoy/pendientes")
async def obtener_citas_pendientes_hoy():
    """
    Obtiene todas las citas del día actual en estado 'Pendiente'.
    Retorna información de paciente, doctor, especialidad y hora.
    OPTIMIZADO: Usa función SQL con filtrado directo (con fallback).
    """
    try:
        from datetime import datetime
        import pytz

        # Obtener fecha actual en zona horaria de Chile
        tz_chile = pytz.timezone('America/Santiago')
        ahora_chile = datetime.now(tz_chile)
        fecha_actual = ahora_chile.date().isoformat()

        # Intentar usar la función SQL optimizada
        try:
            resultado = supabase_client.rpc(
                "obtener_citas_pendientes_hoy",
                {"fecha_filtro": fecha_actual}
            ).execute()

            if resultado.data:
                return {"citas": resultado.data}
        except Exception as rpc_error:
            print(f"⚠️ RPC no disponible, usando fallback: {str(rpc_error)}")

        # FALLBACK: Query optimizada con bulk
        citas = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                paciente:paciente_id(id, nombre, apellido_paterno, apellido_materno, rut, telefono),
                doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno),
                especialidad:especialidad_id(id, nombre)
            """)
            .gte("fecha_atencion", f"{fecha_actual}T00:00:00-03:00")
            .lte("fecha_atencion", f"{fecha_actual}T23:59:59-03:00")
            .order("fecha_atencion", desc=False)
            .execute()
        )

        if not citas.data:
            return {"citas": []}

        # Obtener estados en bulk
        citas_ids = [c["id"] for c in citas.data]
        estados = (
            supabase_client
            .table("estado")
            .select("cita_medica_id, estado, id")
            .in_("cita_medica_id", citas_ids)
            .order("id", desc=True)
            .execute()
        )

        estados_dict = {}
        for est in (estados.data or []):
            if est["cita_medica_id"] not in estados_dict:
                estados_dict[est["cita_medica_id"]] = est["estado"]

        # Filtrar solo pendientes
        citas_pendientes = []
        for cita in citas.data:
            estado_actual = estados_dict.get(cita["id"], "Sin estado")
            if estado_actual.lower() == "pendiente":
                citas_pendientes.append({
                    **cita,
                    "estado_actual": estado_actual
                })

        return {"citas": citas_pendientes}

    except Exception as e:
        print(f"❌ Error en hoy/pendientes: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/hoy/confirmadas")
async def obtener_citas_confirmadas_hoy():
    """
    Obtiene todas las citas del día actual en estado 'Confirmada'.
    Retorna información de paciente, doctor, especialidad y hora.
    """
    try:
        from datetime import date as date_module

        # Obtener fecha actual
        fecha_actual = date_module.today().isoformat()

        # Obtener todas las citas del día
        citas_hoy = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                paciente:paciente_id(id, nombre, apellido_paterno, apellido_materno, rut, telefono),
                doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno),
                especialidad:especialidad_id(id, nombre)
            """)
            .gte("fecha_atencion", f"{fecha_actual}T00:00:00")
            .lte("fecha_atencion", f"{fecha_actual}T23:59:59")
            .order("fecha_atencion", desc=False)
            .execute()
        )

        if not citas_hoy.data:
            return {"citas": []}

        citas_confirmadas = []

        for cita in citas_hoy.data:
            # Obtener estado actual
            estado = (
                supabase_client
                .table("estado")
                .select("estado")
                .eq("cita_medica_id", cita["id"])
                .order("id", desc=True)
                .limit(1)
                .execute()
            )

            estado_texto = estado.data[0]["estado"] if estado.data else "Sin estado"

            # Solo incluir si está en estado Confirmada (case-insensitive)
            if estado_texto.lower() == "confirmada":
                citas_confirmadas.append({
                    **cita,
                    "estado_actual": estado_texto
                })

        return {"citas": citas_confirmadas}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/hoy/todas-estados")
async def obtener_todas_citas_hoy():
    """
    Obtiene todas las citas del día actual con sus estados.
    Útil para ver el panorama completo del día.
    """
    try:
        from datetime import date as date_module

        # Obtener fecha actual
        fecha_actual = date_module.today().isoformat()

        # Obtener todas las citas del día
        citas_hoy = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                paciente:paciente_id(id, nombre, apellido_paterno, apellido_materno, rut, telefono),
                doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno),
                especialidad:especialidad_id(id, nombre)
            """)
            .gte("fecha_atencion", f"{fecha_actual}T00:00:00")
            .lte("fecha_atencion", f"{fecha_actual}T23:59:59")
            .order("fecha_atencion", desc=False)
            .execute()
        )

        if not citas_hoy.data:
            return {"citas": []}

        citas_con_estado = []

        for cita in citas_hoy.data:
            # Obtener estado actual
            estado = (
                supabase_client
                .table("estado")
                .select("estado")
                .eq("cita_medica_id", cita["id"])
                .order("id", desc=True)
                .limit(1)
                .execute()
            )

            estado_texto = estado.data[0]["estado"] if estado.data else "Sin estado"

            citas_con_estado.append({
                **cita,
                "estado_actual": estado_texto
            })

        return {"citas": citas_con_estado}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@appointment_router.get("/actividad-reciente")
async def obtener_actividad_reciente(fecha: Optional[str] = None):
    """
    Obtiene la actividad reciente del día (últimos pagos y últimas citas creadas).
    Si se proporciona fecha, filtra por ese día usando zona horaria de Chile.
    OPTIMIZADO: Usa función SQL con JOINs pre-calculados (con fallback).
    """
    try:
        from datetime import datetime, date as date_module
        import pytz

        # Zona horaria de Chile
        tz_chile = pytz.timezone('America/Santiago')

        # Usar fecha actual de Chile si no se proporciona
        if not fecha:
            ahora_chile = datetime.now(tz_chile)
            fecha_filtro = ahora_chile.date().isoformat()
        else:
            fecha_filtro = fecha

        # Intentar usar la función SQL optimizada
        try:
            resultado = supabase_client.rpc(
                "obtener_actividad_reciente",
                {"fecha_filtro": fecha_filtro}
            ).execute()

            if resultado.data and len(resultado.data) > 0:
                return resultado.data[0]
        except Exception as rpc_error:
            print(f"⚠️ RPC no disponible, usando fallback: {str(rpc_error)}")

        # FALLBACK: Query optimizada con bulk
        # Obtener pagos del día con JOIN
        pagos = (
            supabase_client
            .table("pagos")
            .select("""
                id,
                fecha_pago,
                tipo_pago,
                total,
                cita_medica_id,
                cita_medica:cita_medica_id(
                    paciente:paciente_id(nombre, apellido_paterno, apellido_materno)
                )
            """)
            .gte("fecha_pago", f"{fecha_filtro}T00:00:00-03:00")
            .lte("fecha_pago", f"{fecha_filtro}T23:59:59-03:00")
            .order("fecha_pago", desc=True)
            .limit(10)
            .execute()
        )

        pagos_con_info = []
        for pago in (pagos.data or []):
            paciente = pago.get("cita_medica", {}).get("paciente") if pago.get("cita_medica") else None
            pagos_con_info.append({
                "id": pago["id"],
                "fecha_pago": pago["fecha_pago"],
                "tipo_pago": pago["tipo_pago"],
                "total": pago["total"],
                "cita_medica_id": pago["cita_medica_id"],
                "paciente": paciente
            })

        # Obtener citas del día con JOINs
        citas = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                paciente:paciente_id(id, nombre, apellido_paterno, apellido_materno),
                doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno)
            """)
            .gte("fecha_atencion", f"{fecha_filtro}T00:00:00-03:00")
            .lte("fecha_atencion", f"{fecha_filtro}T23:59:59-03:00")
            .order("id", desc=True)
            .limit(10)
            .execute()
        )

        # Obtener estados en bulk
        if citas.data:
            citas_ids = [c["id"] for c in citas.data]
            estados = (
                supabase_client
                .table("estado")
                .select("cita_medica_id, estado, id")
                .in_("cita_medica_id", citas_ids)
                .order("id", desc=True)
                .execute()
            )

            estados_dict = {}
            for est in (estados.data or []):
                if est["cita_medica_id"] not in estados_dict:
                    estados_dict[est["cita_medica_id"]] = est["estado"]

            citas_con_estado = []
            for cita in citas.data:
                citas_con_estado.append({
                    **cita,
                    "estado_actual": estados_dict.get(cita["id"], "Sin estado")
                })
        else:
            citas_con_estado = []

        return {
            "pagos_recientes": pagos_con_info,
            "citas_recientes": citas_con_estado
        }

    except Exception as e:
        print(f"❌ Error en actividad-reciente: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
