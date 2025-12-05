from src.utils.supabase import supabase_client
from datetime import date

# Ver TODAS las asistencias del doctor 20 hoy
hoy = date.today()
result = supabase_client.from_('asistencia').select('*').eq('usuario_sistema_id', 20).gte('inicio_turno', f'{hoy}T00:00:00').order('id', desc=True).execute()

print(f"Total asistencias hoy para doctor 20: {len(result.data)}")
print("=" * 80)
for asist in result.data:
    print(f"ID: {asist['id']}")
    print(f"  Inicio: {asist['inicio_turno']}")
    print(f"  Fin: {asist.get('finalizacion_turno', 'SIN SALIDA')}")
    print("-" * 80)
