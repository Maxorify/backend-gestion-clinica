from datetime import datetime, timezone, timedelta

# Simular lo que hace el backend
fecha = datetime.strptime("2025-12-04", "%Y-%m-%d").date()
hora_inicio_str = "08:00"
hora_fin_str = "09:00"

# Crear datetimes
hora_bloque = datetime.combine(fecha, datetime.strptime(hora_inicio_str, "%H:%M").time())
hora_fin_dia = datetime.combine(fecha, datetime.strptime(hora_fin_str, "%H:%M").time())

print(f"ANTES de timezone:")
print(f"  hora_bloque: {hora_bloque} (naive)")
print(f"  hora_fin_dia: {hora_fin_dia} (naive)")

# Aplicar timezone Chile
chile_tz = timezone(timedelta(hours=-3))
hora_bloque_utc = hora_bloque.replace(tzinfo=chile_tz).astimezone(timezone.utc)
hora_fin_dia_utc = hora_fin_dia.replace(tzinfo=chile_tz).astimezone(timezone.utc)

print(f"\nDESPUÉS de conversión a UTC:")
print(f"  hora_bloque_utc: {hora_bloque_utc}")
print(f"  hora_fin_dia_utc: {hora_fin_dia_utc}")

# Simular creación de bloques
bloques = []
duracion = 30
current = hora_bloque_utc

while current < hora_fin_dia_utc:
    fin = current + timedelta(minutes=duracion)
    if fin > hora_fin_dia_utc:
        break
    bloques.append((current, fin))
    current = fin

print(f"\nBLOQUES GENERADOS: {len(bloques)}")
for i, (inicio, fin) in enumerate(bloques, 1):
    print(f"  {i}. {inicio.isoformat()} → {fin.isoformat()}")
