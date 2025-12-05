"""
Eliminar TODOS los horarios de Monica Oyarce Poblete
"""
from src.utils.supabase import supabase_client

# ID de Monica
monica_id = 25

# Eliminar todos sus horarios
result = supabase_client.from_('horarios_personal').delete().eq('usuario_sistema_id', monica_id).execute()

print(f"✅ Eliminados {len(result.data) if result.data else 0} horarios de Monica (ID: {monica_id})")

# Verificar
verificar = supabase_client.from_('horarios_personal').select('id').eq('usuario_sistema_id', monica_id).execute()
print(f"Horarios restantes: {len(verificar.data)}")
