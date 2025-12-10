import requests
import json
from datetime import datetime

# Probar endpoint de citas para Monica (ID 25) en diciembre
doctor_id = 25
base_url = "http://localhost:8000"

print("=" * 80)
print("🔍 PROBANDO ENDPOINT /appointment/doctor/{id}/citas")
print("=" * 80)

# Probar con fecha 2025-12-05 (día con más citas)
fecha = "2025-12-05"
estados = "Completada,En Consulta,Pendiente,Confirmada,Cancelada"

url = f"{base_url}/appointment/doctor/{doctor_id}/citas"
params = {
    "fecha": fecha,
    "estados": estados
}

print(f"\n📡 URL: {url}")
print(f"📋 Parámetros: {params}")

try:
    response = requests.get(url, params=params)
    print(f"\n✅ Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📊 Respuesta:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if "citas" in data:
            print(f"\n✅ Total de citas: {len(data['citas'])}")
            
            for i, cita in enumerate(data['citas'], 1):
                print(f"\n📋 Cita {i}:")
                print(f"   ID: {cita.get('id')}")
                print(f"   Fecha: {cita.get('fecha_atencion')}")
                print(f"   Estado: {cita.get('estado_actual')}")
                print(f"   Especialidad: {cita.get('especialidad')}")
                print(f"   Paciente: {cita.get('paciente')}")
    else:
        print(f"\n❌ Error: {response.text}")
        
except Exception as e:
    print(f"\n❌ Error de conexión: {e}")

print("\n" + "=" * 80)
