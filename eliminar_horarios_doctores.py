"""
Eliminar TODOS los horarios asignados de Juanito Perez y Jose Perez
NO elimina las citas, solo los horarios_personal
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

print("=" * 80)
print("🗑️  ELIMINANDO HORARIOS ASIGNADOS")
print("=" * 80)

# Buscar IDs de los doctores
print("\n🔍 Buscando doctores...")

# Juanito Perez
juanito = supabase.table("usuario_sistema") \
    .select("id, nombre, apellido_paterno, apellido_materno") \
    .ilike("nombre", "%juanito%") \
    .ilike("apellido_paterno", "%perez%") \
    .execute()

# Jose Perez
jose = supabase.table("usuario_sistema") \
    .select("id, nombre, apellido_paterno, apellido_materno") \
    .ilike("nombre", "%jose%") \
    .ilike("apellido_paterno", "%perez%") \
    .execute()

doctores_ids = []
nombres_doctores = []

if juanito.data:
    for doc in juanito.data:
        doctores_ids.append(doc['id'])
        nombre_completo = f"{doc['nombre']} {doc['apellido_paterno']} {doc.get('apellido_materno', '')}"
        nombres_doctores.append(nombre_completo)
        print(f"✅ Encontrado: {nombre_completo} (ID: {doc['id']})")

if jose.data:
    for doc in jose.data:
        if doc['id'] not in doctores_ids:  # Evitar duplicados
            doctores_ids.append(doc['id'])
            nombre_completo = f"{doc['nombre']} {doc['apellido_paterno']} {doc.get('apellido_materno', '')}"
            nombres_doctores.append(nombre_completo)
            print(f"✅ Encontrado: {nombre_completo} (ID: {doc['id']})")

if not doctores_ids:
    print("❌ No se encontraron los doctores")
    exit(1)

print(f"\n📊 Total doctores encontrados: {len(doctores_ids)}")

# Contar horarios antes de eliminar
total_horarios = 0
for doctor_id in doctores_ids:
    horarios = supabase.table("horarios_personal") \
        .select("id", count="exact") \
        .eq("usuario_sistema_id", doctor_id) \
        .execute()
    
    count = horarios.count if hasattr(horarios, 'count') else len(horarios.data)
    total_horarios += count
    print(f"   Doctor ID {doctor_id}: {count} horarios asignados")

if total_horarios == 0:
    print("\n✅ No hay horarios asignados para eliminar")
    exit(0)

print(f"\n⚠️  TOTAL A ELIMINAR: {total_horarios} horarios")
print(f"⚠️  Doctores afectados: {', '.join(nombres_doctores)}")

# Eliminar horarios
print(f"\n🗑️  Eliminando horarios...")
horarios_eliminados = 0

for doctor_id in doctores_ids:
    resultado = supabase.table("horarios_personal") \
        .delete() \
        .eq("usuario_sistema_id", doctor_id) \
        .execute()
    
    eliminados = len(resultado.data) if resultado.data else 0
    horarios_eliminados += eliminados
    print(f"   ✅ Doctor ID {doctor_id}: {eliminados} horarios eliminados")

print("\n" + "=" * 80)
print(f"✅ COMPLETADO: {horarios_eliminados} horarios eliminados exitosamente")
print(f"📝 Las citas médicas NO fueron afectadas")
print("=" * 80)
