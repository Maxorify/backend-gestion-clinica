from fastapi import APIRouter, HTTPException
from src.models.citas import (
    CrearCitaCompleta, 
    ActualizarCita, 
    ActualizarInformacionCita,
    CambiarEstado
)
from src.utils.supabase import supabase_client
from typing import Optional
from datetime import datetime

appointment_router = APIRouter(tags=["Gestión de Citas Médicas"], prefix="/Citas")


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

        # Verificar que el doctor existe
        doctor = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno")
            .eq("id", cita_completa.cita.doctor_id)
            .execute()
        )
        if not doctor.data:
            raise HTTPException(status_code=404, detail="El doctor no existe.")

        # Si se proporciona horario_id, verificar que esté disponible
        if cita_completa.cita.horario_id:
            # Verificar que el horario existe
            horario = supabase_client.table("horarios_personal").select("id, usuario_sistema_id").eq(
                "id", cita_completa.cita.horario_id
            ).execute()
            
            if not horario.data:
                raise HTTPException(status_code=404, detail="El horario especificado no existe.")
            
            # Verificar que el horario pertenece al doctor
            if horario.data[0]["usuario_sistema_id"] != cita_completa.cita.doctor_id:
                raise HTTPException(status_code=400, detail="El horario no pertenece al doctor seleccionado.")
            
            # Verificar que el horario no esté ocupado
            cita_existente = supabase_client.table("cita_medica").select("id").eq(
                "horario_id", cita_completa.cita.horario_id
            ).execute()
            
            if cita_existente.data:
                raise HTTPException(status_code=409, detail="Este horario ya está ocupado.")

        # Crear la cita médica
        nueva_cita = (
            supabase_client
            .table("cita_medica")
            .insert({
                "fecha_atencion": cita_completa.cita.fecha_atencion.isoformat(),
                "paciente_id": cita_completa.cita.paciente_id,
                "doctor_id": cita_completa.cita.doctor_id,
                "horario_id": cita_completa.cita.horario_id
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
    estado: Optional[str] = None
):
    """
    Lista todas las citas con información del paciente y doctor.
    Filtros opcionales: fecha, doctor_id, estado.
    """
    try:
        # Obtener todas las citas con joins
        query = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                paciente:paciente_id(id, nombre, apellido_paterno, apellido_materno, telefono, rut),
                doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno)
            """)
        )

        # Aplicar filtros
        if fecha:
            query = query.gte("fecha_atencion", f"{fecha}T00:00:00").lte("fecha_atencion", f"{fecha}T23:59:59")
        if doctor_id:
            query = query.eq("doctor_id", doctor_id)

        citas = query.order("fecha_atencion", desc=False).execute()

        if not citas.data:
            return {"citas": []}

        # Para cada cita, obtener el estado actual (último registro)
        citas_con_estado = []
        for cita in citas.data:
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

            # Filtrar por estado si se especificó
            if estado and estado_texto != estado:
                continue

            citas_con_estado.append({
                **cita,
                "estado_actual": estado_texto
            })

        return {"citas": citas_con_estado}

    except Exception as e:
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
    Si se proporciona fecha, filtra por ese día.
    """
    try:
        # Obtener todas las citas
        query = supabase_client.table("cita_medica").select("id")
        
        if fecha:
            query = query.gte("fecha_atencion", f"{fecha}T00:00:00").lte("fecha_atencion", f"{fecha}T23:59:59")
        
        citas = query.execute()

        if not citas.data:
            return {
                "total": 0,
                "confirmadas": 0,
                "pendientes": 0,
                "en_consulta": 0,
                "completadas": 0,
                "canceladas": 0
            }

        # Contar por estado
        estadisticas = {
            "total": len(citas.data),
            "confirmadas": 0,
            "pendientes": 0,
            "en_consulta": 0,
            "completadas": 0,
            "canceladas": 0
        }

        for cita in citas.data:
            # Obtener estado actual de cada cita
            estado = (
                supabase_client
                .table("estado")
                .select("estado")
                .eq("cita_medica_id", cita["id"])
                .order("id", desc=True)
                .limit(1)
                .execute()
            )

            if estado.data:
                estado_texto = estado.data[0]["estado"].lower()
                if estado_texto == "confirmada":
                    estadisticas["confirmadas"] += 1
                elif estado_texto == "pendiente":
                    estadisticas["pendientes"] += 1
                elif estado_texto == "en consulta":
                    estadisticas["en_consulta"] += 1
                elif estado_texto == "completada":
                    estadisticas["completadas"] += 1
                elif estado_texto == "cancelada":
                    estadisticas["canceladas"] += 1

        return estadisticas

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
