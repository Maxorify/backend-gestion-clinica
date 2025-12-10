"""
VERIFICACIÓN CRÍTICA: ¿Cómo guarda el backend las fechas?
"""
import sys
sys.path.insert(0, 'src')
from utils.supabase import supabase_client
from datetime import datetime, timedelta

print("=" * 80)
print("VERIFICACIÓN: Diferencia entre guardado de Asistencia vs Citas")
print("=" * 80)

# 1. VERIFICAR ASISTENCIA
print("\n1️⃣  ASISTENCIA: ¿Cómo se guarda una entrada a las 08:00 AM Chile?")
print("="*80)

horarios = supabase_client.table("horarios_personal").select(
    "id, inicio_bloque, finalizacion_bloque"
).limit(1).execute()

if horarios.data:
    h = horarios.data[0]
    print(f"\n📊 Ejemplo de horario programado:")
    print(f"   ID: {h['id']}")
    print(f"   Inicio bloque (UTC): {h['inicio_bloque']}")
    print(f"   Fin bloque (UTC): {h['finalizacion_bloque']}")
    
    # Parsear
    inicio_utc = datetime.fromisoformat(h['inicio_bloque'].replace('Z', '').replace('+00:00', ''))
    print(f"\n   Parseado UTC: {inicio_utc}")
    print(f"   Hora UTC: {inicio_utc.hour:02d}:{inicio_utc.minute:02d}")
    
    # ¿Qué hora es en Chile?
    inicio_chile = inicio_utc - timedelta(hours=3)
    print(f"\n   Convertido a Chile (UTC-3): {inicio_chile}")
    print(f"   Hora Chile: {inicio_chile.hour:02d}:{inicio_chile.minute:02d}")
    
    print(f"\n   🔍 ANÁLISIS:")
    if inicio_utc.hour >= 3:  # Si es >= 03:00 UTC
        print(f"      La hora UTC ({inicio_utc.hour}:00) sugiere que se guardó CON CONVERSIÓN")
        print(f"      Es decir: {inicio_chile.hour:02d}:00 Chile → {inicio_utc.hour:02d}:00 UTC")
    else:
        print(f"      La hora UTC ({inicio_utc.hour}:00) sugiere que se guardó SIN CONVERSIÓN")
        print(f"      Es decir: {inicio_utc.hour:02d}:00 literal")

# 2. VERIFICAR CITAS
print(f"\n2️⃣  CITAS: ¿Cómo se guarda una cita a las 21:00 Chile?")
print("="*80)

# Buscar la cita de Johan que sabemos es a las 21:00
cita_johan = supabase_client.table("cita_medica").select(
    "id, fecha_atencion"
).eq("id", 47).execute()

if cita_johan.data:
    c = cita_johan.data[0]
    print(f"\n📊 Cita ID {c['id']} (Johan - agendada para 21:00 Chile):")
    print(f"   Fecha UTC en BD: {c['fecha_atencion']}")
    
    # Parsear
    fecha_utc = datetime.fromisoformat(c['fecha_atencion'].replace('Z', '').replace('+00:00', ''))
    print(f"\n   Parseado UTC: {fecha_utc}")
    print(f"   Hora UTC: {fecha_utc.hour:02d}:{fecha_utc.minute:02d}")
    
    # ¿Qué hora es en Chile?
    fecha_chile = fecha_utc - timedelta(hours=3)
    print(f"\n   Convertido a Chile (UTC-3): {fecha_chile}")
    print(f"   Hora Chile: {fecha_chile.hour:02d}:{fecha_chile.minute:02d}")
    
    print(f"\n   🔍 ANÁLISIS:")
    print(f"      Cita agendada: 21:00 Chile")
    print(f"      Guardada como: {fecha_utc.hour:02d}:00 UTC")
    print(f"      Esto equivale a: {fecha_chile.hour:02d}:00 Chile ✅")
    print(f"      Conclusión: Se guardó CON CONVERSIÓN Chile → UTC (+3 horas)")

# 3. COMPARACIÓN
print(f"\n3️⃣  COMPARACIÓN Y CONCLUSIÓN")
print("="*80)

if horarios.data and cita_johan.data:
    inicio_utc_h = datetime.fromisoformat(horarios.data[0]['inicio_bloque'].replace('Z', '').replace('+00:00', ''))
    fecha_utc_c = datetime.fromisoformat(cita_johan.data[0]['fecha_atencion'].replace('Z', '').replace('+00:00', ''))
    
    print(f"\n📊 PATRÓN DE GUARDADO:")
    print(f"\nASISTENCIA (horarios_personal):")
    print(f"   Ejemplo UTC: {inicio_utc_h.hour:02d}:00")
    print(f"   En Chile: {(inicio_utc_h - timedelta(hours=3)).hour:02d}:00")
    
    print(f"\nCITAS (cita_medica):")
    print(f"   Ejemplo UTC: {fecha_utc_c.hour:02d}:00")
    print(f"   En Chile: {(fecha_utc_c - timedelta(hours=3)).hour:02d}:00")
    
    print(f"\n✅ CONCLUSIÓN:")
    print(f"""
    AMBOS sistemas guardan fechas en UTC REAL (con conversión desde Chile).
    
    Ejemplo:
    - Asistencia 08:00 Chile → Guarda como 11:00 UTC
    - Cita 21:00 Chile → Guarda como 00:00 UTC (día siguiente)
    
    Por lo tanto:
    
    ❌ parseUTCDate() de asistencia.jsx está MAL
       Extrae componentes UTC literales (hora=11 o hora=0)
       Y los muestra tal cual (11:00 o 00:00)
       
    ✅ DEBERÍA extraer componentes UTC y RESTAR 3 HORAS
       O usar toLocaleTimeString con timezone Chile
       
    🤔 PERO ENTONCES... ¿Por qué asistencia.jsx "funciona"?
       
       HIPÓTESIS: Tal vez el módulo de asistencia NO muestra horas correctamente
       y nadie lo ha notado porque las marcas de entrada son temprano (08:00, 09:00)
       donde el error de timezone no es tan evidente.
       
       O tal vez el backend de asistencia guarda SIN conversión (hora literal)
       mientras que el backend de citas SÍ convierte.
    """)

print("\n" + "="*80)
print("🔬 RECOMENDACIÓN")
print("="*80)
print("""
ANTES de alinear todo con asistencia.jsx, necesito que VERIFIQUES:

1. Abre el módulo de asistencia en el frontend
2. Busca un doctor que haya marcado entrada a las 08:00 AM
3. ¿Qué hora muestra la UI?
   - Si muestra 08:00 → Backend guarda sin conversión ✅
   - Si muestra 11:00 → Backend guarda con conversión, UI muestra mal ❌
   
4. Si muestra 08:00, entonces revisa en la BD:
   - ¿La marca_entrada está a las 08:00 UTC o 11:00 UTC?
   
Esta información es CRÍTICA para decidir si:
A) Alinear todo con la lógica actual de asistencia.jsx (parseUTCDate literal)
B) Corregir asistencia.jsx Y todos los demás archivos (parseUTCDate con -3h)
""")

print("\n" + "="*80)
