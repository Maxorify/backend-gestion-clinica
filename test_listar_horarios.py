import urllib.request
import json
from datetime import datetime, timedelta
from collections import defaultdict

# Simular la consulta del frontend
API_URL = "http://localhost:5000"

# Parámetros que envía el frontend para el jueves 4
params = {
    "usuario_sistema_id": "25",
    "fecha_inicio": "2025-12-02T03:00:00.000Z",  # Inicio semana
    "fecha_fin": "2025-12-09T02:59:59.999Z"      # Fin semana
}

url = f"{API_URL}/Horarios/listar-horarios?usuario_sistema_id={params['usuario_sistema_id']}&fecha_inicio={params['fecha_inicio']}&fecha_fin={params['fecha_fin']}"

print("🔍 CONSULTANDO HORARIOS:")
print(f"URL: {url}")

try:
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        horarios = data.get("horarios", [])
        
        print(f"\n✅ Total horarios devueltos: {len(horarios)}")
        
        # Agrupar por día UTC
        por_dia_utc = defaultdict(int)
        por_dia_chile = defaultdict(int)
        
        for h in horarios:
            # Día en UTC
            fecha_utc = h["inicio_bloque"].split("T")[0]
            por_dia_utc[fecha_utc] += 1
            
            # Día en Chile (restar 3 horas aproximadamente)
            dt_utc = datetime.fromisoformat(h["inicio_bloque"].replace("Z", "+00:00"))
            dt_chile = dt_utc.replace(tzinfo=None) - timedelta(hours=3)
            fecha_chile = dt_chile.date()
            por_dia_chile[str(fecha_chile)] += 1
        
        print("\n📅 Bloques por día (UTC):")
        for dia, count in sorted(por_dia_utc.items()):
            print(f"  {dia}: {count} bloques")
        
        print("\n📅 Bloques por día (Chile estimado):")
        for dia, count in sorted(por_dia_chile.items()):
            print(f"  {dia}: {count} bloques")
            
        # Mostrar primeros 3 y últimos 3
        print("\n🔹 Primeros 3 bloques:")
        for h in horarios[:3]:
            print(f"  {h['inicio_bloque']} → {h['finalizacion_bloque']}")
        
        print("\n🔹 Últimos 3 bloques:")
        for h in horarios[-3:]:
            print(f"  {h['inicio_bloque']} → {h['finalizacion_bloque']}")
            
except Exception as e:
    print(f"❌ Error: {e}")
