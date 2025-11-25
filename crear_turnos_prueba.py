from src.utils.supabase import supabase_client
from datetime import datetime

# Obtener doctores (rol_id = 2)
doctores = supabase_client.from_('usuario_sistema').select('id, nombre, apellido_paterno').eq('rol_id', 2).limit(5).execute().data
print(f"Doctores encontrados: {len(doctores)}")
for d in doctores:
    print(f"  - ID {d['id']}: Dr. {d['nombre']} {d['apellido_paterno']}")

# Crear turnos para el 24/11/2025 (8am - 4pm)
turnos = []
for doctor in doctores:
    turno = {
        'inicio_turno': datetime(2025, 11, 24, 8, 0).isoformat(),
        'finalizacion_turno': datetime(2025, 11, 24, 16, 0).isoformat(),
        'usuario_sistema_id': doctor['id']
    }
    turnos.append(turno)

# Insertar turnos
result = supabase_client.from_('asistencia').insert(turnos).execute()
print(f"\n✅ Turnos creados para el 24/11/2025: {len(result.data)}")
print("\nAhora recarga la página de asistencia y deberían aparecer los doctores.")
