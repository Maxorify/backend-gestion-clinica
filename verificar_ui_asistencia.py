"""
Verificar qué hora muestra asistencia.jsx para los horarios configurados
"""
import sys
sys.path.insert(0, 'src')
from utils.supabase import supabase_client
from datetime import datetime, timedelta

print("=" * 80)
print("VERIFICACIÓN: ¿Qué hora muestra asistencia.jsx?")
print("=" * 80)

# Obtener los horarios que configuramos para el demo
print("\n📋 Horarios configurados para hoy (2025-12-09):")
print("="*80)

# Buscar horarios del 9 de diciembre
horarios = supabase_client.table("horarios_personal").select(
    "id, inicio_bloque, finalizacion_bloque, usuario_sistema_id, usuario:usuario_sistema_id(nombre, apellido_paterno)"
).gte("inicio_bloque", "2025-12-09T00:00:00").lte("inicio_bloque", "2025-12-09T23:59:59").execute()

print(f"\n🔍 Encontrados {len(horarios.data or [])} horarios para hoy")

if not horarios.data:
    print("\n⚠️  No hay horarios para hoy, buscando cualquier horario reciente...")
    horarios = supabase_client.table("horarios_personal").select(
        "id, inicio_bloque, finalizacion_bloque, usuario_sistema_id, usuario:usuario_sistema_id(nombre, apellido_paterno)"
    ).order("inicio_bloque", desc=True).limit(5).execute()

for h in (horarios.data or []):
    inicio_utc_str = h['inicio_bloque']
    inicio_utc = datetime.fromisoformat(inicio_utc_str.replace('Z', '').replace('+00:00', ''))
    
    # Simular parseUTCDate de asistencia.jsx
    fecha_parseada = datetime(
        inicio_utc.year,
        inicio_utc.month,
        inicio_utc.day,
        inicio_utc.hour,      # ← LITERAL UTC
        inicio_utc.minute,
        inicio_utc.second
    )
    
    # Hora real en Chile
    inicio_chile = inicio_utc - timedelta(hours=3)
    
    usuario = h.get('usuario', {})
    nombre = f"{usuario.get('nombre', 'N/A')} {usuario.get('apellido_paterno', '')}"
    
    print(f"\n👤 {nombre}")
    print(f"   📅 Fecha UTC en BD: {inicio_utc_str}")
    print(f"   🕐 Hora UTC (BD): {inicio_utc.hour:02d}:{inicio_utc.minute:02d}")
    print(f"   🕐 Hora Chile (Real): {inicio_chile.hour:02d}:{inicio_chile.minute:02d}")
    print(f"   🖥️  parseUTCDate extrae: {fecha_parseada.hour:02d}:{fecha_parseada.minute:02d}")
    print(f"   📺 formatTime() mostrará: {fecha_parseada.hour:02d}:{fecha_parseada.minute:02d}")
    
    if fecha_parseada.hour != inicio_chile.hour:
        print(f"   ❌ ERROR: Muestra {fecha_parseada.hour:02d}:00 cuando debería mostrar {inicio_chile.hour:02d}:00")
    else:
        print(f"   ✅ CORRECTO: Muestra la hora Chile correctamente")

# Ahora verificar asistencias reales (marcas de entrada)
print(f"\n\n📋 Asistencias marcadas (entrada real):")
print("="*80)

asistencias = supabase_client.table("asistencia").select(
    "id, fecha_trabajada, horario_inicio, usuario_sistema_id, usuario:usuario_sistema_id(nombre, apellido_paterno)"
).order("fecha_trabajada", desc=True).limit(5).execute()

for a in (asistencias.data or []):
    if a.get('horario_inicio'):
        entrada_utc_str = a['horario_inicio']
        entrada_utc = datetime.fromisoformat(entrada_utc_str.replace('Z', '').replace('+00:00', ''))
        
        # Simular parseUTCDate
        fecha_parseada = datetime(
            entrada_utc.year,
            entrada_utc.month,
            entrada_utc.day,
            entrada_utc.hour,
            entrada_utc.minute,
            entrada_utc.second
        )
        
        # Hora real en Chile
        entrada_chile = entrada_utc - timedelta(hours=3)
        
        usuario = a.get('usuario', {})
        nombre = f"{usuario.get('nombre', 'N/A')} {usuario.get('apellido_paterno', '')}"
        
        print(f"\n👤 {nombre}")
        print(f"   📅 Marca entrada UTC (BD): {entrada_utc_str}")
        print(f"   🕐 Hora UTC (BD): {entrada_utc.hour:02d}:{entrada_utc.minute:02d}")
        print(f"   🕐 Hora Chile (Real): {entrada_chile.hour:02d}:{entrada_chile.minute:02d}")
        print(f"   🖥️  parseUTCDate extrae: {fecha_parseada.hour:02d}:{fecha_parseada.minute:02d}")
        print(f"   📺 formatTime() mostrará: {fecha_parseada.hour:02d}:{fecha_parseada.minute:02d}")
        
        if fecha_parseada.hour != entrada_chile.hour:
            print(f"   ❌ ERROR: UI muestra {fecha_parseada.hour:02d}:00 en vez de {entrada_chile.hour:02d}:00")
        else:
            print(f"   ✅ CORRECTO")

print("\n" + "="*80)
print("CONCLUSIÓN")
print("="*80)
print("""
Si ves ❌ ERROR en los resultados de arriba, significa que:

1. El backend guarda fechas en UTC REAL (con conversión desde Chile)
2. parseUTCDate() extrae componentes UTC LITERALES
3. La UI muestra horas INCORRECTAS (hora UTC en vez de hora Chile)

Por ejemplo:
- Doctor marca entrada a las 08:00 AM Chile
- Backend guarda: 11:00 UTC
- parseUTCDate extrae: 11:00 (literal)
- UI muestra: 11:00 ❌ (debería mostrar 08:00)

Esto confirma que parseUTCDate() está ROTO en asistencia.jsx
y necesita ser CORREGIDO en todos los archivos.

SOLUCIÓN:
parseUTCDate() debe RESTAR 3 horas:
return new Date(year, month, day, hours - 3, minutes, seconds)
""")

print("\n" + "="*80)
