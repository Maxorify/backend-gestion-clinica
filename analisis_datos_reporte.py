"""
ANÁLISIS PROFUNDO: Datos disponibles vs Propuestas para el reporte
Verificar qué métricas son realmente implementables con el schema actual
"""
from src.utils.supabase import supabase_client
from datetime import datetime, timedelta
import pytz

chile_tz = pytz.timezone('America/Santiago')

print("=" * 100)
print("ANÁLISIS COMPLETO DE DATOS DISPONIBLES PARA REPORTE DE ASISTENCIA")
print("=" * 100)

# ===== 1. DATOS DE ASISTENCIA (Ya tenemos) =====
print("\n📊 1. ASISTENCIA - DATOS DISPONIBLES")
print("-" * 100)

asistencia_sample = supabase_client.from_('asistencia') \
    .select('*') \
    .limit(1) \
    .execute()

print("✅ Tabla: asistencia")
print(f"   Campos: {list(asistencia_sample.data[0].keys()) if asistencia_sample.data else 'Sin datos'}")
print("   - inicio_turno (timestamp)")
print("   - finalizacion_turno (timestamp)")
print("   - usuario_sistema_id")
print("\n   MÉTRICAS CALCULABLES:")
print("   ✅ Horas trabajadas por turno")
print("   ✅ Días trabajados")
print("   ✅ Promedio de horas diarias")
print("   ✅ Turnos completos vs incompletos")

# ===== 2. ESTADOS DE ASISTENCIA (Tenemos pero no estamos usando) =====
print("\n\n📊 2. ASISTENCIA_ESTADOS - DATOS ENRIQUECIDOS")
print("-" * 100)

estados_sample = supabase_client.from_('asistencia_estados') \
    .select('*') \
    .limit(5) \
    .execute()

print(f"✅ Tabla: asistencia_estados")
print(f"   Registros encontrados: {len(estados_sample.data)}")
if estados_sample.data:
    print(f"   Campos: {list(estados_sample.data[0].keys())}")
    print("\n   Campos CRÍTICOS disponibles:")
    print("   - estado: ASISTIO, ATRASO, AUSENTE, JUSTIFICADO, PARCIAL, EN_TURNO")
    print("   - minutos_atraso: Cuantifica retrasos")
    print("   - minutos_trabajados: Ya calculado")
    print("   - porcentaje_asistencia: Métrica de cumplimiento")
    print("   - tipo_justificacion: PERMISO_MEDICO, LICENCIA_MEDICA, etc.")
    print("   - justificacion: Texto explicativo")
    
    print("\n   MÉTRICAS CALCULABLES:")
    print("   ✅ Tasa de puntualidad (% sin ATRASO)")
    print("   ✅ Promedio de minutos de atraso")
    print("   ✅ Ausencias justificadas vs no justificadas")
    print("   ✅ Tipos de justificaciones más frecuentes")
    print("   ✅ Porcentaje de asistencia promedio")
    
    # Mostrar muestra
    print("\n   MUESTRA DE DATOS:")
    for estado in estados_sample.data[:3]:
        print(f"   - Asistencia {estado['asistencia_id']}: {estado['estado']} | "
              f"Atraso: {estado.get('minutos_atraso', 0)} min | "
              f"Trabajados: {estado.get('minutos_trabajados', 0)} min")
else:
    print("   ⚠️ NO HAY DATOS - Tabla existe pero vacía")
    print("   Esto significa que NO ESTAMOS REGISTRANDO estados de asistencia")

# ===== 3. MARCAS DE ASISTENCIA (Sistema de registro detallado) =====
print("\n\n📊 3. MARCAS_ASISTENCIA - SISTEMA DE REGISTRO")
print("-" * 100)

marcas_sample = supabase_client.from_('marcas_asistencia') \
    .select('*') \
    .limit(5) \
    .execute()

print(f"✅ Tabla: marcas_asistencia")
print(f"   Registros encontrados: {len(marcas_sample.data)}")
if marcas_sample.data:
    print(f"   Campos: {list(marcas_sample.data[0].keys())}")
    print("\n   Información detallada:")
    print("   - tipo_marca: ENTRADA / SALIDA")
    print("   - fecha_hora_marca: Timestamp exacto")
    print("   - fuente: WEB, MANUAL, BIOMETRICO, APP")
    print("   - registrado_por: Quién hizo el registro")
    print("   - origen_ip: Trazabilidad")
    
    print("\n   MÉTRICAS CALCULABLES:")
    print("   ✅ Fuente de registro más usada (WEB vs MANUAL)")
    print("   ✅ Marcas irregulares (registradas manualmente)")
    print("   ✅ Historial de modificaciones")
    
    print("\n   MUESTRA DE DATOS:")
    for marca in marcas_sample.data[:3]:
        print(f"   - {marca['tipo_marca']} a las {marca['fecha_hora_marca']} "
              f"vía {marca['fuente']}")
else:
    print("   ⚠️ NO HAY DATOS - Sistema de marcas no está siendo usado")

# ===== 4. CITAS MÉDICAS - PRODUCTIVIDAD CLÍNICA =====
print("\n\n📊 4. CITA_MEDICA - PRODUCTIVIDAD REAL")
print("-" * 100)

# Buscar citas del último mes
hace_30_dias = datetime.now(chile_tz) - timedelta(days=30)
hace_30_dias_utc = hace_30_dias.astimezone(pytz.UTC)

citas_response = supabase_client.from_('cita_medica') \
    .select('id, fecha_atencion, doctor_id, paciente_id, especialidad_id') \
    .gte('fecha_atencion', hace_30_dias_utc.isoformat()) \
    .limit(100) \
    .execute()

print(f"✅ Tabla: cita_medica")
print(f"   Citas últimos 30 días: {len(citas_response.data)}")

if citas_response.data:
    # Agrupar por doctor
    citas_por_doctor = {}
    for cita in citas_response.data:
        doctor_id = cita['doctor_id']
        if doctor_id not in citas_por_doctor:
            citas_por_doctor[doctor_id] = []
        citas_por_doctor[doctor_id].append(cita)
    
    print(f"\n   Doctores con citas: {len(citas_por_doctor)}")
    print("\n   MÉTRICAS CALCULABLES:")
    print("   ✅ Pacientes atendidos por día")
    print("   ✅ Pacientes atendidos por hora trabajada")
    print("   ✅ Distribución por especialidad")
    print("   ✅ Citas totales en el período")
    
    # Mostrar top 3 doctores
    print("\n   TOP 3 DOCTORES POR CANTIDAD DE CITAS:")
    for doctor_id, citas in sorted(citas_por_doctor.items(), 
                                   key=lambda x: len(x[1]), 
                                   reverse=True)[:3]:
        # Obtener nombre del doctor
        doctor = supabase_client.from_('usuario_sistema') \
            .select('nombre, apellido_paterno') \
            .eq('id', doctor_id) \
            .single() \
            .execute()
        
        nombre = f"{doctor.data['nombre']} {doctor.data.get('apellido_paterno', '')}" if doctor.data else f"ID {doctor_id}"
        print(f"   - {nombre}: {len(citas)} citas")
else:
    print("   ⚠️ NO HAY CITAS en los últimos 30 días")

# ===== 5. ESTADOS DE CITAS - CUMPLIMIENTO =====
print("\n\n📊 5. ESTADO (de citas) - TASA DE ATENCIÓN")
print("-" * 100)

estados_citas = supabase_client.from_('estado') \
    .select('id, estado, cita_medica_id') \
    .limit(100) \
    .execute()

print(f"✅ Tabla: estado")
print(f"   Estados registrados: {len(estados_citas.data)}")

if estados_citas.data:
    # Contar por tipo de estado
    conteo_estados = {}
    for estado in estados_citas.data:
        estado_nombre = estado['estado']
        conteo_estados[estado_nombre] = conteo_estados.get(estado_nombre, 0) + 1
    
    print("\n   DISTRIBUCIÓN DE ESTADOS:")
    for estado_nombre, cantidad in sorted(conteo_estados.items(), 
                                          key=lambda x: x[1], 
                                          reverse=True):
        print(f"   - {estado_nombre}: {cantidad} citas")
    
    print("\n   MÉTRICAS CALCULABLES:")
    print("   ✅ Tasa de atención efectiva (Atendida / Total)")
    print("   ✅ Tasa de ausentismo (Ausente / Total)")
    print("   ✅ Tasa de cancelación")
    print("   ✅ Citas pendientes vs completadas")
else:
    print("   ⚠️ NO HAY DATOS de estados de citas")

# ===== 6. INFORMACIÓN DE CITAS - CALIDAD DE ATENCIÓN =====
print("\n\n📊 6. INFORMACION_CITA - CONSULTAS COMPLETADAS")
print("-" * 100)

info_citas = supabase_client.from_('informacion_cita') \
    .select('id, cita_medica_id, diagnostico_id') \
    .limit(100) \
    .execute()

print(f"✅ Tabla: informacion_cita")
print(f"   Consultas documentadas: {len(info_citas.data)}")

if info_citas.data:
    # Contar cuántas tienen diagnóstico
    con_diagnostico = sum(1 for info in info_citas.data if info.get('diagnostico_id'))
    print(f"\n   - Con diagnóstico registrado: {con_diagnostico} ({con_diagnostico*100//len(info_citas.data)}%)")
    print(f"   - Sin diagnóstico: {len(info_citas.data) - con_diagnostico}")
    
    print("\n   MÉTRICAS CALCULABLES:")
    print("   ✅ Tasa de documentación (% citas con info completa)")
    print("   ✅ Diagnósticos más frecuentes")
    print("   ✅ Consultas completas vs incompletas")
else:
    print("   ⚠️ NO HAY DATOS de información de citas")

# ===== 7. PAGOS - PRODUCTIVIDAD FINANCIERA =====
print("\n\n📊 7. PAGOS - INGRESOS GENERADOS")
print("-" * 100)

pagos = supabase_client.from_('pagos') \
    .select('id, total, cita_medica_id, fecha_pago') \
    .gte('fecha_pago', hace_30_dias_utc.isoformat()) \
    .execute()

print(f"✅ Tabla: pagos")
print(f"   Pagos últimos 30 días: {len(pagos.data)}")

if pagos.data:
    total_ingresos = sum(float(pago['total']) for pago in pagos.data)
    promedio = total_ingresos / len(pagos.data) if pagos.data else 0
    
    print(f"\n   - Total ingresos: ${total_ingresos:,.0f}")
    print(f"   - Promedio por pago: ${promedio:,.0f}")
    
    print("\n   MÉTRICAS CALCULABLES:")
    print("   ✅ Ingresos generados por doctor")
    print("   ✅ Ingreso promedio por consulta")
    print("   ✅ Ingresos por hora trabajada")
    print("   ✅ Comparativa de productividad financiera")
else:
    print("   ⚠️ NO HAY DATOS de pagos recientes")

# ===== 8. HORARIOS PROGRAMADOS - COMPARATIVA =====
print("\n\n📊 8. HORARIOS_PERSONAL - CUMPLIMIENTO VS PROGRAMADO")
print("-" * 100)

horarios = supabase_client.from_('horarios_personal') \
    .select('id, inicio_bloque, finalizacion_bloque, usuario_sistema_id') \
    .gte('inicio_bloque', hace_30_dias_utc.isoformat()) \
    .limit(100) \
    .execute()

print(f"✅ Tabla: horarios_personal")
print(f"   Horarios programados (últimos 30 días): {len(horarios.data)}")

if horarios.data:
    print("\n   MÉTRICAS CALCULABLES:")
    print("   ✅ Horas programadas vs trabajadas")
    print("   ✅ Turnos cumplidos vs no cumplidos")
    print("   ✅ Porcentaje de cumplimiento de horario")
    print("   ✅ Horas extras (fuera de horario programado)")
else:
    print("   ⚠️ NO HAY HORARIOS programados recientes")

# ===== RESUMEN FINAL =====
print("\n\n" + "=" * 100)
print("RESUMEN: PROPUESTAS IMPLEMENTABLES vs NO IMPLEMENTABLES")
print("=" * 100)

print("\n✅ INMEDIATAMENTE IMPLEMENTABLE (Datos ya existen):")
print("-" * 100)
print("1. ✅ Pacientes atendidos por día (cita_medica)")
print("2. ✅ Pacientes atendidos por hora trabajada (cita_medica + asistencia)")
print("3. ✅ Distribución por especialidad (cita_medica.especialidad_id)")
print("4. ✅ Tasa de atención efectiva (estado de citas)")
print("5. ✅ Ingresos generados (pagos)")
print("6. ✅ Ingreso por hora trabajada (pagos / horas)")
print("7. ✅ Diagnósticos registrados (informacion_cita)")

print("\n⚠️ PARCIALMENTE IMPLEMENTABLE (Requiere poblar tablas):")
print("-" * 100)
if not estados_sample.data:
    print("1. ⚠️ Tasa de puntualidad (asistencia_estados está VACÍA)")
    print("2. ⚠️ Promedio de atrasos (asistencia_estados está VACÍA)")
    print("3. ⚠️ Justificaciones (asistencia_estados está VACÍA)")
else:
    print("1. ✅ Tasa de puntualidad (asistencia_estados tiene datos)")
    print("2. ✅ Promedio de atrasos (asistencia_estados tiene datos)")
    print("3. ✅ Justificaciones (asistencia_estados tiene datos)")

if not marcas_sample.data:
    print("4. ⚠️ Fuente de registro (marcas_asistencia está VACÍA)")
else:
    print("4. ✅ Fuente de registro (marcas_asistencia tiene datos)")

print("\n❌ NO IMPLEMENTABLE (Datos no existen en el sistema):")
print("-" * 100)
print("1. ❌ Satisfacción de pacientes (no hay tabla de ratings/feedback)")
print("2. ❌ Reconsultas <7 días (requiere lógica adicional, es calculable pero complejo)")
print("3. ❌ Quejas/reclamos formales (no hay tabla)")
print("4. ❌ Tiempo de espera generado (no se registra)")

print("\n\n" + "=" * 100)
print("RECOMENDACIÓN FINAL")
print("=" * 100)

print("\n🎯 PRIORIDAD 1 - AGREGAR AL REPORTE HOY:")
print("   1. Pacientes atendidos en el período")
print("   2. Pacientes por día (gráfico de barras)")
print("   3. Tasa de atención (% citas atendidas vs programadas)")
print("   4. Ingresos generados")
print("   5. Distribución por especialidad")

print("\n🎯 PRIORIDAD 2 - REQUIERE POBLAR asistencia_estados:")
print("   1. Tasa de puntualidad")
print("   2. Minutos promedio de atraso")
print("   3. Ausencias justificadas")

print("\n🎯 PRIORIDAD 3 - MEJORAS FUTURAS:")
print("   1. Comparativa con otros doctores")
print("   2. Ranking de productividad")
print("   3. Tendencias mensuales")

print("\n" + "=" * 100)
