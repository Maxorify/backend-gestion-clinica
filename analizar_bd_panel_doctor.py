from src.utils.supabase import supabase_client
from datetime import datetime, timedelta

print("=" * 80)
print("ANÁLISIS DE BD PARA PANEL DETALLADO DE DOCTOR")
print("=" * 80)

# 1. Verificar estructura de asistencia
print("\n1. TABLA ASISTENCIA (para timeline y marcas)")
asist = supabase_client.from_('asistencia').select('*').limit(1).execute()
if asist.data:
    print(f"   Columnas disponibles: {list(asist.data[0].keys())}")
    print(f"   ✓ Tiene: inicio_turno, finalizacion_turno, usuario_sistema_id")
else:
    print("   ⚠ Tabla vacía o no existe")

# 2. Verificar si existe tabla de marcas (para timeline detallada)
print("\n2. TABLA MARCAS_ASISTENCIA (para timeline de eventos)")
try:
    marcas = supabase_client.from_('marcas_asistencia').select('*').limit(1).execute()
    if marcas.data:
        print(f"   Columnas: {list(marcas.data[0].keys())}")
        print("   ✓ Existe para registrar eventos detallados")
    else:
        print("   ✓ Existe pero vacía (ready para usar)")
except Exception as e:
    print(f"   ✗ NO EXISTE - {str(e)}")
    print("   → NECESITAREMOS CREARLA para timeline de eventos")

# 3. Verificar tabla de estados/justificaciones
print("\n3. TABLA ASISTENCIA_ESTADOS (para justificaciones)")
try:
    estados = supabase_client.from_('asistencia_estados').select('*').limit(1).execute()
    if estados.data:
        print(f"   Columnas: {list(estados.data[0].keys())}")
        print("   ✓ Existe para justificaciones")
    else:
        print("   ✓ Existe pero vacía")
except Exception as e:
    print(f"   ✗ NO EXISTE - {str(e)}")
    print("   → NECESITAREMOS CREARLA para justificaciones")

# 4. Verificar horarios_personal (para turnos programados)
print("\n4. TABLA HORARIOS_PERSONAL (para turnos programados)")
horarios = supabase_client.from_('horarios_personal').select('*').limit(1).execute()
if horarios.data:
    print(f"   Columnas: {list(horarios.data[0].keys())}")
    print("   ✓ Tiene bloques programados")
else:
    print("   ⚠ Tabla vacía")

# 5. Verificar citas médicas (para pacientes atendidos)
print("\n5. TABLA CITA_MEDICA (para pacientes agendados/atendidos)")
citas = supabase_client.from_('cita_medica').select('*').limit(1).execute()
if citas.data:
    print(f"   Columnas: {list(citas.data[0].keys())}")
    print("   ✓ Tiene citas")
else:
    print("   ⚠ Tabla vacía")

# 6. Verificar tabla estado (para saber qué citas están completadas)
print("\n6. TABLA ESTADO (para citas completadas/canceladas)")
estados_cita = supabase_client.from_('estado').select('*').limit(1).execute()
if estados_cita.data:
    print(f"   Columnas: {list(estados_cita.data[0].keys())}")
    print("   ✓ Tiene estados de citas")
else:
    print("   ⚠ Tabla vacía")

# 7. Verificar usuario_sistema (para datos del doctor)
print("\n7. TABLA USUARIO_SISTEMA (para datos del doctor)")
usuario = supabase_client.from_('usuario_sistema').select('*').limit(1).execute()
if usuario.data:
    print(f"   Columnas: {list(usuario.data[0].keys())}")
    tiene_foto = 'foto' in usuario.data[0] or 'avatar' in usuario.data[0] or 'imagen' in usuario.data[0]
    print(f"   {'✓' if tiene_foto else '✗'} {'Tiene' if tiene_foto else 'NO tiene'} campo para foto/avatar")
else:
    print("   ⚠ Tabla vacía")

print("\n" + "=" * 80)
print("ANÁLISIS DE DATOS DE EJEMPLO (Franco Calderon - ID 20)")
print("=" * 80)

doctor_id = 20
fecha_hoy = "2025-11-25"
fecha_hace_30 = (datetime.now() - timedelta(days=30)).date()

# Asistencias históricas
asist_hist = supabase_client.from_('asistencia').select('*').eq('usuario_sistema_id', doctor_id).execute()
print(f"\n8. ASISTENCIAS HISTÓRICAS DE FRANCO: {len(asist_hist.data)} registros")
if asist_hist.data:
    print("   Ejemplo:")
    for a in asist_hist.data[:3]:
        inicio = a['inicio_turno'][:16]
        fin = a.get('finalizacion_turno', 'EN CURSO')[:16] if a.get('finalizacion_turno') else 'EN CURSO'
        print(f"   - {inicio} → {fin}")

# Horarios programados
horarios_hist = supabase_client.from_('horarios_personal').select('*').eq('usuario_sistema_id', doctor_id).gte('inicio_bloque', f'{fecha_hace_30}T00:00:00').execute()
print(f"\n9. HORARIOS PROGRAMADOS (últimos 30 días): {len(horarios_hist.data)} bloques")

# Citas
citas_hist = supabase_client.from_('cita_medica').select('*').eq('doctor_id', doctor_id).gte('fecha_atencion', f'{fecha_hace_30}T00:00:00').execute()
print(f"\n10. CITAS MÉDICAS (últimos 30 días): {len(citas_hist.data)} citas")

print("\n" + "=" * 80)
print("RESUMEN DE NECESIDADES")
print("=" * 80)

print("\n📊 PARA IMPLEMENTAR EL PANEL COMPLETO NECESITAS:")
print("\n✅ YA TENEMOS:")
print("   - Asistencias con inicio/fin de turno")
print("   - Horarios programados (para calcular atrasos)")
print("   - Citas médicas (para pacientes agendados/atendidos)")
print("   - Especialidades del doctor")

print("\n⚠️ NECESITAMOS VERIFICAR/CREAR:")
print("   1. Campo FOTO/AVATAR en usuario_sistema (para encabezado)")
print("   2. Tabla MARCAS_ASISTENCIA (para timeline detallada de eventos)")
print("   3. Tabla ASISTENCIA_ESTADOS (para justificaciones)")
print("   4. Campo REGISTRADO_POR en asistencia/marcas (para auditoría)")

print("\n💡 FUNCIONALIDADES QUE PODEMOS CALCULAR:")
print("   - % Asistencia (asistencias / días con horario)")
print("   - Minutos de atraso promedio")
print("   - Horas trabajadas vs programadas")
print("   - Pacientes atendidos vs agendados")
print("   - Timeline del día (si agregamos marcas detalladas)")

print("\n" + "=" * 80)
