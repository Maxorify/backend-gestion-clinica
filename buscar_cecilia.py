"""
Buscar cita de Cecilia de hoy
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

print("Buscando citas de Cecilia Carcamo...")

# Buscar por nombre
response = supabase.table("cita_medica") \
    .select("*, paciente:paciente_id(nombre, apellido_paterno, rut), doctor:doctor_id(nombre, apellido_paterno)") \
    .gte("fecha_atencion", "2025-12-09T00:00:00") \
    .lte("fecha_atencion", "2025-12-10T23:59:59") \
    .execute()

print(f"\nTotal citas encontradas en rango 9-10 dic: {len(response.data)}")

for cita in response.data:
    paciente = cita.get('paciente', {})
    doctor = cita.get('doctor', {})
    nombre_completo = f"{paciente.get('nombre', '')} {paciente.get('apellido_paterno', '')}"
    
    if 'cecilia' in nombre_completo.lower() or 'carcamo' in nombre_completo.lower():
        print(f"\n✅ ENCONTRADA:")
        print(f"   Paciente: {nombre_completo}")
        print(f"   RUT: {paciente.get('rut', 'N/A')}")
        print(f"   Doctor: {doctor.get('nombre')} {doctor.get('apellido_paterno')}")
        print(f"   Fecha UTC: {cita.get('fecha_atencion')}")
        print(f"   Estado: {cita.get('estado_actual')}")
        print(f"   Doctor ID: {cita.get('doctor_id')}")
        
        # Convertir a Chile
        dt_utc = datetime.fromisoformat(cita.get('fecha_atencion').replace('Z', '+00:00').replace('+00:00', ''))
        dt_chile = dt_utc - timedelta(hours=3)
        print(f"   Hora Chile: {dt_chile.strftime('%Y-%m-%d %H:%M')}")

# Mostrar todas las citas para debug
print(f"\n\nTodas las citas del rango:")
for cita in response.data[:5]:
    paciente = cita.get('paciente', {})
    print(f"  - {paciente.get('nombre')} {paciente.get('apellido_paterno')}: {cita.get('fecha_atencion')} ({cita.get('estado_actual')})")
