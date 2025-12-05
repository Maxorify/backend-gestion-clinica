from datetime import datetime
from zoneinfo import ZoneInfo

# Simular lo que hace el código
fecha = datetime(2025, 12, 4).date()
hora_inicio_str = "08:00"
hora_fin_str = "22:00"

chile_tz = ZoneInfo("America/Santiago")

# Crear datetime con timezone Chile
hora_inicio = datetime.combine(
    fecha,
    datetime.strptime(hora_inicio_str, "%H:%M").time(),
    tzinfo=chile_tz
)

hora_fin = datetime.combine(
    fecha,
    datetime.strptime(hora_fin_str, "%H:%M").time(),
    tzinfo=chile_tz
)

print("🔍 DEBUG TIMEZONE CONVERSION:")
print(f"Fecha: {fecha}")
print(f"Hora inicio Chile: {hora_inicio}")
print(f"Hora inicio UTC: {hora_inicio.astimezone(ZoneInfo('UTC'))}")
print(f"Hora inicio ISO: {hora_inicio.isoformat()}")
print()
print(f"Hora fin Chile: {hora_fin}")
print(f"Hora fin UTC: {hora_fin.astimezone(ZoneInfo('UTC'))}")
print(f"Hora fin ISO: {hora_fin.isoformat()}")
print()

# Verificar offset
print(f"UTC offset Chile: {hora_inicio.strftime('%z')} ({hora_inicio.tzname()})")
print(f"Diferencia en horas: {hora_inicio.utcoffset().total_seconds() / 3600}")
