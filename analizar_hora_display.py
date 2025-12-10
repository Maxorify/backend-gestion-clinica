"""
Análisis: ¿Por qué la cita de 21:00 se muestra como 12:00?
"""
from datetime import datetime, timedelta

print("=" * 80)
print("ANÁLISIS: Hora mostrada incorrectamente (21:00 → 12:00)")
print("=" * 80)

# La cita en la base de datos
fecha_bd = "2025-12-10T00:00:00.000Z"
print(f"\n📊 Fecha guardada en BD (UTC): {fecha_bd}")

# Parseamos como lo hace parseUTCDate()
print("\n1️⃣  PARSEADO CON parseUTCDate() (CitasDoctor.jsx):")
print("="*80)

utc_date = datetime.fromisoformat(fecha_bd.replace('Z', ''))
print(f"   Fecha UTC parseada: {utc_date}")
print(f"   Componentes UTC:")
print(f"      Año: {utc_date.year}")
print(f"      Mes: {utc_date.month}")
print(f"      Día: {utc_date.day}")
print(f"      Hora UTC: {utc_date.hour}")
print(f"      Minuto UTC: {utc_date.minute}")

# parseUTCDate crea una fecha LOCAL con componentes UTC
fecha_parseada = datetime(
    utc_date.year,
    utc_date.month,
    utc_date.day,
    utc_date.hour,
    utc_date.minute,
    utc_date.second
)

print(f"\n   ✅ Fecha creada (local con valores UTC): {fecha_parseada}")
print(f"   Hora extraída: {fecha_parseada.hour}:{fecha_parseada.minute:02d}")

# Ahora aplicamos toLocaleTimeString()
print(f"\n2️⃣  FORMATEO CON toLocaleTimeString('es-CL'):")
print("="*80)
print(f"   JavaScript recibe: Date objeto con valores 2025-12-10 00:00 (local)")
print(f"   toLocaleTimeString() formatea: {fecha_parseada.hour:02d}:{fecha_parseada.minute:02d}")
print(f"   Resultado en pantalla: 00:00")

# ¿Qué esperábamos?
print(f"\n3️⃣  ¿QUÉ ESPERÁBAMOS VER?")
print("="*80)
print(f"   Hora deseada: 21:00 (hora Chile cuando se agendó)")
print(f"   Hora en BD UTC: 2025-12-10 00:00 (equivalente a 21:00 Chile del día anterior)")
print(f"   Hora que se muestra: 00:00 ❌")

print(f"\n4️⃣  DIAGNÓSTICO DEL PROBLEMA:")
print("="*80)
print("""
   ❌ PROBLEMA IDENTIFICADO:
   
   parseUTCDate() extrae los componentes UTC LITERALES (00:00) y los muestra tal cual.
   NO está convirtiendo de UTC a hora Chile.
   
   FLUJO ACTUAL:
   1. BD almacena: 2025-12-10T00:00:00Z (UTC)
   2. parseUTCDate() extrae: 00:00 (valores UTC literales)
   3. toLocaleTimeString() muestra: 00:00 ❌
   
   FLUJO CORRECTO DEBERÍA SER:
   1. BD almacena: 2025-12-10T00:00:00Z (UTC) 
   2. Convertir a Chile: 2025-12-09 21:00 (UTC-3)
   3. toLocaleTimeString() muestra: 21:00 ✅
""")

print(f"\n5️⃣  COMPARACIÓN: ¿Cómo lo hace asistencia.jsx?")
print("="*80)

print("""
   🔍 ASISTENCIA.JSX (QUE FUNCIONA):
   
   Usa parseUTCDate() SOLO para comparaciones de FECHA (día/mes/año),
   NO para mostrar HORAS.
   
   Para mostrar horas, usa formatTime() que hace:
   
   const formatTime = (dateTimeString) => {
       if (!dateTimeString) return "N/A";
       const date = parseUTCDate(dateTimeString);
       if (!date) return "N/A";
       
       // Aquí solo extrae hora/minuto del objeto Date local
       return date.toLocaleTimeString("es-CL", {
           hour: "2-digit",
           minute: "2-digit",
       });
   }
   
   PERO esto también mostraría 00:00 porque parseUTCDate extrae literales UTC.
   
   🤔 MOMENTO... déjame revisar el código real de asistencia.jsx
""")

# Simulación de conversión correcta
print(f"\n6️⃣  SOLUCIÓN CORRECTA:")
print("="*80)

utc_datetime = datetime.fromisoformat(fecha_bd.replace('Z', ''))
print(f"   1. Fecha UTC: {utc_datetime}")

# Convertir a Chile (UTC-3)
chile_datetime = utc_datetime - timedelta(hours=3)
print(f"   2. Convertir a Chile (UTC-3): {chile_datetime}")
print(f"   3. Mostrar hora: {chile_datetime.hour:02d}:{chile_datetime.minute:02d}")
print(f"   4. Resultado esperado: 21:00 ✅")

print(f"\n" + "="*80)
print("CONCLUSIÓN")
print("="*80)
print("""
El problema NO está en el filtrado del endpoint (ese ya funciona ✅).

El problema está en CÓMO SE MUESTRA LA HORA en el frontend:

parseUTCDate() extrae componentes UTC LITERALES sin convertir a hora local de Chile.

SOLUCIONES POSIBLES:

A) MODIFICAR parseUTCDate() para que convierta UTC → Chile:
   - Restar 3 horas al crear el Date
   - return new Date(year, month, day, hours-3, minutes)

B) CREAR formatChileTime() que convierta antes de formatear:
   - Usar Date con timezone 'America/Santiago'
   - O restar 3 horas manualmente

C) DEJAR que JavaScript haga la conversión automática:
   - NO usar parseUTCDate para HORAS
   - Usar directamente new Date(dateString).toLocaleTimeString()
   - Esto convierte automáticamente UTC → timezone local

La opción C es la MÁS SIMPLE y CORRECTA para mostrar horas.
parseUTCDate() solo debe usarse para COMPARAR FECHAS (día/mes/año).
""")

print("\n" + "="*80)
