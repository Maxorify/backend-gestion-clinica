from src.utils.supabase import supabase_client

tables = ['marcas_asistencia', 'asistencia_estados', 'parametros_asistencia']

for t in tables:
    try:
        result = supabase_client.from_(t).select('*').limit(1).execute()
        print(f'✅ {t}: EXISTE')
    except Exception as e:
        print(f'❌ {t}: NO EXISTE - {str(e)[:50]}')