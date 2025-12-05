from datetime import datetime

# Verificar qué día de la semana es el 4 de diciembre de 2025
fecha = datetime(2025, 12, 4)

print(f"📅 Fecha: {fecha.strftime('%Y-%m-%d')}")
print(f"Día de la semana: {fecha.strftime('%A')}")
print(f"weekday(): {fecha.weekday()} (0=Lunes, 6=Domingo)")
print(f"isoweekday(): {fecha.isoweekday()} (1=Lunes, 7=Domingo)")

# Verificar para los 3 jueves
fechas_jueves = [
    datetime(2025, 12, 4),
    datetime(2025, 12, 11),
    datetime(2025, 12, 18),
]

print("\n🔍 Verificación de los jueves:")
for f in fechas_jueves:
    print(f"  {f.strftime('%Y-%m-%d')} → {f.strftime('%A')} (weekday: {f.weekday()})")

print("\n📝 En el código:")
print("  dia_semana: 3 = Jueves (0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves)")
print("\n¿Cuándo seleccionaste 'Jueves' en el frontend?")
