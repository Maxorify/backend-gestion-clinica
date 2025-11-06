from fastapi import APIRouter, HTTPException, status
from src.models.auth import LoginRequest, LoginResponse, UserData
from src.utils.supabase import supabase_client
from typing import Dict
import bcrypt
import secrets

auth_router = APIRouter(tags=["Autenticación"], prefix="/auth")

# Mapeo de roles a sus URLs de redirección
ROLE_REDIRECTS: Dict[str, str] = {
    "medico": "/doctor/dashboard",
    "admin": "/admin/dashboard",
    "secretaria": "/secretaria/dashboard"
}

@auth_router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Endpoint de login que valida credenciales y retorna información del usuario
    junto con la URL de redirección según su rol.

    Roles soportados:
    - medico: Redirige a /doctor/dashboard
    - admin: Redirige a /admin/dashboard
    - secretaria: Redirige a /secretaria/dashboard
    """
    try:
        # 1. Obtener información del usuario desde la tabla usuario_sistema
        user_query = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno, apellido_materno, email, rut, rol_id, rol(id, nombre)")
            .eq("email", credentials.email)
            .execute()
        )

        if not user_query.data or len(user_query.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos"
            )

        user_info = user_query.data[0]

        # 2. Verificar la contraseña desde la tabla contraseñas
        password_query = (
            supabase_client
            .table("contraseñas")
            .select("contraseña, contraseña_temporal")
            .eq("id_profesional_salud", user_info["id"])
            .execute()
        )

        if not password_query.data or len(password_query.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos"
            )

        stored_password = password_query.data[0]

        # Verificar contraseña
        password_valid = False

        # Intentar con contraseña normal
        if stored_password.get("contraseña"):
            try:
                # Si la contraseña está hasheada con bcrypt
                if stored_password["contraseña"].startswith("$2b$") or stored_password["contraseña"].startswith("$2a$"):
                    password_valid = bcrypt.checkpw(
                        credentials.password.encode('utf-8'),
                        stored_password["contraseña"].encode('utf-8')
                    )
                else:
                    # Contraseña en texto plano (no recomendado)
                    password_valid = stored_password["contraseña"] == credentials.password
            except:
                password_valid = stored_password["contraseña"] == credentials.password

        # Si no es válida, intentar con contraseña temporal
        if not password_valid and stored_password.get("contraseña_temporal"):
            try:
                if stored_password["contraseña_temporal"].startswith("$2b$") or stored_password["contraseña_temporal"].startswith("$2a$"):
                    password_valid = bcrypt.checkpw(
                        credentials.password.encode('utf-8'),
                        stored_password["contraseña_temporal"].encode('utf-8')
                    )
                else:
                    password_valid = stored_password["contraseña_temporal"] == credentials.password
            except:
                password_valid = stored_password["contraseña_temporal"] == credentials.password

        if not password_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos"
            )

        # 3. Obtener el nombre del rol
        rol_data = user_info.get("rol")

        if not rol_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sin rol asignado"
            )

        rol_nombre_original = rol_data.get("nombre", "")
        if not rol_nombre_original:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sin rol asignado"
            )

        # Normalizar el nombre del rol
        rol_nombre = rol_nombre_original.lower().strip()

        # Mapeo flexible para diferentes variaciones de nombres
        rol_mapping = {
            "medico": "medico",
            "médico": "medico",
            "doctor": "medico",
            "admin": "admin",
            "administrador": "admin",
            "administrator": "admin",
            "secretaria": "secretaria",
            "secretario": "secretaria",
        }

        # Intentar mapear el rol
        rol_normalizado = rol_mapping.get(rol_nombre, rol_nombre)

        # 4. Verificar si el rol tiene una URL de redirección
        redirect_url = ROLE_REDIRECTS.get(rol_normalizado)

        if not redirect_url:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{rol_nombre_original}' no autorizado. Roles permitidos: medico, admin, secretaria"
            )

        # 5. Si es médico, obtener su especialidad
        especialidad_id = None
        especialidad_nombre = None

        if rol_normalizado == "medico":
            especialidad_query = (
                supabase_client
                .table("especialidades_doctor")
                .select("especialidad_id, especialidad(id, nombre)")
                .eq("usuario_sistema_id", user_info["id"])
                .execute()
            )

            if especialidad_query.data and len(especialidad_query.data) > 0:
                esp_data = especialidad_query.data[0]
                especialidad_id = esp_data.get("especialidad_id")
                especialidad_nombre = esp_data.get("especialidad", {}).get("nombre")

        # 6. Generar un token simple
        auth_token = secrets.token_urlsafe(32)

        # 7. Construir respuesta con los datos del usuario
        # Verificar si tiene contraseña temporal (contraseña es null y contraseña_temporal no es null)
        tiene_contrasena_temporal = (
            stored_password.get("contraseña") is None and
            stored_password.get("contraseña_temporal") is not None
        )

        user_data = {
            "id": user_info["id"],
            "nombre": user_info["nombre"],
            "apellido_paterno": user_info["apellido_paterno"],
            "apellido_materno": user_info["apellido_materno"],
            "email": user_info["email"],
            "rut": user_info.get("rut"),
            "rol_id": user_info["rol_id"],
            "rol_nombre": rol_normalizado,  # Usar el rol normalizado
            "especialidad_id": especialidad_id,
            "especialidad_nombre": especialidad_nombre,
            "auth_token": auth_token,
            "contrasena_temporal": tiene_contrasena_temporal
        }

        return LoginResponse(
            success=True,
            message=f"Bienvenido/a {user_info['nombre']} {user_info['apellido_paterno']}",
            data=user_data,
            redirect_url=redirect_url
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el proceso de autenticación: {str(e)}"
        )


@auth_router.put("/cambiar-contrasena-temporal")
async def cambiar_contrasena_temporal(data: dict):
    """
    Endpoint para cambiar la contraseña temporal por una definitiva
    """
    try:
        usuario_id = data.get("usuario_id")
        nueva_contrasena = data.get("nueva_contrasena")

        if not usuario_id or not nueva_contrasena:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere usuario_id y nueva_contrasena"
            )

        # Validar longitud mínima
        if len(nueva_contrasena) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña debe tener al menos 8 caracteres"
            )

        # Hashear la nueva contraseña
        hashed_password = bcrypt.hashpw(
            nueva_contrasena.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Actualizar en la base de datos: establecer contraseña y eliminar contraseña temporal
        update_result = (
            supabase_client
            .table("contraseñas")
            .update({
                "contraseña": hashed_password,
                "contraseña_temporal": None
            })
            .eq("id_profesional_salud", usuario_id)
            .execute()
        )

        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        return {
            "success": True,
            "message": "Contraseña actualizada correctamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar contraseña: {str(e)}"
        )


@auth_router.post("/logout")
async def logout():
    """
    Endpoint para cerrar sesión
    """
    return {"success": True, "message": "Sesión cerrada correctamente"}


@auth_router.get("/debug/roles")
async def debug_roles():
    """
    Endpoint de diagnóstico para ver todos los roles en la base de datos
    ELIMINAR EN PRODUCCIÓN
    """
    try:
        roles_query = (
            supabase_client
            .table("rol")
            .select("*")
            .execute()
        )
        return {
            "success": True,
            "roles": roles_query.data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )
