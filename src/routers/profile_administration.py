from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
from src.utils.supabase import supabase_client
import bcrypt

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


# ==================== ENDPOINTS ESPECÍFICOS PARA DOCTORES ====================

@profile_router.get("/doctor/{doctor_id}")
async def obtener_perfil_doctor(doctor_id: int):
    """
    Obtiene el perfil completo de un doctor incluyendo sus especialidades.
    """
    try:
        # Obtener datos del doctor
        doctor = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno, apellido_materno, rut, email, celular, cel_secundario, direccion, rol_id, rol(nombre)")
            .eq("id", doctor_id)
            .execute()
        )

        if not doctor.data:
            raise HTTPException(status_code=404, detail="Doctor no encontrado.")

        doctor_data = doctor.data[0]

        # Obtener especialidades del doctor
        especialidades_response = (
            supabase_client
            .table("especialidades_doctor")
            .select("especialidad_id, especialidad(id, nombre, descripcion)")
            .eq("usuario_sistema_id", doctor_id)
            .execute()
        )

        especialidades = []
        if especialidades_response.data:
            for esp_rel in especialidades_response.data:
                if esp_rel.get("especialidad"):
                    especialidades.append({
                        "id": esp_rel["especialidad"]["id"],
                        "nombre": esp_rel["especialidad"]["nombre"],
                        "descripcion": esp_rel["especialidad"].get("descripcion")
                    })

        # Preparar respuesta
        perfil = {
            "id": doctor_data["id"],
            "nombre": doctor_data["nombre"],
            "apellido_paterno": doctor_data["apellido_paterno"],
            "apellido_materno": doctor_data["apellido_materno"],
            "nombre_completo": f"{doctor_data['nombre']} {doctor_data['apellido_paterno']} {doctor_data.get('apellido_materno', '')}".strip(),
            "rut": doctor_data["rut"],
            "email": doctor_data["email"],
            "celular": doctor_data["celular"],
            "cel_secundario": doctor_data.get("cel_secundario"),
            "direccion": doctor_data["direccion"],
            "rol_id": doctor_data["rol_id"],
            "rol_nombre": doctor_data["rol"]["nombre"] if doctor_data.get("rol") else None,
            "especialidades": especialidades
        }

        return {"perfil": perfil}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@profile_router.get("/doctor/{doctor_id}/estadisticas")
async def obtener_estadisticas_doctor(doctor_id: int):
    """
    Obtiene estadísticas del doctor: pacientes atendidos y citas del mes actual.
    """
    try:
        # Verificar que el doctor existe
        doctor = (
            supabase_client
            .table("usuario_sistema")
            .select("id")
            .eq("id", doctor_id)
            .execute()
        )

        if not doctor.data:
            raise HTTPException(status_code=404, detail="Doctor no encontrado.")

        # Obtener todas las citas del doctor
        citas_response = (
            supabase_client
            .table("cita_medica")
            .select("id, fecha_atencion, paciente_id")
            .eq("doctor_id", doctor_id)
            .execute()
        )

        # Calcular estadísticas
        pacientes_unicos = set()
        citas_mes_actual = 0
        total_citas_completadas = 0
        
        ahora = datetime.now()
        inicio_mes = datetime(ahora.year, ahora.month, 1)
        
        if citas_response.data:
            for cita in citas_response.data:
                # Verificar estado de la cita
                estado_response = (
                    supabase_client
                    .table("estado")
                    .select("estado")
                    .eq("cita_medica_id", cita["id"])
                    .execute()
                )
                
                if estado_response.data:
                    estado = estado_response.data[0]["estado"]
                    
                    # Contar solo citas completadas
                    if estado == "Completada":
                        total_citas_completadas += 1
                        pacientes_unicos.add(cita["paciente_id"])
                    
                    # Contar citas del mes actual (cualquier estado excepto Cancelada)
                    fecha_cita = datetime.fromisoformat(cita["fecha_atencion"].replace('Z', '+00:00'))
                    if fecha_cita >= inicio_mes and estado != "Cancelada":
                        citas_mes_actual += 1

        estadisticas = {
            "pacientes_atendidos": len(pacientes_unicos),
            "citas_mes_actual": citas_mes_actual,
            "total_citas_completadas": total_citas_completadas
        }

        return {"estadisticas": estadisticas}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CambiarPasswordDoctor(BaseModel):
    password_actual: str
    password_nueva: str

@profile_router.post("/doctor/{doctor_id}/cambiar-password")
async def cambiar_password_doctor(doctor_id: int, passwords: CambiarPasswordDoctor):
    """
    Cambia la contraseña de un doctor.
    Verifica la contraseña actual antes de actualizar.
    """
    try:
        # Obtener contraseña actual del doctor
        password_response = (
            supabase_client
            .table("contraseñas")
            .select("id, contraseña")
            .eq("id_profesional_salud", doctor_id)
            .execute()
        )

        if not password_response.data:
            raise HTTPException(status_code=404, detail="No se encontró información de contraseña para este doctor.")

        password_data = password_response.data[0]
        password_actual_hash = password_data["contraseña"]

        # Verificar contraseña actual
        if not bcrypt.checkpw(passwords.password_actual.encode('utf-8'), password_actual_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="La contraseña actual es incorrecta.")

        # Generar hash de la nueva contraseña
        nueva_password_hash = bcrypt.hashpw(passwords.password_nueva.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Actualizar contraseña
        actualizado = (
            supabase_client
            .table("contraseñas")
            .update({
                "contraseña": nueva_password_hash,
                "contraseña_temporal": None  # Limpiar contraseña temporal si existe
            })
            .eq("id_profesional_salud", doctor_id)
            .execute()
        )

        if not actualizado.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar la contraseña.")

        return {"mensaje": "Contraseña actualizada correctamente."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ActualizarPerfilDoctor(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str] = None
    email: str
    celular: str
    cel_secundario: Optional[str] = None
    direccion: str

@profile_router.put("/doctor/{doctor_id}")
async def actualizar_perfil_doctor(doctor_id: int, perfil: ActualizarPerfilDoctor):
    """
    Actualiza los datos editables del perfil de un doctor.
    No se puede editar RUT ni especialidades (solo el admin puede hacerlo).
    """
    try:
        # Verificar que el doctor existe
        existe = (
            supabase_client
            .table("usuario_sistema")
            .select("id, rut")
            .eq("id", doctor_id)
            .execute()
        )

        if not existe.data:
            raise HTTPException(status_code=404, detail="Doctor no encontrado.")

        # Verificar que no existe otro usuario con el mismo email
        duplicado = (
            supabase_client
            .table("usuario_sistema")
            .select("id")
            .eq("email", perfil.email)
            .neq("id", doctor_id)
            .execute()
        )

        if duplicado.data:
            raise HTTPException(status_code=409, detail="Ya existe otro usuario con ese email.")

        # Actualizar datos del perfil
        actualizado = (
            supabase_client
            .table("usuario_sistema")
            .update({
                "nombre": perfil.nombre,
                "apellido_paterno": perfil.apellido_paterno,
                "apellido_materno": perfil.apellido_materno,
                "email": perfil.email,
                "celular": perfil.celular,
                "cel_secundario": perfil.cel_secundario,
                "direccion": perfil.direccion
            })
            .eq("id", doctor_id)
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
