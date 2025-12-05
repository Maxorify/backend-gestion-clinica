from datetime import datetime

primer_dia = datetime(2025, 12, 1)
print(f"1 de diciembre 2025: {primer_dia.strftime('%A')}")
print(f"getDay() debería devolver: {primer_dia.weekday()}")  # En Python weekday()
print(f"En JavaScript getDay() devolvería: {(primer_dia.weekday() + 1) % 7}")  # JS usa 0=Dom

# Simular lógica JavaScript
primer_dia_semana_js = (primer_dia.weekday() + 1) % 7  # Convertir a sistema JavaScript
dias_anteriores = 6 if primer_dia_semana_js == 0 else primer_dia_semana_js - 1

print(f"\nprimerDiaSemana (JS): {primer_dia_semana_js}")
print(f"diasAnteriores: {dias_anteriores}")
print(f"\nEsto significa que el calendario debería empezar mostrando {dias_anteriores} días del mes anterior")

# Verificar día 4
cuarto_dia = datetime(2025, 12, 4)
print(f"\n4 de diciembre 2025: {cuarto_dia.strftime('%A')}")
print(f"Posición en calendario (después de {dias_anteriores} días anteriores): {dias_anteriores + 4}")
print(f"Columna (0-6): {(dias_anteriores + 4 - 1) % 7}")
columnas = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
print(f"Debería aparecer en: {columnas[(dias_anteriores + 3) % 7]}")
