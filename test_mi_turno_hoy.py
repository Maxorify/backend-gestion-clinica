import urllib.request
import json
from datetime import datetime

# Consultar el endpoint de turno actual para Monica (ID: 25)
url = "http://localhost:5000/asistencia/doctor/mi-turno-hoy?usuario_id=25"

print("🔍 CONSULTANDO ENDPOINT mi-turno-hoy:")
print(f"URL: {url}\n")

try:
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        
        print("📋 RESPUESTA COMPLETA:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if 'horarios' in data:
            horarios = data['horarios']
            print(f"\n✅ Total horarios encontrados: {len(horarios)}")
            
            if horarios:
                print("\n🕐 Primer horario:")
                print(f"  inicio_bloque: {horarios[0]['inicio_bloque']}")
                print(f"  finalizacion_bloque: {horarios[0]['finalizacion_bloque']}")
                
                print("\n🕐 Último horario:")
                print(f"  inicio_bloque: {horarios[-1]['inicio_bloque']}")
                print(f"  finalizacion_bloque: {horarios[-1]['finalizacion_bloque']}")
                
                # Convertir a hora Chile
                from datetime import timedelta
                
                primer_inicio_utc = datetime.fromisoformat(horarios[0]['inicio_bloque'].replace('Z', '+00:00'))
                ultimo_fin_utc = datetime.fromisoformat(horarios[-1]['finalizacion_bloque'].replace('Z', '+00:00'))
                
                # Restar 3 horas para Chile
                primer_inicio_chile = primer_inicio_utc - timedelta(hours=3)
                ultimo_fin_chile = ultimo_fin_utc - timedelta(hours=3)
                
                print(f"\n🇨🇱 En hora Chile:")
                print(f"  Primer bloque inicia: {primer_inicio_chile.strftime('%H:%M')}")
                print(f"  Último bloque termina: {ultimo_fin_chile.strftime('%H:%M')}")
        
except Exception as e:
    print(f"❌ Error: {e}")
