"""
Arreglar estado de cita de Cecilia
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

print("🔍 Buscando cita de Cecilia...")

# Buscar cita de Cecilia
response = supabase.table("cita_medica") \
    .select("*, paciente:paciente_id(nombre, apellido_paterno)") \
    .gte("fecha_atencion", "2025-12-09T00:00:00") \
    .lte("fecha_atencion", "2025-12-11T00:00:00") \
    .execute()

cita_cecilia = None
for cita in response.data:
    paciente = cita.get('paciente', {})
    if 'cecilia' in paciente.get('nombre', '').lower():
        cita_cecilia = cita
        break

if not cita_cecilia:
    print("❌ No se encontró la cita de Cecilia")
    exit(1)

cita_id = cita_cecilia['id']
print(f"✅ Cita encontrada: ID={cita_id}")
print(f"   Paciente: {cita_cecilia['paciente']['nombre']} {cita_cecilia['paciente']['apellido_paterno']}")
print(f"   Fecha: {cita_cecilia['fecha_atencion']}")

# Verificar si ya tiene estado
estado_actual = supabase.table("estado") \
    .select("*") \
    .eq("cita_medica_id", cita_id) \
    .execute()

if estado_actual.data:
    print(f"\n⚠️  La cita YA tiene estado: {estado_actual.data[0]['estado']}")
else:
    print(f"\n📝 Creando estado inicial 'Pendiente'...")
    nuevo_estado = supabase.table("estado") \
        .insert({
            "estado": "Pendiente",
            "cita_medica_id": cita_id
        }) \
        .execute()
    
    if nuevo_estado.data:
        print(f"✅ Estado creado exitosamente!")
        print(f"   Estado: Pendiente")
        print(f"   Cita ID: {cita_id}")
    else:
        print(f"❌ Error al crear el estado")

print("\n🎯 Ahora la cita debería aparecer en CitasDoctor.jsx")
