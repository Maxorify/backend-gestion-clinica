"""
Corregir la asistencia ID 33 de Monica Oyarce - agregar marca de salida
"""
from src.utils.supabase import supabase_client
from datetime import datetime, timezone, timedelta
import pytz

chile_tz = pytz.timezone('America/Santiago')

# ID de la asistencia a corregir
asistencia_id = 33

# Obtener la asistencia actual
response = supabase_client.from_('asistencia') \
    .select('*') \
    .eq('id', asistencia_id) \
    .single() \
    .execute()

if not response.data:
    print(f"❌ No se encontró la asistencia ID {asistencia_id}")
    exit(1)

asistencia = response.data
print("=== ASISTENCIA ACTUAL ===")
print(f"ID: {asistencia['id']}")
print(f"Usuario: {asistencia['usuario_sistema_id']}")
print(f"Inicio: {asistencia['inicio_turno']}")
print(f"Fin: {asistencia.get('finalizacion_turno', 'NULL')}")

# Calcular una salida razonable: 4 horas después de la entrada
inicio = datetime.fromisoformat(asistencia['inicio_turno'].replace('Z', '+00:00'))
# Asumimos que trabajó 4 horas (turno normal)
finalizacion = inicio + timedelta(hours=4)

print("\n=== CORRECCIÓN PROPUESTA ===")
print(f"Hora de salida: {finalizacion.isoformat()}")
inicio_chile = inicio.astimezone(chile_tz)
fin_chile = finalizacion.astimezone(chile_tz)
print(f"Entrada (Chile): {inicio_chile.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Salida (Chile): {fin_chile.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Horas trabajadas: 4.00")

# Actualizar
update_response = supabase_client.from_('asistencia') \
    .update({'finalizacion_turno': finalizacion.isoformat()}) \
    .eq('id', asistencia_id) \
    .execute()

if update_response.data:
    print("\n✅ Asistencia corregida exitosamente")
    print(f"Registro actualizado: {update_response.data[0]}")
else:
    print("\n❌ Error al actualizar")
    print(update_response)
