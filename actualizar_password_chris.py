"""
Script para actualizar la contraseña del doctor chris@gmail.com
Contraseña temporal: temporal123
"""
from src.utils.supabase import supabase_client

# Hash generado para 'temporal123'
password_hash = "$2b$12$EZZrHn/JD8qMNsURUcSmxOIuH9PsHykSfgG5z2PbcJUmlHVKlrgF."

# Primero buscar el usuario
user_response = supabase_client.from_("usuario_sistema") \
    .select("id, nombre, apellido_paterno, email") \
    .eq("email", "chris@gmail.com") \
    .execute()

if not user_response.data:
    print("❌ No se encontró usuario con email chris@gmail.com")
    exit(1)

user = user_response.data[0]
user_id = user['id']

# Actualizar contraseña en la tabla contraseñas
response = supabase_client.from_("contraseñas") \
    .update({"contraseña": password_hash}) \
    .eq("id_profesional_salud", user_id) \
    .execute()

if response.data:
    print(f"✅ Contraseña actualizada para {user['email']}")
    print(f"   Usuario: {user['nombre']} {user['apellido_paterno']}")
    print(f"   Nueva contraseña: temporal123")
else:
    print(f"❌ No se encontró registro de contraseña para el usuario ID {user_id}")

