import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("🔍 VERIFICANDO ESTADOS REALES DE CITAS DE MONICA DICIEMBRE 2025")
print("=" * 80)

# Obtener ID de Monica
monica_query = supabase.table("usuario_sistema").select("id, nombre, apellido_paterno").eq("nombre", "Monica").eq("apellido_paterno", "Oyarce").execute()

if not monica_query.data:
    print("❌ No se encontró a Monica Oyarce")
    exit()

monica_id = monica_query.data[0]["id"]
print(f"\n✅ Monica Oyarce encontrada - ID: {monica_id}")

# Obtener todas las citas de diciembre 2025
citas_query = supabase.table("cita_medica")\
    .select("id, fecha_atencion, paciente_id, especialidad_id")\
    .eq("doctor_id", monica_id)\
    .gte("fecha_atencion", "2025-12-01T00:00:00")\
    .lt("fecha_atencion", "2026-01-01T00:00:00")\
    .order("fecha_atencion")\
    .execute()

print(f"\n📅 Citas encontradas en diciembre: {len(citas_query.data)}")
print("=" * 80)

for cita in citas_query.data:
    cita_id = cita["id"]
    fecha = cita["fecha_atencion"]
    
    # Obtener paciente
    paciente_query = supabase.table("paciente").select("nombre, apellido_paterno").eq("id", cita["paciente_id"]).execute()
    paciente_nombre = f"{paciente_query.data[0]['nombre']} {paciente_query.data[0]['apellido_paterno']}" if paciente_query.data else "Desconocido"
    
    # Obtener especialidad
    especialidad_query = supabase.table("especialidad").select("nombre").eq("id", cita["especialidad_id"]).execute()
    especialidad_nombre = especialidad_query.data[0]["nombre"] if especialidad_query.data else "Sin especialidad"
    
    # Obtener TODOS los estados de esta cita (ordenados por ID)
    estados_query = supabase.table("estado")\
        .select("id, estado")\
        .eq("cita_medica_id", cita_id)\
        .order("id")\
        .execute()
    
    # Estado actual (el último)
    estado_actual = estados_query.data[-1]["estado"] if estados_query.data else "Sin estado"
    
    # Obtener pago
    pago_query = supabase.table("pagos").select("total").eq("cita_medica_id", cita_id).execute()
    monto_pago = f"${float(pago_query.data[0]['total']):,.0f}" if pago_query.data else "Sin pago"
    
    print(f"\n📋 Cita ID: {cita_id}")
    print(f"   📅 Fecha: {fecha}")
    print(f"   👤 Paciente: {paciente_nombre}")
    print(f"   🏥 Especialidad: {especialidad_nombre}")
    print(f"   📊 Estado actual: {estado_actual}")
    print(f"   💰 Pago: {monto_pago}")
    print(f"   🔄 Historial de estados ({len(estados_query.data)}):")
    for estado in estados_query.data:
        print(f"      - {estado['estado']} (ID: {estado['id']})")

print("\n" + "=" * 80)
print("📊 RESUMEN")
print("=" * 80)

# Contar por estado
estados_count = {}
for cita in citas_query.data:
    estados_query = supabase.table("estado")\
        .select("estado")\
        .eq("cita_medica_id", cita["id"])\
        .order("id", desc=True)\
        .limit(1)\
        .execute()
    
    estado = estados_query.data[0]["estado"] if estados_query.data else "Sin estado"
    estados_count[estado] = estados_count.get(estado, 0) + 1

print("\nDistribución de estados:")
for estado, count in estados_count.items():
    print(f"  - {estado}: {count} citas")

# Contar pagos totales
pagos_query = supabase.table("pagos")\
    .select("total, cita_medica_id")\
    .execute()

total_pagos = 0
pagos_monica = []
for pago in pagos_query.data:
    # Verificar si la cita pertenece a Monica
    cita_check = supabase.table("cita_medica").select("doctor_id, fecha_atencion").eq("id", pago["cita_medica_id"]).execute()
    if cita_check.data and cita_check.data[0]["doctor_id"] == monica_id:
        # Verificar si es de diciembre
        fecha_str = cita_check.data[0]["fecha_atencion"]
        if fecha_str.startswith("2025-12"):
            monto = float(pago["total"])
            total_pagos += monto
            pagos_monica.append((pago["cita_medica_id"], monto))

print(f"\n💰 Total de ingresos en diciembre: ${total_pagos:,.0f}")
print(f"   Cantidad de pagos: {len(pagos_monica)}")

print("\n" + "=" * 80)
