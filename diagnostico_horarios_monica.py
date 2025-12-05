"""
Script para diagnosticar qué horarios se crearon para Monica Oyarce Poblete
"""
from src.utils.supabase import supabase_client

# Buscar el doctor por nombre
doctors = supabase_client.from_('usuario_sistema').select('id, nombre, apellido_paterno, apellido_materno').ilike('nombre', '%Monica%').execute()

if doctors.data:
    for doc in doctors.data:
        print(f"Doctor encontrado: {doc['nombre']} {doc['apellido_paterno']} {doc['apellido_materno']} (ID: {doc['id']})")
        
        # Ver sus horarios
        horarios = supabase_client.from_('horarios_personal').select('*').eq('usuario_sistema_id', doc['id']).order('inicio_bloque').execute()
        
        print(f"\nTotal horarios: {len(horarios.data)}")
        print("=" * 80)
        
        if horarios.data:
            print("Primeros 5 bloques:")
            for h in horarios.data[:5]:
                print(f"  ID {h['id']}: {h['inicio_bloque']} → {h['finalizacion_bloque']}")
            
            print("\n...")
            print("\nÚltimos 5 bloques:")
            for h in horarios.data[-5:]:
                print(f"  ID {h['id']}: {h['inicio_bloque']} → {h['finalizacion_bloque']}")
            
            # Agrupar por día
            from collections import defaultdict
            por_dia = defaultdict(int)
            for h in horarios.data:
                dia = h['inicio_bloque'][:10]  # YYYY-MM-DD
                por_dia[dia] += 1
            
            print(f"\nBloques por día:")
            for dia, count in sorted(por_dia.items()):
                print(f"  {dia}: {count} bloques")
else:
    print("No se encontró doctora Monica")
