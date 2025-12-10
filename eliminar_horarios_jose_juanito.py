from supabase import create_client

# Conectar a Supabase
SUPABASE_URL = 'https://pjuaufpyctvxvcqomknq.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBqdWF1ZnB5Y3R2eHZjcW9ta25xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzA3NjE4OTYsImV4cCI6MjA0NjMzNzg5Nn0.RnVPtcKLNXkam3T5NOz8lmjyPTnyOOKbKx_vR8cO8dM'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print('🔍 Buscando Jose Perez y Juanito Perez...')

# Buscar usuarios
usuarios = supabase.table('usuario_sistema').select('id, nombre, apellido').or_('nombre.ilike.%jose%,nombre.ilike.%juanito%').execute()

if not usuarios.data:
    print('❌ No se encontraron usuarios')
    exit(0)

print(f'✅ Encontrados {len(usuarios.data)} usuarios:')
for user in usuarios.data:
    print(f'  - ID {user["id"]}: {user["nombre"]} {user["apellido"]}')

# Eliminar horarios
total_eliminados = 0
for user in usuarios.data:
    user_id = user['id']
    user_name = f'{user["nombre"]} {user["apellido"]}'
    
    # Contar horarios
    horarios = supabase.table('horario').select('id', count='exact').eq('doctor_id', user_id).execute()
    count = horarios.count if horarios.count else 0
    
    print(f'\n📋 {user_name} (ID {user_id}): {count} horarios')
    
    if count > 0:
        print(f'🗑️  Eliminando {count} horarios...')
        delete_result = supabase.table('horario').delete().eq('doctor_id', user_id).execute()
        print(f'✅ Eliminados exitosamente')
        total_eliminados += count

print(f'\n✅ Proceso completado: {total_eliminados} horarios eliminados en total')
