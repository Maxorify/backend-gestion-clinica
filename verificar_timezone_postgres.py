from src.utils.supabase import supabase_client

# Ejecutar query para ver timezone de PostgreSQL
result = supabase_client.rpc('show_timezone').execute()
print("🔍 Timezone de PostgreSQL:")
print(result)

# Alternativa: crear una función temporal
try:
    test_query = supabase_client.rpc('exec_sql', {'sql': 'SHOW TIMEZONE'}).execute()
    print("Timezone:", test_query)
except Exception as e:
    print(f"Error al obtener timezone: {e}")

# Probar inserción y ver qué se guarda
from datetime import datetime

print("\n🧪 TEST: Insertar datetime naive y ver qué guarda PostgreSQL")
print(f"Datetime enviado: 2025-12-04 08:00:00 (naive, sin timezone)")
