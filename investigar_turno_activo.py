"""
Investigar el turno que aparece como "En turno" en el reporte del 5 de diciembre 2025
"""
from src.utils.supabase import supabase_client
from datetime import datetime, timezone, timedelta
import pytz

chile_tz = pytz.timezone('America/Santiago')

# Buscar asistencias del 5 de diciembre 2025
fecha = datetime(2025, 12, 5, tzinfo=chile_tz)
fecha_inicio = fecha.replace(hour=0, minute=0, second=0).astimezone(timezone.utc)
fecha_fin = fecha.replace(hour=23, minute=59, second=59).astimezone(timezone.utc)

response = supabase_client.from_('asistencia') \
    .select('*') \
    .gte('inicio_turno', fecha_inicio.isoformat()) \
    .lte('inicio_turno', fecha_fin.isoformat()) \
    .execute()

print('=== ASISTENCIAS DEL 5 DE DICIEMBRE 2025 ===\n')
print(f'Total encontradas: {len(response.data)}\n')

for asist in response.data:
    print(f'ID Asistencia: {asist["id"]}')
    print(f'Usuario ID: {asist["usuario_sistema_id"]}')
    
    # Obtener info del usuario
    user_resp = supabase_client.from_('usuario_sistema') \
        .select('nombre, apellido_paterno, apellido_materno') \
        .eq('id', asist["usuario_sistema_id"]) \
        .single() \
        .execute()
    
    if user_resp.data:
        nombre_completo = f"{user_resp.data['nombre']} {user_resp.data['apellido_paterno']} {user_resp.data.get('apellido_materno', '')}".strip()
        print(f'Doctor: {nombre_completo}')
    
    print(f'Inicio Turno (UTC): {asist["inicio_turno"]}')
    print(f'Finalizacion Turno (UTC): {asist.get("finalizacion_turno", "❌ NULL - SIN MARCA DE SALIDA")}')
    
    # Convertir a Chile
    inicio = datetime.fromisoformat(asist['inicio_turno'].replace('Z', '+00:00'))
    inicio_chile = inicio.astimezone(chile_tz)
    print(f'Inicio Turno (Chile): {inicio_chile.strftime("%Y-%m-%d %H:%M:%S")}')
    
    if asist.get('finalizacion_turno'):
        fin = datetime.fromisoformat(asist['finalizacion_turno'].replace('Z', '+00:00'))
        fin_chile = fin.astimezone(chile_tz)
        print(f'Finalizacion Turno (Chile): {fin_chile.strftime("%Y-%m-%d %H:%M:%S")}')
        diff_horas = (fin - inicio).total_seconds() / 3600
        print(f'✅ Horas trabajadas: {diff_horas:.2f}')
    else:
        ahora = datetime.now(timezone.utc)
        diff_horas = (ahora - inicio).total_seconds() / 3600
        print(f'⚠️ TURNO ACTIVO (SIN SALIDA)')
        print(f'   Horas transcurridas desde entrada: {diff_horas:.2f}')
        print(f'   Fecha actual: {datetime.now(chile_tz).strftime("%Y-%m-%d %H:%M:%S")} (Chile)')
        
        # Calcular cuánto tiempo ha pasado desde el turno
        dias_transcurridos = (datetime.now(chile_tz).date() - inicio_chile.date()).days
        print(f'   ⚠️ Han pasado {dias_transcurridos} días desde la entrada')
    
    print(f'Created at: {asist.get("created_at", "N/A")}')
    print('=' * 80)

# Buscar también en fechas cercanas para ver si hay un patrón
print('\n\n=== BÚSQUEDA AMPLIADA: 4-6 DICIEMBRE ===\n')
fecha_amplia_inicio = datetime(2025, 12, 4, tzinfo=chile_tz).replace(hour=0, minute=0).astimezone(timezone.utc)
fecha_amplia_fin = datetime(2025, 12, 6, tzinfo=chile_tz).replace(hour=23, minute=59).astimezone(timezone.utc)

response_amplia = supabase_client.from_('asistencia') \
    .select('id, usuario_sistema_id, inicio_turno, finalizacion_turno') \
    .gte('inicio_turno', fecha_amplia_inicio.isoformat()) \
    .lte('inicio_turno', fecha_amplia_fin.isoformat()) \
    .order('inicio_turno', desc=False) \
    .execute()

sin_salida = []
con_salida = []

for asist in response_amplia.data:
    inicio = datetime.fromisoformat(asist['inicio_turno'].replace('Z', '+00:00'))
    inicio_chile = inicio.astimezone(chile_tz)
    fecha_str = inicio_chile.strftime("%d-%m-%Y %H:%M")
    
    if asist.get('finalizacion_turno'):
        con_salida.append(f"  ✅ ID {asist['id']}: {fecha_str} (Usuario {asist['usuario_sistema_id']})")
    else:
        sin_salida.append(f"  ❌ ID {asist['id']}: {fecha_str} (Usuario {asist['usuario_sistema_id']}) - SIN SALIDA")

print(f'Turnos CON salida registrada: {len(con_salida)}')
for t in con_salida:
    print(t)

print(f'\nTurnos SIN salida registrada: {len(sin_salida)}')
for t in sin_salida:
    print(t)
