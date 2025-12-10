"""
Verificar: ¿Asistencia.jsx muestra las horas correctamente?
"""
import sys
sys.path.insert(0, 'src')
from utils.supabase import supabase_client

print("=" * 80)
print("VERIFICACIÓN: ¿Cómo muestra asistencia.jsx las horas?")
print("=" * 80)

# Obtener una asistencia con hora de entrada
asistencia = supabase_client.table("asistencia").select(
    "id, marca_entrada, usuario_sistema_id"
).not_.is_("marca_entrada", "null").limit(1).execute()

if asistencia.data:
    data = asistencia.data[0]
    print(f"\n📊 Ejemplo de asistencia:")
    print(f"   ID: {data['id']}")
    print(f"   marca_entrada (UTC): {data['marca_entrada']}")
    
    # Simular parseUTCDate de JavaScript
    from datetime import datetime, timedelta
    
    fecha_str = data['marca_entrada']
    utc_date = datetime.fromisoformat(fecha_str.replace('Z', '').replace('+00:00', ''))
    
    # parseUTCDate extrae componentes UTC literales
    fecha_local = datetime(
        utc_date.year,
        utc_date.month, 
        utc_date.day,
        utc_date.hour,
        utc_date.minute,
        utc_date.second
    )
    
    print(f"\n   parseUTCDate() extrae: {fecha_local}")
    print(f"   Hora mostrada en UI: {fecha_local.hour:02d}:{fecha_local.minute:02d}")
    
    # ¿Qué debería mostrar en Chile?
    chile_date = utc_date - timedelta(hours=3)
    print(f"\n   Hora CORRECTA en Chile: {chile_date.hour:02d}:{chile_date.minute:02d}")
    
    if fecha_local.hour != chile_date.hour:
        print(f"\n   ❌ ERROR: Asistencia.jsx TAMBIÉN muestra hora incorrecta!")
        print(f"      Muestra: {fecha_local.hour:02d}:{fecha_local.minute:02d}")
        print(f"      Debería: {chile_date.hour:02d}:{chile_date.minute:02d}")
    else:
        print(f"\n   ✅ Asistencia.jsx muestra hora correcta")

print("\n" + "="*80)
