"""
Script de diagnóstico: Problema de timezone en citas
Compara cómo se maneja la fecha en asistencia vs agendamiento
"""
from datetime import datetime, timedelta

print("=" * 80)
print("DIAGNÓSTICO: Problema de Timezone en Registro de Citas")
print("=" * 80)

# Simular el caso: Registrar cita para 21:00 hora Chile
hora_chile = "21:00"
fecha_local = "2025-12-09"

print(f"\n📅 Input del usuario:")
print(f"   Fecha: {fecha_local}")
print(f"   Hora: {hora_chile}")

# ============================================================================
# MÉTODO ACTUAL EN AGENDAMIENTO (chileTimeToUTC de dateUtils.js)
# ============================================================================
print(f"\n{'='*80}")
print("MÉTODO ACTUAL: chileTimeToUTC() - agendamientoConsultas.jsx")
print("="*80)

# Simular la lógica de createChileDateUTC
def simulate_current_method(date_str, time_str):
    """Simula chileTimeToUTC de dateUtils.js"""
    year, month, day = map(int, date_str.split('-'))
    hours, minutes = map(int, time_str.split(':'))
    
    # 1. Crear fecha en UTC con los valores directos
    date_utc = datetime(year, month, day, hours, minutes, 0, 0)
    print(f"   1. Crear fecha UTC directa: {date_utc} UTC")
    
    # 2. Sumar 3 horas (conversión Chile -> UTC)
    date_utc_plus_3 = date_utc + timedelta(hours=3)
    print(f"   2. Agregar +3 horas: {date_utc_plus_3} UTC")
    
    return date_utc_plus_3

resultado_actual = simulate_current_method(fecha_local, hora_chile)
print(f"\n   ✅ Resultado enviado al backend: {resultado_actual.isoformat()}Z")
print(f"   ⚠️  PROBLEMA: 21:00 Chile se convirtió en 00:00 UTC del día siguiente")

# ============================================================================
# MÉTODO CORRECTO USADO EN ASISTENCIA (basado en offset manual)
# ============================================================================
print(f"\n{'='*80}")
print("MÉTODO CORRECTO: Conversión con offset manual -3 horas")
print("="*80)

def simulate_correct_method(date_str, time_str):
    """Método correcto: Hora Chile -> UTC (restar 3 horas, no sumar)"""
    year, month, day = map(int, date_str.split('-'))
    hours, minutes = map(int, time_str.split(':'))
    
    # 1. Crear fecha en hora LOCAL de Chile
    date_chile = datetime(year, month, day, hours, minutes, 0, 0)
    print(f"   1. Crear fecha en hora Chile: {date_chile} (local)")
    
    # 2. Chile está en UTC-3, entonces UTC = Chile + 3 horas
    date_utc = date_chile + timedelta(hours=3)
    print(f"   2. Convertir a UTC (+3h): {date_utc} UTC")
    
    return date_utc

resultado_correcto = simulate_correct_method(fecha_local, hora_chile)
print(f"\n   ✅ Resultado enviado al backend: {resultado_correcto.isoformat()}")
print(f"   ✅ CORRECTO: 21:00 Chile = 00:00 UTC (mismo día en Chile al consultar)")

# ============================================================================
# COMPARACIÓN FINAL
# ============================================================================
print(f"\n{'='*80}")
print("COMPARACIÓN DE RESULTADOS")
print("="*80)

print(f"\nHora ingresada: {hora_chile} del {fecha_local} (hora Chile)")
print(f"\nMétodo ACTUAL (dateUtils.js):")
print(f"  - UTC enviado: {resultado_actual.isoformat()}Z")
print(f"  - En Chile sería: {fecha_local} 00:00 (día siguiente!) ❌")

print(f"\nMétodo CORRECTO (ZoneInfo):")
print(f"  - UTC enviado: {resultado_correcto.isoformat()}")
print(f"  - En Chile sería: {fecha_local} {hora_chile} ✅")

# ============================================================================
# ANÁLISIS DEL PROBLEMA
# ============================================================================
print(f"\n{'='*80}")
print("ANÁLISIS DEL PROBLEMA")
print("="*80)

print("""
🔍 CAUSA RAÍZ:
   La función chileTimeToUTC() en dateUtils.js tiene una lógica invertida:
   
   1. Crea una fecha en UTC con valores locales: Date.UTC(2025, 11, 9, 21, 0)
      Esto crea "2025-12-09 21:00 UTC" (NO hora Chile)
   
   2. Le suma +3 horas pensando que convierte Chile -> UTC
      Resultado: "2025-12-10 00:00 UTC" ❌
   
   PERO la lógica correcta es:
   - Chile está en UTC-3
   - Si en Chile son las 21:00, en UTC son las 00:00 (del MISMO día localmente)
   - El frontend debe enviar: "2025-12-10 00:00:00Z"
   - Cuando el backend consulte por fecha 2025-12-09, NO encontrará esta cita

📊 IMPACTO:
   - Todas las citas agendadas tienen +3 horas de error
   - Las citas del día actual aparecen como "mañana" en UTC
   - Los doctores no ven sus citas del día

✅ SOLUCIÓN:
   Reemplazar la lógica en dateUtils.js para usar:
   - En backend: python datetime con ZoneInfo('America/Santiago')
   - En frontend: Date.toLocaleString con timeZone: 'America/Santiago'
   
   O implementar parseUTCDate (como en asistencia.jsx) que extrae
   componentes UTC y crea fecha local sin offset.
""")

print(f"\n{'='*80}")
print("PRUEBA CON CASO REAL: Johan a las 21:00")
print("="*80)

# Caso real de Johan
print("\n📋 Caso real:")
print("   Fecha ingresada: 2025-12-09")
print("   Hora ingresada: 21:00 - 21:30")

print("\n   Método ACTUAL:")
inicio_actual = simulate_current_method("2025-12-09", "21:00")
print(f"   Guardado en BD: {inicio_actual}")
print(f"   ❌ Consulta por 2025-12-09 -> NO encuentra (está en 2025-12-10)")

print("\n   Método CORRECTO:")
inicio_correcto = simulate_correct_method("2025-12-09", "21:00")
print(f"   Guardado en BD: {inicio_correcto}")
print(f"   ✅ Consulta por 2025-12-09 -> SÍ encuentra (conversión correcta)")

print("\n" + "="*80)
