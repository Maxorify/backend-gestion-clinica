"""
Verificar datos de TODO DICIEMBRE 2025 para Monica Oyarce
"""
from src.utils.supabase import supabase_client
from datetime import datetime, timezone
import pytz

chile_tz = pytz.timezone('America/Santiago')

doctor_id = 25

print("=" * 100)
print("VERIFICACIÓN DE DATOS - TODO DICIEMBRE 2025")
print("=" * 100)

# Obtener info del doctor
doctor = supabase_client.from_('usuario_sistema') \
    .select('id, nombre, apellido_paterno') \
    .eq('id', doctor_id) \
    .single() \
    .execute()

nombre = f"{doctor.data['nombre']} {doctor.data['apellido_paterno']}" if doctor.data else "Desconocido"
print(f"\nDoctor: {nombre} (ID: {doctor_id})")

# TODO DICIEMBRE
fecha_inicio = datetime(2025, 12, 1, 0, 0, 0, tzinfo=chile_tz).astimezone(timezone.utc)
fecha_fin = datetime(2025, 12, 31, 23, 59, 59, tzinfo=chile_tz).astimezone(timezone.utc)

print(f"Período: TODO DICIEMBRE 2025")
print("=" * 100)

# ===== ASISTENCIAS =====
print("\n📊 ASISTENCIAS DEL MES")
print("-" * 100)

asistencias = supabase_client.from_('asistencia') \
    .select('*') \
    .eq('usuario_sistema_id', doctor_id) \
    .gte('inicio_turno', fecha_inicio.isoformat()) \
    .lte('inicio_turno', fecha_fin.isoformat()) \
    .execute()

print(f"Total asistencias: {len(asistencias.data)}")

total_horas = 0
for asist in asistencias.data:
    inicio = datetime.fromisoformat(asist['inicio_turno'].replace('Z', '+00:00'))
    fin = datetime.fromisoformat(asist['finalizacion_turno'].replace('Z', '+00:00')) if asist.get('finalizacion_turno') else None
    
    inicio_chile = inicio.astimezone(chile_tz)
    
    if fin:
        horas = (fin - inicio).total_seconds() / 3600
        total_horas += horas
        print(f"  ✅ {inicio_chile.strftime('%d/%m %H:%M')}: {horas:.2f} hrs")

print(f"\n📈 TOTAL HORAS DICIEMBRE: {total_horas:.1f} hrs")

# ===== CITAS =====
print("\n\n📊 CITAS DEL MES")
print("-" * 100)

citas = supabase_client.from_('cita_medica') \
    .select('id, fecha_atencion, paciente_id, especialidad_id') \
    .eq('doctor_id', doctor_id) \
    .gte('fecha_atencion', fecha_inicio.isoformat()) \
    .lte('fecha_atencion', fecha_fin.isoformat()) \
    .execute()

print(f"Total citas: {len(citas.data)}")

citas_atendidas = 0
especialidades = {}

for cita in citas.data:
    # Estado
    estado_response = supabase_client.from_('estado') \
        .select('estado') \
        .eq('cita_medica_id', cita['id']) \
        .execute()
    
    estado = estado_response.data[0]['estado'] if estado_response.data else 'Sin estado'
    
    if estado in ['Completada', 'En Consulta']:
        citas_atendidas += 1
    
    # Especialidad
    if cita['especialidad_id']:
        esp = supabase_client.from_('especialidad') \
            .select('nombre') \
            .eq('id', cita['especialidad_id']) \
            .single() \
            .execute()
        if esp.data:
            nombre_esp = esp.data['nombre']
            especialidades[nombre_esp] = especialidades.get(nombre_esp, 0) + 1
    
    fecha = datetime.fromisoformat(cita['fecha_atencion'].replace('Z', '+00:00')).astimezone(chile_tz)
    print(f"  📅 {fecha.strftime('%d/%m %H:%M')} | Estado: {estado}")

print(f"\n📈 CITAS PROGRAMADAS: {len(citas.data)}")
print(f"📈 CITAS ATENDIDAS: {citas_atendidas}")

if especialidades:
    print(f"\n📊 POR ESPECIALIDAD:")
    for esp, cant in especialidades.items():
        print(f"  - {esp}: {cant}")

# ===== PAGOS =====
print("\n\n📊 PAGOS DEL MES")
print("-" * 100)

ingresos = 0
pagos_count = 0

for cita in citas.data:
    pagos = supabase_client.from_('pagos') \
        .select('total, fecha_pago') \
        .eq('cita_medica_id', cita['id']) \
        .execute()
    
    for pago in pagos.data:
        total = float(pago['total'])
        ingresos += total
        pagos_count += 1
        fecha_pago = datetime.fromisoformat(pago['fecha_pago'].replace('Z', '+00:00')).astimezone(chile_tz)
        print(f"  💰 {fecha_pago.strftime('%d/%m')}: ${total:,.0f}")

print(f"\n📈 TOTAL INGRESOS DICIEMBRE: ${ingresos:,.0f}")
print(f"📈 PAGOS REGISTRADOS: {pagos_count}")

# ===== RESUMEN =====
print("\n\n" + "=" * 100)
print("RESUMEN: LO QUE DEBE MOSTRAR EL REPORTE BETA")
print("=" * 100)

print(f"\n✅ Horas Trabajadas: {total_horas:.1f} hrs")
print(f"✅ Pacientes Atendidos: {citas_atendidas}")
print(f"✅ Ingresos Generados: ${ingresos:,.0f}")
print(f"✅ Citas Programadas: {len(citas.data)}")

if total_horas > 0:
    print(f"\n📊 PRODUCTIVIDAD:")
    print(f"  - Pacientes/Hora: {citas_atendidas/total_horas:.2f}")
    if ingresos > 0:
        print(f"  - Ingreso/Hora: ${ingresos/total_horas:,.0f}")
        print(f"  - Promedio/Consulta: ${ingresos/citas_atendidas:,.0f}")

tasa = (citas_atendidas / len(citas.data) * 100) if len(citas.data) > 0 else 0
print(f"  - Tasa Atención: {tasa:.1f}%")
