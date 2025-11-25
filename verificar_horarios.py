from src.utils.supabase import supabase_client
from datetime import datetime

# Verificar horarios para el 25/11/2025
result = supabase_client.from_('horarios_personal').select('*, usuario:usuario_sistema_id(nombre, apellido_paterno, apellido_materno)').gte('inicio_bloque', '2025-11-25T00:00:00').lte('inicio_bloque', '2025-11-25T23:59:59').execute()

print(f'Horarios para 25/11/2025: {len(result.data)}')
for h in result.data:
    if h.get('usuario'):
        print(f"  - ID {h['id']}: {h['usuario']['nombre']} {h['usuario']['apellido_paterno']} - {h['inicio_bloque']} a {h['finalizacion_bloque']}")

# Verificar asistencia para el 25/11/2025
result2 = supabase_client.from_('asistencia').select('*').gte('inicio_turno', '2025-11-25T00:00:00').lte('inicio_turno', '2025-11-25T23:59:59').execute()
print(f'\nAsistencias para 25/11/2025: {len(result2.data)}')
for a in result2.data:
    print(f"  - ID {a['id']}: Usuario {a['usuario_sistema_id']} - {a['inicio_turno']} a {a.get('finalizacion_turno', 'EN CURSO')}")
