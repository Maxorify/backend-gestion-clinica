from datetime import datetime
from zoneinfo import ZoneInfo

# Simular lo que muestra el frontend
bloques = [
    "2025-12-04T11:00:00+00:00",  # Primer bloque
    "2025-12-05T00:00:00+00:00",  # Bloque que cruza medianoche
    "2025-12-05T00:30:00+00:00",  # Último bloque
]

print("🔍 CONVERSIÓN UTC → CHILE:")
print("=" * 60)

for bloque_utc in bloques:
    dt_utc = datetime.fromisoformat(bloque_utc.replace("Z", "+00:00"))
    
    # Método 1: Restar 3 horas manualmente (lo que hace el frontend ahora)
    dt_chile_manual = datetime.fromtimestamp(dt_utc.timestamp() - 3*60*60)
    fecha_chile_manual = dt_chile_manual.strftime("%Y-%m-%d %H:%M")
    
    # Método 2: Usar ZoneInfo (correcto)
    chile_tz = ZoneInfo("America/Santiago")
    dt_chile_correcto = dt_utc.astimezone(chile_tz)
    fecha_chile_correcto = dt_chile_correcto.strftime("%Y-%m-%d %H:%M %Z")
    
    print(f"\nUTC:            {bloque_utc}")
    print(f"Manual (-3h):   {fecha_chile_manual}")
    print(f"ZoneInfo Chile: {fecha_chile_correcto}")
    print(f"Fecha solo:     {dt_chile_correcto.strftime('%Y-%m-%d')}")
