"""
Router para la administración profesional de asistencia de doctores.
REESCRITURA COMPLETA - Basado en horarios_personal
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import List, Optional
from datetime import datetime, date, time, timedelta
from src.utils.supabase import supabase_client
from src.models.asistencia import (
    MarcaAsistenciaCreate, MarcaAsistenciaResponse,
    JustificacionCreate, EstadoAsistenciaResponse,
    TurnoAsistenciaDetalle, ResumenDiarioAsistencia,
    EstadisticasAsistenciaDoctor, DoctorBasicInfo,
    ParametroAsistencia, ParametroAsistenciaUpdate,
    TipoMarca, FuenteMarca, EstadoAsistencia
)

attendance_router = APIRouter(tags=["Asistencia Profesional"], prefix="/asistencia")


@attendance_router.get("/turnos-dia", response_model=ResumenDiarioAsistencia)
async def obtener_turnos_dia(
    fecha: Optional[date] = Query(None, description="Fecha a consultar (default: hoy)"),
):
    """
    📊 Obtiene el resumen de asistencia del día basado en horarios_personal.
    OPTIMIZADO: Usa queries masivas con JOINs en vez de N+1 queries.
    """
    fecha_consulta = fecha or date.today()
    
    try:
        # OPTIMIZACIÓN 1: Query única con JOIN para horarios + doctores
        horarios_response = supabase_client.from_("horarios_personal") \
            .select("*, usuario:usuario_sistema_id(id, nombre, apellido_paterno, apellido_materno, rut, email, celular)") \
            .gte("inicio_bloque", f"{fecha_consulta}T00:00:00") \
            .lte("inicio_bloque", f"{fecha_consulta}T23:59:59") \
            .order("inicio_bloque", desc=False) \
            .execute()
        
        if not horarios_response.data:
            return ResumenDiarioAsistencia(
                fecha=fecha_consulta,
                total_turnos=0,
                en_turno=0,
                asistieron=0,
                con_atraso=0,
                ausentes=0,
                justificados=0,
                turnos=[]
            )
        
        # Extraer IDs únicos de doctores para bulk queries
        doctor_ids = list(set(h['usuario']['id'] for h in horarios_response.data if h.get('usuario')))
        
        if not doctor_ids:
            return ResumenDiarioAsistencia(
                fecha=fecha_consulta,
                total_turnos=0,
                en_turno=0,
                asistieron=0,
                con_atraso=0,
                ausentes=0,
                justificados=0,
                turnos=[]
            )
        
        # OPTIMIZACIÓN 2: Bulk query de asistencias de TODOS los doctores
        inicio_dia = f"{fecha_consulta}T00:00:00"
        fin_dia = f"{fecha_consulta}T23:59:59"
        
        asistencias_response = supabase_client.from_("asistencia") \
            .select("*") \
            .in_("usuario_sistema_id", doctor_ids) \
            .gte("inicio_turno", inicio_dia) \
            .lte("inicio_turno", fin_dia) \
            .execute()
        
        # Crear diccionario de asistencias por doctor_id para lookup rápido
        asistencias_dict = {}
        if asistencias_response.data:
            for asist in asistencias_response.data:
                asistencias_dict[asist['usuario_sistema_id']] = asist
        
        # OPTIMIZACIÓN 3: Bulk query de especialidades de TODOS los doctores
        especialidades_response = supabase_client.from_("especialidades_doctor") \
            .select("usuario_sistema_id, especialidad:especialidad_id(nombre)") \
            .in_("usuario_sistema_id", doctor_ids) \
            .execute()
        
        # Agrupar especialidades por doctor_id
        especialidades_dict = {}
        if especialidades_response.data:
            for esp in especialidades_response.data:
                doctor_id = esp['usuario_sistema_id']
                if doctor_id not in especialidades_dict:
                    especialidades_dict[doctor_id] = []
                if esp.get('especialidad'):
                    especialidades_dict[doctor_id].append(esp['especialidad']['nombre'])
        
        # OPTIMIZACIÓN 4: Bulk query de pacientes de TODOS los doctores
        pacientes_response = supabase_client.from_("cita_medica") \
            .select("doctor_id") \
            .in_("doctor_id", doctor_ids) \
            .gte("fecha_atencion", inicio_dia) \
            .lte("fecha_atencion", fin_dia) \
            .execute()
        
        # Contar pacientes por doctor_id
        pacientes_dict = {}
        if pacientes_response.data:
            for cita in pacientes_response.data:
                doctor_id = cita['doctor_id']
                pacientes_dict[doctor_id] = pacientes_dict.get(doctor_id, 0) + 1
        
        # Agrupar horarios por doctor
        doctores_dict = {}
        for horario in horarios_response.data:
            if not horario.get('usuario'):
                continue
                
            doctor_id = horario['usuario']['id']
            
            if doctor_id not in doctores_dict:
                doctores_dict[doctor_id] = {
                    'doctor': horario['usuario'],
                    'bloques': [],
                    'primer_bloque': horario,
                    'inicio_turno': horario['inicio_bloque'],
                    'finalizacion_turno': horario['finalizacion_bloque']
                }
            else:
                doctores_dict[doctor_id]['finalizacion_turno'] = horario['finalizacion_bloque']
            
            doctores_dict[doctor_id]['bloques'].append(horario)
        
        # Procesar cada doctor usando datos pre-cargados
        turnos_procesados = []
        stats = {"en_turno": 0, "asistieron": 0, "con_atraso": 0, "ausentes": 0, "justificados": 0}
        
        for doctor_id, info in doctores_dict.items():
            doctor_data = info['doctor']
            
            # Obtener asistencia del diccionario (O(1) lookup)
            asistencia = asistencias_dict.get(doctor_id)
            
            # Obtener especialidades del diccionario (O(1) lookup)
            especialidades = especialidades_dict.get(doctor_id, [])
            
            # Construir objeto doctor
            doctor = DoctorBasicInfo(
                id=doctor_id,
                nombre=doctor_data.get("nombre", ""),
                apellido_paterno=doctor_data.get("apellido_paterno", ""),
                apellido_materno=doctor_data.get("apellido_materno", ""),
                nombre_completo=f"{doctor_data.get('nombre', '')} {doctor_data.get('apellido_paterno', '')} {doctor_data.get('apellido_materno', '')}".strip(),
                rut=doctor_data.get("rut"),
                especialidades=especialidades,
                email=doctor_data.get("email"),
                celular=doctor_data.get("celular")
            )
            
            # Obtener pacientes del diccionario (O(1) lookup)
            pacientes_agendados = pacientes_dict.get(doctor_id, 0)
            
            # Calcular estado y tiempos
            if asistencia:
                # Tiene asistencia registrada
                inicio_real = datetime.fromisoformat(asistencia['inicio_turno'].replace("Z", "+00:00"))
                fin_real = datetime.fromisoformat(asistencia['finalizacion_turno'].replace("Z", "+00:00")) if asistencia.get('finalizacion_turno') else None
                
                inicio_programado = datetime.fromisoformat(info['inicio_turno'].replace("Z", "+00:00"))
                
                # Calcular atraso
                minutos_atraso = max(0, int((inicio_real - inicio_programado).total_seconds() / 60))
                
                # Calcular minutos trabajados
                if fin_real:
                    minutos_trabajados = int((fin_real - inicio_real).total_seconds() / 60)
                    # Si llegó con atraso, aunque haya completado el turno
                    if minutos_atraso > 0:
                        estado = "ATRASO"
                        stats["con_atraso"] += 1
                    else:
                        estado = "ASISTIO"
                        stats["asistieron"] += 1
                else:
                    # Aún en turno
                    ahora = datetime.now(inicio_real.tzinfo)
                    minutos_trabajados = int((ahora - inicio_real).total_seconds() / 60)
                    # Si llegó con atraso, aunque esté en turno
                    if minutos_atraso > 0:
                        estado = "ATRASO"
                        stats["con_atraso"] += 1
                    else:
                        estado = "EN_TURNO"
                        stats["en_turno"] += 1
                
                marca_entrada = inicio_real
                marca_salida = fin_real
            else:
                # No tiene asistencia - verificar si debería estar
                inicio_programado = datetime.fromisoformat(info['inicio_turno'].replace("Z", "+00:00"))
                fin_programado = datetime.fromisoformat(info['finalizacion_turno'].replace("Z", "+00:00"))
                ahora = datetime.now(inicio_programado.tzinfo)
                
                if ahora >= fin_programado:
                    # Ya terminó el turno y nunca marcó
                    estado = "AUSENTE"
                    stats["ausentes"] += 1
                elif ahora >= inicio_programado:
                    # Ya debería haber iniciado pero no marcó entrada - está ATRASADO sin marcar
                    estado = "ATRASADO"
                    stats["con_atraso"] += 1
                else:
                    # Aún no llega la hora - turno programado para después
                    estado = "PROGRAMADO"
                    stats["en_turno"] += 1  # Lo contamos como "en turno" para estadísticas
                
                minutos_atraso = 0
                minutos_trabajados = None
                marca_entrada = None
                marca_salida = None
            
            # Construir turno
            turno_detalle = TurnoAsistenciaDetalle(
                id=asistencia['id'] if asistencia else info['primer_bloque']['id'],
                horario_id=info['primer_bloque']['id'],
                inicio_turno=datetime.fromisoformat(info['inicio_turno'].replace("Z", "+00:00")),
                finalizacion_turno=datetime.fromisoformat(info['finalizacion_turno'].replace("Z", "+00:00")),
                doctor=doctor,
                estado_asistencia=estado,
                minutos_atraso=minutos_atraso,
                minutos_trabajados=minutos_trabajados,
                porcentaje_asistencia=None,
                marca_entrada=marca_entrada,
                marca_salida=marca_salida,
                fuente_entrada=None,
                fuente_salida=None,
                justificacion=None,
                tipo_justificacion=None,
                pacientes_agendados=pacientes_agendados,
                pacientes_atendidos=0,
                created_at=datetime.now()
            )
            
            turnos_procesados.append(turno_detalle)
        
        return ResumenDiarioAsistencia(
            fecha=fecha_consulta,
            total_turnos=len(turnos_procesados),
            en_turno=stats["en_turno"],
            asistieron=stats["asistieron"],
            con_atraso=stats["con_atraso"],
            ausentes=stats["ausentes"],
            justificados=stats["justificados"],
            turnos=turnos_procesados
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener turnos del día: {str(e)}")


# Endpoints adicionales para registrar entrada/salida
@attendance_router.post("/registrar-entrada")
async def registrar_entrada(usuario_sistema_id: int):
    """Registra la entrada (inicio de turno) de un doctor."""
    try:
        # Verificar turno activo
        turno_activo = supabase_client.from_("asistencia").select("id").eq("usuario_sistema_id", usuario_sistema_id).is_("finalizacion_turno", "null").execute()
        
        if turno_activo.data:
            raise HTTPException(status_code=409, detail="Ya tiene un turno activo")
        
        # Registrar inicio
        nuevo_registro = {
            "usuario_sistema_id": usuario_sistema_id,
            "inicio_turno": datetime.now().isoformat()
        }
        
        resultado = supabase_client.from_("asistencia").insert(nuevo_registro).execute()
        
        return {"mensaje": "Entrada registrada", "asistencia": resultado.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@attendance_router.post("/registrar-salida/{asistencia_id}")
async def registrar_salida(asistencia_id: int):
    """Registra la salida (finalización de turno) de un doctor."""
    try:
        # Verificar registro
        registro = supabase_client.from_("asistencia").select("*").eq("id", asistencia_id).execute()
        
        if not registro.data:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        if registro.data[0]["finalizacion_turno"]:
            raise HTTPException(status_code=409, detail="Turno ya finalizado")
        
        # Registrar finalización
        resultado = supabase_client.from_("asistencia").update({"finalizacion_turno": datetime.now().isoformat()}).eq("id", asistencia_id).execute()
        
        return {"mensaje": "Salida registrada", "asistencia": resultado.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT: DETALLE COMPLETO DEL DOCTOR (Panel derecho)
# ============================================================================

@attendance_router.get("/doctor/{doctor_id}/detalle-completo")
async def obtener_detalle_completo_doctor(
    doctor_id: int,
    fecha: Optional[date] = Query(None, description="Fecha a consultar (default: hoy)")
):
    """
    📋 Obtiene el detalle completo del doctor para el panel lateral.
    Incluye: info básica, estado actual, turno del día, pacientes, estadísticas.
    """
    fecha_consulta = fecha or date.today()
    
    try:
        # 1. Datos básicos del doctor
        doctor_response = supabase_client.from_("usuario_sistema") \
            .select("id, nombre, apellido_paterno, apellido_materno, rut, email") \
            .eq("id", doctor_id) \
            .single() \
            .execute()
        
        if not doctor_response.data:
            raise HTTPException(status_code=404, detail="Doctor no encontrado")
        
        doctor_data = doctor_response.data
        
        # 2. Especialidades
        esp_response = supabase_client.from_("especialidades_doctor") \
            .select("especialidad:especialidad_id(nombre)") \
            .eq("usuario_sistema_id", doctor_id) \
            .execute()
        
        especialidades = []
        if esp_response.data:
            especialidades = [e["especialidad"]["nombre"] for e in esp_response.data if e.get("especialidad")]
        
        # 3. Horario programado del día
        horarios_response = supabase_client.from_("horarios_personal") \
            .select("*") \
            .eq("usuario_sistema_id", doctor_id) \
            .gte("inicio_bloque", f"{fecha_consulta}T00:00:00") \
            .lte("inicio_bloque", f"{fecha_consulta}T23:59:59") \
            .order("inicio_bloque", desc=False) \
            .execute()
        
        turno_programado = None
        if horarios_response.data:
            primer_bloque = horarios_response.data[0]
            ultimo_bloque = horarios_response.data[-1]
            turno_programado = {
                "inicio": primer_bloque["inicio_bloque"],
                "fin": ultimo_bloque["finalizacion_bloque"],
                "total_bloques": len(horarios_response.data)
            }
        
        # 4. Asistencia del día (entrada/salida real)
        asist_response = supabase_client.from_("asistencia") \
            .select("*") \
            .eq("usuario_sistema_id", doctor_id) \
            .gte("inicio_turno", f"{fecha_consulta}T00:00:00") \
            .lte("inicio_turno", f"{fecha_consulta}T23:59:59") \
            .execute()
        
        asistencia_hoy = None
        estado_actual = "FUERA_DE_TURNO"
        minutos_atraso = 0
        minutos_trabajados = None
        
        if asist_response.data:
            asistencia_hoy = asist_response.data[0]
            inicio_real = datetime.fromisoformat(asistencia_hoy['inicio_turno'].replace("Z", "+00:00"))
            fin_real = datetime.fromisoformat(asistencia_hoy['finalizacion_turno'].replace("Z", "+00:00")) if asistencia_hoy.get('finalizacion_turno') else None
            
            if turno_programado:
                inicio_prog = datetime.fromisoformat(turno_programado['inicio'].replace("Z", "+00:00"))
                minutos_atraso = max(0, int((inicio_real - inicio_prog).total_seconds() / 60))
            
            if fin_real:
                estado_actual = "FUERA_DE_TURNO"
                minutos_trabajados = int((fin_real - inicio_real).total_seconds() / 60)
            else:
                estado_actual = "EN_TURNO"
                ahora = datetime.now(inicio_real.tzinfo)
                minutos_trabajados = int((ahora - inicio_real).total_seconds() / 60)
        
        # 5. Pacientes del día
        pacientes_response = supabase_client.from_("cita_medica") \
            .select("id, fecha_atencion, paciente:paciente_id(nombre, apellido_paterno)") \
            .eq("doctor_id", doctor_id) \
            .gte("fecha_atencion", f"{fecha_consulta}T00:00:00") \
            .lte("fecha_atencion", f"{fecha_consulta}T23:59:59") \
            .execute()
        
        pacientes_agendados = len(pacientes_response.data) if pacientes_response.data else 0
        
        # Contar atendidos (estados COMPLETADA)
        pacientes_atendidos = 0
        if pacientes_response.data:
            citas_ids = [c['id'] for c in pacientes_response.data]
            estados_response = supabase_client.from_("estado") \
                .select("cita_medica_id, estado") \
                .in_("cita_medica_id", citas_ids) \
                .eq("estado", "COMPLETADA") \
                .execute()
            pacientes_atendidos = len(estados_response.data) if estados_response.data else 0
        
        pacientes_pendientes = pacientes_agendados - pacientes_atendidos
        
        # 6. Timeline del día (eventos)
        timeline = []
        if asistencia_hoy:
            # Evento: Entrada
            timeline.append({
                "hora": asistencia_hoy['inicio_turno'],
                "tipo": "ENTRADA",
                "descripcion": f"Entrada a turno{f' ({minutos_atraso} min atraso)' if minutos_atraso > 0 else ''}",
                "icono": "🟢"
            })
            
            # Evento: Salida (si existe)
            if asistencia_hoy.get('finalizacion_turno'):
                timeline.append({
                    "hora": asistencia_hoy['finalizacion_turno'],
                    "tipo": "SALIDA",
                    "descripcion": "Salida de turno",
                    "icono": "🔴"
                })
        
        # Construir respuesta
        return {
            "doctor": {
                "id": doctor_data["id"],
                "nombre_completo": f"{doctor_data['nombre']} {doctor_data.get('apellido_paterno', '')} {doctor_data.get('apellido_materno', '')}".strip(),
                "nombre": doctor_data["nombre"],
                "apellido_paterno": doctor_data.get("apellido_paterno"),
                "apellido_materno": doctor_data.get("apellido_materno"),
                "rut": doctor_data.get("rut"),
                "email": doctor_data.get("email"),
                "especialidades": especialidades
            },
            "turno_hoy": {
                "programado": turno_programado,
                "asistencia": asistencia_hoy,
                "estado_actual": estado_actual,
                "minutos_atraso": minutos_atraso,
                "minutos_trabajados": minutos_trabajados
            },
            "pacientes_hoy": {
                "agendados": pacientes_agendados,
                "atendidos": pacientes_atendidos,
                "pendientes": pacientes_pendientes
            },
            "timeline": timeline
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener detalle del doctor: {str(e)}")


# ============================================================================
# ENDPOINT: ESTADÍSTICAS DEL DOCTOR (Período: Hoy/Semana/Mes)
# ============================================================================

@attendance_router.get("/doctor/{doctor_id}/estadisticas-periodo")
async def obtener_estadisticas_periodo(
    doctor_id: int,
    periodo: str = Query("hoy", description="hoy | semana | mes"),
    fecha_referencia: Optional[date] = Query(None)
):
    """
    📊 Estadísticas del doctor por período.
    KPIs: Asistencia, Puntualidad, Horas, Pacientes.
    """
    fecha_ref = fecha_referencia or date.today()
    
    # Calcular rango de fechas según período
    if periodo == "hoy":
        fecha_inicio = fecha_ref
        fecha_fin = fecha_ref
    elif periodo == "semana":
        # Lunes de esta semana
        fecha_inicio = fecha_ref - timedelta(days=fecha_ref.weekday())
        fecha_fin = fecha_inicio + timedelta(days=6)
    elif periodo == "mes":
        # Primer día del mes
        fecha_inicio = date(fecha_ref.year, fecha_ref.month, 1)
        # Último día del mes
        if fecha_ref.month == 12:
            fecha_fin = date(fecha_ref.year, 12, 31)
        else:
            fecha_fin = date(fecha_ref.year, fecha_ref.month + 1, 1) - timedelta(days=1)
    else:
        raise HTTPException(status_code=400, detail="Período inválido. Use: hoy, semana o mes")
    
    try:
        # 1. ASISTENCIA: Obtener todos los horarios programados en el período
        horarios_response = supabase_client.from_("horarios_personal") \
            .select("inicio_bloque, finalizacion_bloque") \
            .eq("usuario_sistema_id", doctor_id) \
            .gte("inicio_bloque", f"{fecha_inicio}T00:00:00") \
            .lte("inicio_bloque", f"{fecha_fin}T23:59:59") \
            .execute()
        
        # Agrupar por día
        dias_con_turno = set()
        if horarios_response.data:
            for h in horarios_response.data:
                fecha_turno = h['inicio_bloque'][:10]
                dias_con_turno.add(fecha_turno)
        
        total_dias_turno = len(dias_con_turno)
        
        # 2. Obtener asistencias en el período
        asistencias_response = supabase_client.from_("asistencia") \
            .select("*") \
            .eq("usuario_sistema_id", doctor_id) \
            .gte("inicio_turno", f"{fecha_inicio}T00:00:00") \
            .lte("inicio_turno", f"{fecha_fin}T23:59:59") \
            .execute()
        
        asistencias_data = asistencias_response.data if asistencias_response.data else []
        
        # Días que asistió
        dias_asistio = len(asistencias_data)
        
        # 3. Obtener justificaciones
        estados_response = supabase_client.from_("asistencia_estados") \
            .select("*, asistencia:asistencia_id(inicio_turno)") \
            .in_("asistencia_id", [a['id'] for a in asistencias_data]) \
            .execute()
        
        ausencias_justificadas = 0
        if estados_response.data:
            ausencias_justificadas = len([e for e in estados_response.data if e.get('estado') == 'JUSTIFICADO'])
        
        ausencias_injustificadas = total_dias_turno - dias_asistio - ausencias_justificadas
        
        # 4. PUNTUALIDAD: Calcular atrasos
        atrasos = []
        horas_programadas_total = 0
        horas_efectivas_total = 0
        
        for asistencia in asistencias_data:
            fecha_asist = asistencia['inicio_turno'][:10]
            
            # Buscar horario programado ese día
            horario_dia = supabase_client.from_("horarios_personal") \
                .select("*") \
                .eq("usuario_sistema_id", doctor_id) \
                .gte("inicio_bloque", f"{fecha_asist}T00:00:00") \
                .lte("inicio_bloque", f"{fecha_asist}T23:59:59") \
                .order("inicio_bloque", desc=False) \
                .execute()
            
            if horario_dia.data:
                inicio_prog = datetime.fromisoformat(horario_dia.data[0]['inicio_bloque'].replace("Z", "+00:00"))
                fin_prog = datetime.fromisoformat(horario_dia.data[-1]['finalizacion_bloque'].replace("Z", "+00:00"))
                
                inicio_real = datetime.fromisoformat(asistencia['inicio_turno'].replace("Z", "+00:00"))
                fin_real = datetime.fromisoformat(asistencia['finalizacion_turno'].replace("Z", "+00:00")) if asistencia.get('finalizacion_turno') else datetime.now(inicio_real.tzinfo)
                
                # Calcular atraso
                minutos_atraso = max(0, int((inicio_real - inicio_prog).total_seconds() / 60))
                if minutos_atraso > 0:
                    atrasos.append(minutos_atraso)
                
                # Calcular horas
                horas_programadas = (fin_prog - inicio_prog).total_seconds() / 3600
                horas_efectivas = (fin_real - inicio_real).total_seconds() / 3600
                
                horas_programadas_total += horas_programadas
                horas_efectivas_total += horas_efectivas
        
        total_atrasos = len(atrasos)
        atraso_promedio = int(sum(atrasos) / len(atrasos)) if atrasos else 0
        peor_atraso = max(atrasos) if atrasos else 0
        
        # 5. PACIENTES
        pacientes_response = supabase_client.from_("cita_medica") \
            .select("id, fecha_atencion") \
            .eq("doctor_id", doctor_id) \
            .gte("fecha_atencion", f"{fecha_inicio}T00:00:00") \
            .lte("fecha_atencion", f"{fecha_fin}T23:59:59") \
            .execute()
        
        total_pacientes_agendados = len(pacientes_response.data) if pacientes_response.data else 0
        
        # Contar atendidos
        pacientes_atendidos = 0
        if pacientes_response.data:
            citas_ids = [c['id'] for c in pacientes_response.data]
            estados_pac = supabase_client.from_("estado") \
                .select("*") \
                .in_("cita_medica_id", citas_ids) \
                .eq("estado", "COMPLETADA") \
                .execute()
            pacientes_atendidos = len(estados_pac.data) if estados_pac.data else 0
        
        return {
            "periodo": periodo,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "asistencia": {
                "dias_con_turno": total_dias_turno,
                "asistencias": dias_asistio,
                "ausencias_injustificadas": max(0, ausencias_injustificadas),
                "ausencias_justificadas": ausencias_justificadas
            },
            "puntualidad": {
                "total_atrasos": total_atrasos,
                "atraso_promedio_min": atraso_promedio,
                "peor_atraso_min": peor_atraso
            },
            "horas": {
                "programadas": round(horas_programadas_total, 2),
                "efectivas": round(horas_efectivas_total, 2),
                "diferencia": round(horas_efectivas_total - horas_programadas_total, 2)
            },
            "pacientes": {
                "agendados": total_pacientes_agendados,
                "atendidos": pacientes_atendidos,
                "pendientes": total_pacientes_agendados - pacientes_atendidos
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular estadísticas: {str(e)}")


# ============================================================================
# ENDPOINT: HISTORIAL DIARIO DEL DOCTOR (Tabla)
# ============================================================================

@attendance_router.get("/doctor/{doctor_id}/historial-diario")
async def obtener_historial_diario(
    doctor_id: int,
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    limit: int = Query(30, le=100)
):
    """
    📅 Historial diario del doctor.
    Retorna tabla con: fecha, turno programado, entrada/salida real, atrasos, estado, pacientes.
    """
    # Defaults: últimos 30 días
    if not fecha_desde:
        fecha_desde = date.today() - timedelta(days=30)
    if not fecha_hasta:
        fecha_hasta = date.today()
    
    try:
        # 1. Obtener todas las asistencias en el rango
        asistencias_response = supabase_client.from_("asistencia") \
            .select("*") \
            .eq("usuario_sistema_id", doctor_id) \
            .gte("inicio_turno", f"{fecha_desde}T00:00:00") \
            .lte("inicio_turno", f"{fecha_hasta}T23:59:59") \
            .order("inicio_turno", desc=True) \
            .limit(limit) \
            .execute()
        
        historial = []
        
        for asist in (asistencias_response.data or []):
            fecha_dia = asist['inicio_turno'][:10]
            
            # Horario programado ese día
            horarios = supabase_client.from_("horarios_personal") \
                .select("*") \
                .eq("usuario_sistema_id", doctor_id) \
                .gte("inicio_bloque", f"{fecha_dia}T00:00:00") \
                .lte("inicio_bloque", f"{fecha_dia}T23:59:59") \
                .order("inicio_bloque", desc=False) \
                .execute()
            
            turno_prog_inicio = None
            turno_prog_fin = None
            if horarios.data:
                turno_prog_inicio = horarios.data[0]['inicio_bloque']
                turno_prog_fin = horarios.data[-1]['finalizacion_bloque']
            
            # Calcular atraso
            minutos_atraso = 0
            if turno_prog_inicio:
                inicio_prog = datetime.fromisoformat(turno_prog_inicio.replace("Z", "+00:00"))
                inicio_real = datetime.fromisoformat(asist['inicio_turno'].replace("Z", "+00:00"))
                minutos_atraso = max(0, int((inicio_real - inicio_prog).total_seconds() / 60))
            
            # Estado del día
            estado_dia = "ASISTIO" if asist.get('finalizacion_turno') else "EN_TURNO"
            
            # Justificación (si existe)
            justificacion = None
            estado_response = supabase_client.from_("asistencia_estados") \
                .select("*") \
                .eq("asistencia_id", asist['id']) \
                .execute()
            if estado_response.data:
                if estado_response.data[0].get('estado') == 'JUSTIFICADO':
                    estado_dia = "JUSTIFICADO"
                    justificacion = estado_response.data[0].get('justificacion')
            
            # Pacientes ese día
            pacientes = supabase_client.from_("cita_medica") \
                .select("id", count="exact") \
                .eq("doctor_id", doctor_id) \
                .gte("fecha_atencion", f"{fecha_dia}T00:00:00") \
                .lte("fecha_atencion", f"{fecha_dia}T23:59:59") \
                .execute()
            
            pacientes_agendados = pacientes.count or 0
            
            # Pacientes atendidos
            pacientes_atendidos = 0
            if pacientes.data:
                citas_ids = [p['id'] for p in pacientes.data]
                estados_pac = supabase_client.from_("estado") \
                    .select("*", count="exact") \
                    .in_("cita_medica_id", citas_ids) \
                    .eq("estado", "COMPLETADA") \
                    .execute()
                pacientes_atendidos = estados_pac.count or 0
            
            historial.append({
                "fecha": fecha_dia,
                "turno_programado": {
                    "inicio": turno_prog_inicio,
                    "fin": turno_prog_fin
                },
                "entrada_real": asist['inicio_turno'],
                "salida_real": asist.get('finalizacion_turno'),
                "minutos_atraso": minutos_atraso,
                "estado_dia": estado_dia,
                "justificacion": justificacion,
                "pacientes": {
                    "agendados": pacientes_agendados,
                    "atendidos": pacientes_atendidos
                },
                "asistencia_id": asist['id']
            })
        
        return {
            "doctor_id": doctor_id,
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "total_registros": len(historial),
            "historial": historial
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener historial: {str(e)}")


# ============================================================================
# ENDPOINT: JUSTIFICACIONES DEL DOCTOR
# ============================================================================

@attendance_router.get("/doctor/{doctor_id}/justificaciones")
async def obtener_justificaciones_doctor(doctor_id: int):
    """
    📝 Lista todas las justificaciones del doctor.
    """
    try:
        # Obtener todas las asistencias del doctor
        asistencias = supabase_client.from_("asistencia") \
            .select("id, inicio_turno") \
            .eq("usuario_sistema_id", doctor_id) \
            .execute()
        
        if not asistencias.data:
            return {"justificaciones": []}
        
        asist_ids = [a['id'] for a in asistencias.data]
        
        # Obtener estados justificados
        estados = supabase_client.from_("asistencia_estados") \
            .select("*") \
            .in_("asistencia_id", asist_ids) \
            .eq("estado", "JUSTIFICADO") \
            .order("fecha_justificacion", desc=True) \
            .execute()
        
        justificaciones = []
        for estado in (estados.data or []):
            # Buscar fecha de la asistencia
            asist_info = next((a for a in asistencias.data if a['id'] == estado['asistencia_id']), None)
            
            justificaciones.append({
                "id": estado['id'],
                "fecha": asist_info['inicio_turno'][:10] if asist_info else None,
                "tipo": estado.get('tipo_justificacion'),
                "descripcion": estado.get('justificacion'),
                "justificado_por": estado.get('justificado_por'),
                "fecha_justificacion": estado.get('fecha_justificacion'),
                "asistencia_id": estado['asistencia_id']
            })
        
        return {"justificaciones": justificaciones}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener justificaciones: {str(e)}")


# ============================================================================
# ENDPOINT: AGREGAR JUSTIFICACIÓN
# ============================================================================

@attendance_router.post("/doctor/{doctor_id}/agregar-justificacion")
async def agregar_justificacion_doctor(
    doctor_id: int,
    asistencia_id: int,
    tipo_justificacion: str,
    descripcion: str,
    justificado_por: int
):
    """
    ✍️ Agrega una justificación a una ausencia/atraso del doctor.
    """
    try:
        # Verificar que la asistencia existe y pertenece al doctor
        asist = supabase_client.from_("asistencia") \
            .select("*") \
            .eq("id", asistencia_id) \
            .eq("usuario_sistema_id", doctor_id) \
            .single() \
            .execute()
        
        if not asist.data:
            raise HTTPException(status_code=404, detail="Asistencia no encontrada")
        
        # Crear o actualizar estado
        estado_data = {
            "asistencia_id": asistencia_id,
            "estado": "JUSTIFICADO",
            "tipo_justificacion": tipo_justificacion,
            "justificacion": descripcion,
            "justificado_por": justificado_por,
            "fecha_justificacion": datetime.now().isoformat()
        }
        
        # Verificar si ya existe
        existing = supabase_client.from_("asistencia_estados") \
            .select("id") \
            .eq("asistencia_id", asistencia_id) \
            .execute()
        
        if existing.data:
            # Actualizar
            result = supabase_client.from_("asistencia_estados") \
                .update(estado_data) \
                .eq("asistencia_id", asistencia_id) \
                .execute()
        else:
            # Insertar
            result = supabase_client.from_("asistencia_estados") \
                .insert(estado_data) \
                .execute()
        
        return {"mensaje": "Justificación agregada", "data": result.data[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al agregar justificación: {str(e)}")

# ============================================================================
# ENDPOINTS PARA DOCTORES - MARCAR ASISTENCIA
# ============================================================================

@attendance_router.get("/doctor/mi-turno-hoy")
async def obtener_mi_turno_hoy(
    usuario_id: int = Query(..., description="ID del doctor"),
    fecha: Optional[date] = Query(None, description="Fecha (default: hoy)")
):
    """
    📋 Obtiene el turno del día y estado de asistencia del doctor.
    """
    fecha_consulta = fecha or date.today()
    
    try:
        # Buscar horarios del doctor para hoy
        horarios_response = supabase_client.from_("horarios_personal") \
            .select("*") \
            .eq("usuario_sistema_id", usuario_id) \
            .gte("inicio_bloque", f"{fecha_consulta}T00:00:00") \
            .lte("inicio_bloque", f"{fecha_consulta}T23:59:59") \
            .order("inicio_bloque", desc=False) \
            .execute()
        
        if not horarios_response.data:
            return {
                "tiene_turno": False,
                "mensaje": "No tienes turno programado para hoy"
            }
        
        # Calcular rango del turno
        primer_bloque = horarios_response.data[0]
        ultimo_bloque = horarios_response.data[-1]
        
        inicio_turno = primer_bloque['inicio_bloque']
        fin_turno = ultimo_bloque['finalizacion_bloque']
        
        # Buscar asistencia registrada
        asistencia_response = supabase_client.from_("asistencia") \
            .select("*") \
            .eq("usuario_sistema_id", usuario_id) \
            .gte("inicio_turno", f"{fecha_consulta}T00:00:00") \
            .lte("inicio_turno", f"{fecha_consulta}T23:59:59") \
            .execute()
        
        asistencia = asistencia_response.data[0] if asistencia_response.data else None
        
        # Calcular estado
        ahora = datetime.now()
        inicio_prog = datetime.fromisoformat(inicio_turno.replace("Z", "+00:00"))
        
        if asistencia:
            tiene_entrada = True
            tiene_salida = bool(asistencia.get('finalizacion_turno'))
            hora_entrada = asistencia['inicio_turno']
            hora_salida = asistencia.get('finalizacion_turno')
            
            # Calcular atraso
            entrada_dt = datetime.fromisoformat(hora_entrada.replace("Z", "+00:00"))
            minutos_atraso = max(0, int((entrada_dt - inicio_prog).total_seconds() / 60))
            
            # Calcular horas trabajadas
            if hora_salida:
                salida_dt = datetime.fromisoformat(hora_salida.replace("Z", "+00:00"))
                horas_trabajadas = (salida_dt - entrada_dt).total_seconds() / 3600
            else:
                horas_trabajadas = (ahora - entrada_dt.replace(tzinfo=None)).total_seconds() / 3600
        else:
            tiene_entrada = False
            tiene_salida = False
            hora_entrada = None
            hora_salida = None
            minutos_atraso = 0
            horas_trabajadas = 0
        
        return {
            "tiene_turno": True,
            "turno_programado": {
                "inicio": inicio_turno,
                "fin": fin_turno,
                "total_bloques": len(horarios_response.data)
            },
            "asistencia": {
                "id": asistencia['id'] if asistencia else None,
                "tiene_entrada": tiene_entrada,
                "tiene_salida": tiene_salida,
                "hora_entrada": hora_entrada,
                "hora_salida": hora_salida,
                "minutos_atraso": minutos_atraso,
                "horas_trabajadas": round(horas_trabajadas, 2)
            },
            "puede_marcar_entrada": not tiene_entrada,
            "puede_marcar_salida": tiene_entrada and not tiene_salida
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener turno: {str(e)}")


@attendance_router.post("/doctor/marcar-entrada")
async def marcar_entrada_doctor(
    usuario_id: int = Query(..., description="ID del doctor")
):
    """
    ✅ Marca la entrada del doctor a su turno.
    """
    try:
        fecha_hoy = date.today()
        ahora = datetime.now()
        
        # Verificar que tenga turno hoy
        horarios_response = supabase_client.from_("horarios_personal") \
            .select("*") \
            .eq("usuario_sistema_id", usuario_id) \
            .gte("inicio_bloque", f"{fecha_hoy}T00:00:00") \
            .lte("inicio_bloque", f"{fecha_hoy}T23:59:59") \
            .execute()
        
        if not horarios_response.data:
            raise HTTPException(status_code=400, detail="No tienes turno programado para hoy")
        
        # Verificar que no haya marcado ya
        asistencia_response = supabase_client.from_("asistencia") \
            .select("*") \
            .eq("usuario_sistema_id", usuario_id) \
            .gte("inicio_turno", f"{fecha_hoy}T00:00:00") \
            .lte("inicio_turno", f"{fecha_hoy}T23:59:59") \
            .execute()
        
        if asistencia_response.data:
            raise HTTPException(status_code=400, detail="Ya marcaste entrada hoy")
        
        # Registrar entrada
        asistencia_data = {
            "usuario_sistema_id": usuario_id,
            "inicio_turno": ahora.isoformat(),
            "finalizacion_turno": None
        }
        
        result = supabase_client.from_("asistencia") \
            .insert(asistencia_data) \
            .execute()
        
        return {
            "mensaje": "Entrada registrada exitosamente",
            "hora": ahora.isoformat(),
            "asistencia_id": result.data[0]['id']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al marcar entrada: {str(e)}")


@attendance_router.post("/doctor/marcar-salida")
async def marcar_salida_doctor(
    usuario_id: int = Query(..., description="ID del doctor")
):
    """
    🚪 Marca la salida del doctor de su turno.
    """
    try:
        fecha_hoy = date.today()
        ahora = datetime.now()
        
        # Buscar asistencia del día
        asistencia_response = supabase_client.from_("asistencia") \
            .select("*") \
            .eq("usuario_sistema_id", usuario_id) \
            .gte("inicio_turno", f"{fecha_hoy}T00:00:00") \
            .lte("inicio_turno", f"{fecha_hoy}T23:59:59") \
            .execute()
        
        if not asistencia_response.data:
            raise HTTPException(status_code=400, detail="No has marcado entrada hoy")
        
        asistencia = asistencia_response.data[0]
        
        if asistencia.get('finalizacion_turno'):
            raise HTTPException(status_code=400, detail="Ya marcaste salida hoy")
        
        # Registrar salida
        result = supabase_client.from_("asistencia") \
            .update({"finalizacion_turno": ahora.isoformat()}) \
            .eq("id", asistencia['id']) \
            .execute()
        
        # Calcular horas trabajadas
        entrada = datetime.fromisoformat(asistencia['inicio_turno'].replace("Z", "+00:00"))
        horas_trabajadas = (ahora - entrada.replace(tzinfo=None)).total_seconds() / 3600
        
        return {
            "mensaje": "Salida registrada exitosamente",
            "hora": ahora.isoformat(),
            "horas_trabajadas": round(horas_trabajadas, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al marcar salida: {str(e)}")
