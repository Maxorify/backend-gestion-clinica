from src.utils.supabase import supabase_client

print("🧹 LIMPIEZA COMPLETA PARA MONICA (ID: 25)")
print("=" * 60)

# 1. Eliminar todas las asistencias
print("\n1️⃣ Eliminando asistencias...")
result_asist = supabase_client.from_("asistencia") \
    .delete() \
    .eq("usuario_sistema_id", 25) \
    .execute()
print(f"   ✅ Asistencias eliminadas")

# 2. Eliminar todas las citas médicas donde Monica es el doctor
print("\n2️⃣ Eliminando citas médicas...")
result_citas = supabase_client.from_("cita_medica") \
    .delete() \
    .eq("doctor_id", 25) \
    .execute()
print(f"   ✅ Citas eliminadas")

# 3. Eliminar todos los horarios
print("\n3️⃣ Eliminando horarios...")
result_horarios = supabase_client.from_("horarios_personal") \
    .delete() \
    .eq("usuario_sistema_id", 25) \
    .execute()
print(f"   ✅ Horarios eliminados")

print("\n✅ LIMPIEZA COMPLETA")
print("\nAhora puedes:")
print("  1. Crear horarios para hoy (08:00-23:00)")
print("  2. Crear un paciente de prueba")
print("  3. Agendar cita en un bloque")
print("  4. Marcar entrada como doctor")
print("  5. Atender paciente")
print("  6. Marcar salida")
