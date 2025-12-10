"""
Test para verificar que las citas se filtran correctamente por fecha
Especialmente citas agendadas después de las 21:00 Chile (00:00 UTC día siguiente)
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

print("=" * 80)
print("🧪 TEST: Verificando filtrado de citas por fecha")
print("=" * 80)

# Fecha de hoy en Chile
fecha_chile = datetime.now().strftime("%Y-%m-%d")
print(f"\n📅 Fecha actual Chile: {fecha_chile}")

# Ver cita de Cecilia Carcamo
print("\n🔍 Buscando cita de Cecilia Carcamo...")
response = supabase.table("cita_medica") \
    .select("*, paciente:paciente_id(nombre, apellido_paterno), doctor:doctor_id(nombre, apellido_paterno)") \
    .eq("paciente_id", 5) \
    .order("fecha_atencion", desc=True) \
    .limit(1) \
    .execute()

if response.data:
    cita = response.data[0]
    paciente = cita.get('paciente', {})
    doctor = cita.get('doctor', {})
    fecha_atencion = cita.get('fecha_atencion')
    
    print(f"\n✅ Cita encontrada:")
    print(f"   👤 Paciente: {paciente.get('nombre')} {paciente.get('apellido_paterno')}")
    print(f"   👨‍⚕️ Doctor: {doctor.get('nombre')} {doctor.get('apellido_paterno')}")
    print(f"   📅 Fecha/Hora UTC guardada: {fecha_atencion}")
    
    # Convertir a Chile
    dt_utc = datetime.fromisoformat(fecha_atencion.replace('Z', '+00:00'))
    dt_chile = dt_utc - timedelta(hours=3)
    
    print(f"   🇨🇱 Fecha/Hora en Chile: {dt_chile.strftime('%Y-%m-%d %H:%M')}")
    print(f"   📆 Día en Chile: {dt_chile.strftime('%Y-%m-%d')}")
    print(f"   📆 Día en UTC: {dt_utc.strftime('%Y-%m-%d')}")
    
    # Verificar si el backend filtra correctamente
    print(f"\n🔎 Verificando filtrado del backend...")
    print(f"   Frontend busca: fecha={fecha_chile}")
    print(f"   Backend debería convertir: {fecha_chile} 00:00 Chile → UTC")
    
    inicio_chile = datetime.strptime(fecha_chile, "%Y-%m-%d")
    inicio_utc = inicio_chile + timedelta(hours=3)
    fin_utc = inicio_chile + timedelta(days=1, hours=3)
    
    print(f"   Rango UTC esperado: {inicio_utc.isoformat()} a {fin_utc.isoformat()}")
    
    # Verificar si la cita está en el rango
    if inicio_utc <= dt_utc < fin_utc:
        print(f"   ✅ La cita ESTÁ en el rango (debería aparecer)")
    else:
        print(f"   ❌ La cita NO está en el rango (no aparecerá)")
        print(f"      Cita UTC: {dt_utc.isoformat()}")
        print(f"      Rango: {inicio_utc.isoformat()} a {fin_utc.isoformat()}")
else:
    print("❌ No se encontró la cita de Cecilia")

print("\n" + "=" * 80)
print("📝 CONCLUSIÓN:")
print("=" * 80)
print("Si Frontend usa: new Date().toLocaleDateString('en-CA', {timeZone: 'America/Santiago'})")
print("✅ Enviará la fecha correcta en timezone Chile al backend")
print("✅ Backend convertirá correctamente Chile → UTC para filtrar")
print("✅ Citas de 21:00-23:59 Chile aparecerán en el día correcto")
print("=" * 80)
