"""
Script de diagnóstico para analizar formatos de timestamp en Supabase
"""
from src.utils.supabase import supabase_client

print("=" * 80)
print("DIAGNÓSTICO COMPLETO DE TIMESTAMPS EN SUPABASE")
print("=" * 80)

# 1. TABLA: horarios_personal
print("\n1️⃣  TABLA: horarios_personal")
print("-" * 80)
horarios = supabase_client.from_('horarios_personal').select('*').limit(5).execute()
if horarios.data:
    print(f"   Total registros: {len(horarios.data)}")
    print(f"   Columnas: {list(horarios.data[0].keys())}")
    print("\n   MUESTRA DE DATOS:")
    for h in horarios.data[:3]:
        print(f"   • ID {h['id']}:")
        print(f"     inicio_bloque: {h['inicio_bloque']} (tipo: {type(h['inicio_bloque']).__name__})")
        print(f"     finalizacion_bloque: {h['finalizacion_bloque']} (tipo: {type(h['finalizacion_bloque']).__name__})")
        print(f"     Formato detectado: {'✅ CON TIMEZONE' if '+' in str(h['inicio_bloque']) or 'Z' in str(h['inicio_bloque']) else '❌ SIN TIMEZONE'}")
else:
    print("   ⚠️  Tabla vacía")

# 2. TABLA: asistencia
print("\n2️⃣  TABLA: asistencia")
print("-" * 80)
asistencia = supabase_client.from_('asistencia').select('*').limit(5).execute()
if asistencia.data:
    print(f"   Total registros: {len(asistencia.data)}")
    print(f"   Columnas: {list(asistencia.data[0].keys())}")
    print("\n   MUESTRA DE DATOS:")
    for a in asistencia.data[:3]:
        print(f"   • ID {a['id']}:")
        print(f"     inicio_turno: {a.get('inicio_turno')} (tipo: {type(a.get('inicio_turno')).__name__})")
        print(f"     finalizacion_turno: {a.get('finalizacion_turno')} (tipo: {type(a.get('finalizacion_turno')).__name__})")
        if a.get('inicio_turno'):
            print(f"     Formato detectado: {'✅ CON TIMEZONE' if '+' in str(a['inicio_turno']) or 'Z' in str(a['inicio_turno']) else '❌ SIN TIMEZONE'}")
else:
    print("   ⚠️  Tabla vacía")

# 3. TABLA: cita_medica
print("\n3️⃣  TABLA: cita_medica")
print("-" * 80)
citas = supabase_client.from_('cita_medica').select('*').limit(5).execute()
if citas.data:
    print(f"   Total registros: {len(citas.data)}")
    print(f"   Columnas: {list(citas.data[0].keys())}")
    print("\n   MUESTRA DE DATOS:")
    for c in citas.data[:3]:
        print(f"   • ID {c['id']}:")
        print(f"     fecha_atencion: {c.get('fecha_atencion')} (tipo: {type(c.get('fecha_atencion')).__name__})")
        if c.get('fecha_atencion'):
            print(f"     Formato detectado: {'✅ CON TIMEZONE' if '+' in str(c['fecha_atencion']) or 'Z' in str(c['fecha_atencion']) else '❌ SIN TIMEZONE'}")
else:
    print("   ⚠️  Tabla vacía")

# 4. CONSULTA A SUPABASE: Verificar tipo de columna en PostgreSQL
print("\n4️⃣  TIPOS DE COLUMNA EN POSTGRESQL (desde información del esquema)")
print("-" * 80)
print("   Según query postgres.txt:")
print("   • horarios_personal.inicio_bloque: timestamp with time zone")
print("   • horarios_personal.finalizacion_bloque: timestamp with time zone")
print("   • asistencia.inicio_turno: timestamp with time zone")
print("   • asistencia.finalizacion_turno: timestamp with time zone")
print("   • cita_medica.fecha_atencion: timestamp with time zone")

print("\n" + "=" * 80)
print("CONCLUSIÓN:")
print("=" * 80)
print("Si los datos muestran ❌ SIN TIMEZONE pero la BD es 'timestamptz',")
print("significa que los datos se insertaron sin timezone y PostgreSQL los")
print("almacenó asumiendo la zona horaria del servidor.")
print("\n🎯 NECESITAREMOS:")
print("   1. Migrar datos existentes agregando timezone explícito")
print("   2. Asegurar que Python siempre envíe datetime con timezone.utc")
print("=" * 80)
