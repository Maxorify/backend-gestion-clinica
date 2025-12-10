"""
Verificar datos reales de Monica Oyarce entre 9-11 diciembre 2025
para confirmar si el reporte beta está mostrando datos correctos
"""
from src.utils.supabase import supabase_client
from datetime import datetime, timezone
import pytz

chile_tz = pytz.timezone('America/Santiago')

# Datos del empleado (Monica Oyarce, ID 25)
doctor_id = 25

print("=" * 100)
print("VERIFICACIÓN DE DATOS REALES PARA REPORTE BETA")
print("=" * 100)

# Obtener info del doctor
doctor = supabase_client.from_('usuario_sistema') \
    .select('id, nombre, apellido_paterno, apellido_materno') \
    .eq('id', doctor_id) \
    .single() \
    .execute()

if doctor.data:
    nombre_completo = f"{doctor.data['nombre']} {doctor.data['apellido_paterno']} {doctor.data.get('apellido_materno', '')}".strip()
    print(f"\nDoctor: {nombre_completo} (ID: {doctor_id})")
else:
    print(f"❌ Doctor ID {doctor_id} no encontrado")
    exit(1)

# Período del reporte
fecha_inicio = datetime(2025, 12, 9, tzinfo=chile_tz)
fecha_fin = datetime(2025, 12, 12, tzinfo=chile_tz)
fecha_inicio_utc = fecha_inicio.replace(hour=0, minute=0, second=0).astimezone(timezone.utc)
fecha_fin_utc = fecha_fin.replace(hour=23, minute=59, second=59).astimezone(timezone.utc)

print(f"Período: {fecha_inicio.strftime('%d-%m-%Y')} al {fecha_fin.strftime('%d-%m-%Y')}")
print("=" * 100)

# ===== 1. VERIFICAR ASISTENCIAS (HORAS TRABAJADAS) =====
print("\n📊 1. ASISTENCIAS (Horas Trabajadas)")
print("-" * 100)

asistencias = supabase_client.from_('asistencia') \
    .select('*') \
    .eq('usuario_sistema_id', doctor_id) \
    .gte('inicio_turno', fecha_inicio_utc.isoformat()) \
    .lte('inicio_turno', fecha_fin_utc.isoformat()) \
    .execute()

print(f"Asistencias encontradas: {len(asistencias.data)}")

total_horas = 0
for asist in asistencias.data:
    inicio = datetime.fromisoformat(asist['inicio_turno'].replace('Z', '+00:00'))
    fin = datetime.fromisoformat(asist['finalizacion_turno'].replace('Z', '+00:00')) if asist.get('finalizacion_turno') else None
    
    inicio_chile = inicio.astimezone(chile_tz)
    
    if fin:
        fin_chile = fin.astimezone(chile_tz)
        horas = (fin - inicio).total_seconds() / 3600
        total_horas += horas
        print(f"  ✅ {inicio_chile.strftime('%d/%m %H:%M')} - {fin_chile.strftime('%H:%M')}: {horas:.2f} hrs")
    else:
        print(f"  ⚠️ {inicio_chile.strftime('%d/%m %H:%M')} - SIN SALIDA")

print(f"\n📈 TOTAL HORAS TRABAJADAS: {total_horas:.1f} hrs")

# ===== 2. VERIFICAR CITAS MÉDICAS =====
print("\n\n📊 2. CITAS MÉDICAS (Pacientes)")
print("-" * 100)

citas = supabase_client.from_('cita_medica') \
    .select('id, fecha_atencion, paciente_id, especialidad_id') \
    .eq('doctor_id', doctor_id) \
    .gte('fecha_atencion', fecha_inicio_utc.isoformat()) \
    .lte('fecha_atencion', fecha_fin_utc.isoformat()) \
    .execute()

print(f"Citas encontradas: {len(citas.data)}")

citas_por_estado = {
    'Completada': 0,
    'En Consulta': 0,
    'Pendiente': 0,
    'Confirmada': 0,
    'Cancelada': 0
}

for cita in citas.data:
    fecha_atencion = datetime.fromisoformat(cita['fecha_atencion'].replace('Z', '+00:00'))
    fecha_chile = fecha_atencion.astimezone(chile_tz)
    
    # Obtener estado
    estado_response = supabase_client.from_('estado') \
        .select('estado') \
        .eq('cita_medica_id', cita['id']) \
        .execute()
    
    estado = estado_response.data[0]['estado'] if estado_response.data else 'Sin estado'
    if estado in citas_por_estado:
        citas_por_estado[estado] += 1
    
    # Obtener paciente
    paciente = supabase_client.from_('paciente') \
        .select('nombre, apellido_paterno') \
        .eq('id', cita['paciente_id']) \
        .single() \
        .execute()
    
    nombre_pac = f"{paciente.data['nombre']} {paciente.data.get('apellido_paterno', '')}" if paciente.data else "Desconocido"
    
    # Obtener especialidad
    especialidad = "General"
    if cita['especialidad_id']:
        esp = supabase_client.from_('especialidad') \
            .select('nombre') \
            .eq('id', cita['especialidad_id']) \
            .single() \
            .execute()
        especialidad = esp.data['nombre'] if esp.data else "General"
    
    print(f"  📅 {fecha_chile.strftime('%d/%m %H:%M')} | {nombre_pac[:20]:20} | {especialidad[:15]:15} | Estado: {estado}")

print(f"\n📊 DISTRIBUCIÓN POR ESTADO:")
for estado, cantidad in citas_por_estado.items():
    if cantidad > 0:
        print(f"  - {estado}: {cantidad}")

citas_atendidas = citas_por_estado['Completada'] + citas_por_estado['En Consulta']
citas_programadas = len(citas.data)
tasa_atencion = (citas_atendidas / citas_programadas * 100) if citas_programadas > 0 else 0

print(f"\n📈 CITAS PROGRAMADAS: {citas_programadas}")
print(f"📈 CITAS ATENDIDAS: {citas_atendidas}")
print(f"📈 TASA DE ATENCIÓN: {tasa_atencion:.1f}%")

# ===== 3. VERIFICAR PAGOS (INGRESOS) =====
print("\n\n📊 3. PAGOS (Ingresos Generados)")
print("-" * 100)

# Obtener todos los pagos del período
ingresos_totales = 0
pagos_count = 0

for cita in citas.data:
    pagos = supabase_client.from_('pagos') \
        .select('total, fecha_pago, tipo_pago') \
        .eq('cita_medica_id', cita['id']) \
        .execute()
    
    if pagos.data:
        for pago in pagos.data:
            total = float(pago['total'])
            ingresos_totales += total
            pagos_count += 1
            
            fecha_pago = datetime.fromisoformat(pago['fecha_pago'].replace('Z', '+00:00'))
            fecha_pago_chile = fecha_pago.astimezone(chile_tz)
            
            print(f"  💰 {fecha_pago_chile.strftime('%d/%m %H:%M')} | ${total:,.0f} | Tipo: {pago.get('tipo_pago', 'N/A')}")

print(f"\n📈 TOTAL INGRESOS: ${ingresos_totales:,.0f}")
print(f"📈 PAGOS REGISTRADOS: {pagos_count}")

if pagos_count > 0:
    print(f"📈 PROMEDIO POR PAGO: ${ingresos_totales/pagos_count:,.0f}")

# ===== 4. CALCULAR MÉTRICAS DEL REPORTE =====
print("\n\n" + "=" * 100)
print("RESUMEN: DATOS QUE DEBERÍA MOSTRAR EL REPORTE BETA")
print("=" * 100)

print(f"\n✅ Horas Trabajadas: {total_horas:.1f} hrs")
print(f"✅ Pacientes Atendidos: {citas_atendidas}")
print(f"✅ Ingresos Generados: ${ingresos_totales:,.0f}")

if total_horas > 0:
    print(f"\n📊 PRODUCTIVIDAD:")
    print(f"  - Pacientes/Hora: {citas_atendidas/total_horas:.2f}")
    print(f"  - Ingreso/Hora: ${ingresos_totales/total_horas:,.0f}")

if citas_atendidas > 0:
    print(f"  - Promedio/Consulta: ${ingresos_totales/citas_atendidas:,.0f}")

print(f"\n📊 TASA DE ATENCIÓN: {tasa_atencion:.1f}%")

# ===== 5. VERIFICAR SI ESOS SON LOS VALORES EN EL PDF =====
print("\n\n" + "=" * 100)
print("⚠️ VERIFICACIÓN: ¿El PDF muestra estos valores?")
print("=" * 100)

print(f"\nSegún la imagen del PDF:")
print(f"  - Horas Trabajadas: 8.4 hrs")
print(f"  - Pacientes Atendidos: 0")
print(f"  - Ingresos Generados: $0")

print(f"\nDatos REALES calculados:")
print(f"  - Horas Trabajadas: {total_horas:.1f} hrs ✅ {'COINCIDE' if abs(total_horas - 8.4) < 0.5 else '❌ NO COINCIDE'}")
print(f"  - Pacientes Atendidos: {citas_atendidas} ❌ {'COINCIDE' if citas_atendidas == 0 else 'NO COINCIDE - PDF muestra 0'}")
print(f"  - Ingresos Generados: ${ingresos_totales:,.0f} ❌ {'COINCIDE' if ingresos_totales == 0 else 'NO COINCIDE - PDF muestra $0'}")

if citas_programadas > 0 or ingresos_totales > 0:
    print("\n❌ PROBLEMA DETECTADO:")
    print("   El reporte PDF BETA está mostrando 0 pacientes y $0 en ingresos")
    print("   cuando en realidad HAY datos en la base de datos.")
    print("\n   Causa probable: Las llamadas al API en generarReporteAsistenciaBetaPDF.js están fallando")
    print("   o los endpoints no existen/no retornan datos correctamente.")
else:
    print("\n✅ Los datos son correctos - realmente NO hay pacientes ni ingresos en este período")
