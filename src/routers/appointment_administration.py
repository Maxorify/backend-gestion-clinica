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
                "doctor_id": cita_completa.cita.doctor_id
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
    """
    try:
        from datetime import date as date_module
        import calendar
        
        # Usar fecha actual si no se proporciona
        fecha_actual = fecha or date_module.today().isoformat()
        print(f"🔍 DEBUG Stats - Doctor ID: {doctor_id}, Fecha: {fecha_actual}")
        
        # Obtener todas las citas del día
        citas_hoy = (
            supabase_client
            .table("cita_medica")
            .select("id")
            .eq("doctor_id", doctor_id)
            .gte("fecha_atencion", f"{fecha_actual}T00:00:00")
            .lte("fecha_atencion", f"{fecha_actual}T23:59:59")
            .execute()
        )

        print(f"🔍 DEBUG Stats - Citas hoy: {len(citas_hoy.data) if citas_hoy.data else 0}")

        # Contar por estados
        total_hoy = 0
        atendidos_hoy = 0
        pendientes_hoy = 0
        cancelados_hoy = 0

        if citas_hoy.data:
            for cita in citas_hoy.data:
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
                    estado_actual = estado.data[0]["estado"]
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
            .gte("fecha_atencion", f"{año_mes}-01T00:00:00")
            .lte("fecha_atencion", f"{año_mes}-{ultimo_dia}T23:59:59")
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
