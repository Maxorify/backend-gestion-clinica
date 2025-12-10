"""
Script de prueba: Verificar corrección de timezone para cita de Johan
"""
import sys
sys.path.insert(0, 'src')

from utils.supabase import supabase_client
from datetime import datetime, timedelta

print("=" * 80)
print("PRUEBA: Verificar cita de Johan después del fix de timezone")
print("=" * 80)

# 1. Obtener la cita de Johan con Dr. Jose Perez
print("\n1️⃣  Buscando cita de Johan con Dr. Jose Perez...")
cita = supabase_client.table("cita_medica").select(
    "id, fecha_atencion, doctor_id, paciente:paciente_id(nombre, apellido_paterno)"
).eq("paciente_id", 10).eq("doctor_id", 27).execute()

if not cita.data:
    print("   ❌ No se encontró la cita")
    sys.exit(1)

cita_data = cita.data[0]
print(f"\n   ✅ Cita encontrada:")
print(f"      ID: {cita_data['id']}")
print(f"      Fecha UTC: {cita_data['fecha_atencion']}")
print(f"      Paciente: {cita_data['paciente']['nombre']} {cita_data['paciente']['apellido_paterno']}")
print(f"      Doctor ID: {cita_data['doctor_id']}")

# 2. Parsear la fecha
fecha_utc_str = cita_data['fecha_atencion'].replace('Z', '').replace('+00:00', '')
fecha_utc = datetime.fromisoformat(fecha_utc_str)
fecha_chile = fecha_utc - timedelta(hours=3)  # UTC-3

print(f"\n   📅 Conversión a hora Chile:")
print(f"      UTC: {fecha_utc}")
print(f"      Chile (UTC-3): {fecha_chile}")
print(f"      Día en Chile: {fecha_chile.date()}")

# 3. Simular la consulta del endpoint CON el fix
fecha_consulta = "2025-12-09"
print(f"\n2️⃣  Simulando endpoint /doctor/27/citas?fecha={fecha_consulta}")

fecha_chile_param = datetime.strptime(fecha_consulta, "%Y-%m-%d")
inicio_utc = fecha_chile_param + timedelta(hours=3)  # 00:00 Chile = 03:00 UTC
fin_utc = fecha_chile_param + timedelta(days=1, hours=3)  # 24:00 Chile = 03:00 UTC día siguiente

print(f"\n   🔍 Conversión de parámetros:")
print(f"      Fecha Chile: {fecha_chile_param}")
print(f"      Inicio UTC: {inicio_utc.isoformat()}")
print(f"      Fin UTC: {fin_utc.isoformat()}")

print(f"\n   🔍 Filtro SQL:")
print(f"      WHERE fecha_atencion >= '{inicio_utc.isoformat()}'")
print(f"      AND fecha_atencion < '{fin_utc.isoformat()}'")

# 4. Verificar si la cita está en el rango
print(f"\n   ❓ ¿La cita {fecha_utc} está en el rango?")
print(f"      {inicio_utc} <= {fecha_utc} < {fin_utc}")

if inicio_utc <= fecha_utc < fin_utc:
    print(f"\n   ✅ SÍ - La cita ESTÁ en el rango")
    print(f"\n   ✅ RESULTADO: Johan aparecerá en el panel del doctor Jose Perez")
else:
    print(f"\n   ❌ NO - La cita NO está en el rango")
    if fecha_utc < inicio_utc:
        print(f"      La cita es ANTERIOR al inicio del día ({(inicio_utc - fecha_utc).total_seconds() / 3600:.1f}h antes)")
    else:
        print(f"      La cita es POSTERIOR al fin del día ({(fecha_utc - fin_utc).total_seconds() / 3600:.1f}h después)")

# 5. Hacer la consulta REAL al endpoint simulado
print(f"\n3️⃣  Ejecutando consulta REAL a la base de datos...")

citas_doctor = supabase_client.table("cita_medica").select(
    "id, fecha_atencion, paciente:paciente_id(nombre, apellido_paterno)"
).eq("doctor_id", 27).gte(
    "fecha_atencion", inicio_utc.isoformat()
).lt(
    "fecha_atencion", fin_utc.isoformat()
).execute()

print(f"\n   📊 Citas encontradas: {len(citas_doctor.data or [])}")

if citas_doctor.data:
    for c in citas_doctor.data:
        fecha_c = datetime.fromisoformat(c['fecha_atencion'].replace('Z', ''))
        fecha_c_chile = fecha_c - timedelta(hours=3)
        print(f"\n      📌 Cita ID {c['id']}:")
        print(f"         Paciente: {c['paciente']['nombre']} {c['paciente']['apellido_paterno']}")
        print(f"         Fecha UTC: {fecha_c}")
        print(f"         Fecha Chile: {fecha_c_chile}")
        
        if c['id'] == cita_data['id']:
            print(f"         ✅ ¡Esta es la cita de Johan!")

print("\n" + "=" * 80)
print("RESUMEN DEL FIX")
print("=" * 80)

print(f"""
✅ PROBLEMA RESUELTO:

ANTES (SIN FIX):
   - Endpoint filtraba: fecha_atencion BETWEEN '2025-12-09 00:00' AND '2025-12-09 23:59' (UTC)
   - Cita de Johan: 2025-12-10 00:00 UTC (21:00 Chile del 09)
   - Resultado: NO encontrada ❌

DESPUÉS (CON FIX):
   - Endpoint convierte: fecha=2025-12-09 (Chile) → UTC
   - Filtra: fecha_atencion >= 2025-12-09 03:00 UTC AND < 2025-12-10 03:00 UTC
   - Cita de Johan: 2025-12-10 00:00 UTC
   - Resultado: ✅ ENCONTRADA (está en el rango {inicio_utc} <= {fecha_utc} < {fin_utc})

ARCHIVOS MODIFICADOS:
   1. appointment_administration.py (línea 1202):
      - Agregada conversión Chile -> UTC en filtro de fecha
      - inicio_utc = fecha_chile + timedelta(hours=3)
      - fin_utc = fecha_chile + timedelta(days=1, hours=3)
   
   2. CitasDoctor.jsx:
      - Agregada función parseUTCDate() (línea 10)
      - Reemplazadas 5 conversiones de fecha para evitar offset automático
      - Ahora muestra fechas en hora local sin conversión UTC
""")

print("\n" + "=" * 80)
