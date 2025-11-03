from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.utils.supabase import supabase_client

profile_router = APIRouter(tags=["Perfil de Usuario"], prefix="/Perfil")

class PerfilUsuario(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    rut: str
    email: str
    celular: str
    cel_secundario: Optional[str] = None
    direccion: str

@profile_router.get("/obtener/{usuario_id}")
async def obtener_perfil(usuario_id: int):
    """
    Obtiene el perfil completo de un usuario por su ID.
    Retorna los datos editables de la tabla usuario_sistema.
    """
    try:
        # Obtener datos del usuario
        usuario = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno, apellido_materno, rut, email, celular, cel_secundario, direccion, rol_id, rol(nombre)")
            .eq("id", usuario_id)
            .execute()
        )

        if not usuario.data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        usuario_data = usuario.data[0]

        # Preparar respuesta con los datos del perfil
        perfil = {
            "id": usuario_data["id"],
            "nombre": usuario_data["nombre"],
            "apellido_paterno": usuario_data["apellido_paterno"],
            "apellido_materno": usuario_data["apellido_materno"],
            "rut": usuario_data["rut"],
            "email": usuario_data["email"],
            "celular": usuario_data["celular"],
            "cel_secundario": usuario_data.get("cel_secundario"),
            "direccion": usuario_data["direccion"],
            "rol_id": usuario_data["rol_id"],
            "rol_nombre": usuario_data["rol"]["nombre"] if usuario_data.get("rol") else None
        }

        return {"perfil": perfil}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@profile_router.put("/actualizar/{usuario_id}")
async def actualizar_perfil(usuario_id: int, perfil: PerfilUsuario):
    """
    Actualiza los datos del perfil de un usuario.
    Solo actualiza los campos editables: nombre, apellidos, contacto y dirección.
    """
    try:
        # Verificar que el usuario existe
        existe = (
            supabase_client
            .table("usuario_sistema")
            .select("id")
            .eq("id", usuario_id)
            .execute()
        )

        if not existe.data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        # Verificar que no existe otro usuario con el mismo RUT o email
        duplicado = (
            supabase_client
            .table("usuario_sistema")
            .select("id")
            .or_(f"rut.eq.{perfil.rut},email.eq.{perfil.email}")
            .neq("id", usuario_id)
            .execute()
        )

        if duplicado.data:
            raise HTTPException(status_code=409, detail="Ya existe otro usuario con ese RUT o email.")

        # Actualizar datos del perfil
        actualizado = (
            supabase_client
            .table("usuario_sistema")
            .update({
                "nombre": perfil.nombre,
                "apellido_paterno": perfil.apellido_paterno,
                "apellido_materno": perfil.apellido_materno,
                "rut": perfil.rut,
                "email": perfil.email,
                "celular": perfil.celular,
                "cel_secundario": perfil.cel_secundario,
                "direccion": perfil.direccion
            })
            .eq("id", usuario_id)
            .execute()
        )

        if not actualizado.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el perfil.")

        return {
            "mensaje": "Perfil actualizado correctamente.",
            "perfil": actualizado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
