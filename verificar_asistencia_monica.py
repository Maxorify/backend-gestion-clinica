from src.utils.supabase import supabase_client
from datetime import date

# Verificar si hay asistencia registrada para Monica hoy
fecha_hoy = date.today()

print(f"🔍 Buscando asistencias para Monica (ID: 25) en fecha {fecha_hoy}")

result = supabase_client.from_("asistencia") \
    .select("*") \
    .eq("usuario_sistema_id", 25) \
    .gte("inicio_turno", f"{fecha_hoy}T00:00:00") \
    .lte("inicio_turno", f"{fecha_hoy}T23:59:59") \
    .execute()

if result.data:
    print(f"\n✅ Encontradas {len(result.data)} asistencias:")
    for asist in result.data:
        print(f"\n  ID: {asist['id']}")
        print(f"  horario_id: {asist.get('horario_id')}")
        print(f"  inicio_turno: {asist.get('inicio_turno')}")
        print(f"  finalizacion_turno: {asist.get('finalizacion_turno')}")
        print(f"  fuente_entrada: {asist.get('fuente_entrada')}")
else:
    print("\n❌ No hay asistencias registradas")
    print("\nBuscando en todo el rango (ampliado):")
    
    result2 = supabase_client.from_("asistencia") \
        .select("*") \
        .eq("usuario_sistema_id", 25) \
        .execute()
    
    if result2.data:
        print(f"✅ Encontradas {len(result2.data)} asistencias en total:")
        for asist in result2.data:
            print(f"  - ID {asist['id']}: {asist.get('inicio_turno')}")
    else:
        print("❌ No hay NINGUNA asistencia para Monica")
