from fastapi import APIRouter, HTTPException, Query
from src.models.users import Rol, Usuario
from src.utils.supabase import supabase_client

user_router = APIRouter(tags=["Gestión de Usuarios y Roles"], prefix="/Usuarios")

@user_router.post("/crear-rol")
async def crear_rol(rol: Rol):
    """
    Crea un nuevo rol en la tabla public.rol si no existe.
    Lanza error 409 si el nombre ya está registrado.
    """
    try:
        # 1) Verificar si ya existe
        existe = (
            supabase_client
            .table("rol")
            .select("id, nombre")
            .eq("nombre", rol.nombre)
            .execute()
        )
        if existe.data:
            raise HTTPException(
                status_code=409,
                detail=f"El rol '{rol.nombre}' ya existe en el sistema."
            )

        # 2) Insertar nuevo rol
        nuevo = (
            supabase_client
            .table("rol")
            .insert({
                "nombre": rol.nombre,
                "descripcion": rol.descripcion
            })
            .execute()
        )
        if not nuevo.data:
            raise HTTPException(status_code=500, detail="No se pudo insertar el rol.")

        # 3) Obtener lista de roles actualizada
        roles_actuales = (
            supabase_client
            .table("rol")
            .select("id, nombre, descripcion")
            .order("id", desc=False)
            .execute()
        )

        return {
            "mensaje": f"Rol '{rol.nombre}' creado correctamente.",
            "roles_actuales": roles_actuales.data
        }

    except HTTPException:
        raise
    except Exception as e:
        # Si Supabase devuelve JSON de error, pásalo textual para no perder el detalle
        raise HTTPException(status_code=500, detail=str(e))
@user_router.put("/modificar-rol/{rol_id}")
async def modificar_rol(rol_id: int, rol: Rol):
    """
    Modifica un rol existente según su ID.
    Lanza 404 si no existe el rol.
    Lanza 409 si se intenta cambiar a un nombre ya usado.
    """
    try:
        # Verificar existencia
        existente = (
            supabase_client
            .table("rol")
            .select("id, nombre")
            .eq("id", rol_id)
            .execute()
        )

        if not existente.data:
            raise HTTPException(status_code=404, detail=f"No existe el rol con ID {rol_id}.")

        # Verificar duplicado de nombre (otro rol con mismo nombre)
        duplicado = (
            supabase_client
            .table("rol")
            .select("id")
            .eq("nombre", rol.nombre)
            .neq("id", rol_id)
            .execute()
        )
        if duplicado.data:
            raise HTTPException(status_code=409, detail=f"Ya existe otro rol con nombre '{rol.nombre}'.")

        # Actualizar datos
        actualizado = (
            supabase_client
            .table("rol")
            .update({
                "nombre": rol.nombre,
                "descripcion": rol.descripcion
            })
            .eq("id", rol_id)
            .execute()
        )

        if not actualizado.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el rol.")

        return {
            "mensaje": f"Rol '{rol.nombre}' modificado correctamente.",
            "rol_actualizado": actualizado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@user_router.delete("/eliminar-rol/{rol_id}")
async def eliminar_rol(rol_id: int):
    """
    Elimina un rol existente por su ID.
    Lanza 404 si el rol no existe.
    """
    try:
        # Verificar existencia
        existe = (
            supabase_client
            .table("rol")
            .select("id, nombre")
            .eq("id", rol_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail=f"No existe el rol con ID {rol_id}.")

        nombre = existe.data[0]["nombre"]

        # Eliminar el rol
        eliminado = (
            supabase_client
            .table("rol")
            .delete()
            .eq("id", rol_id)
            .execute()
        )

        if not eliminado.data:
            raise HTTPException(status_code=500, detail="No se pudo eliminar el rol.")

        return {"mensaje": f"Rol '{nombre}' eliminado correctamente."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post("/crear-usuario")
async def crear_usuario(usuario: Usuario):
    """
    Crea un nuevo usuario en la tabla usuario_sistema.
    Rut y email deben ser únicos.
    """
    try:
        # Verificar si ya existe rut o email
        existe = (
            supabase_client
            .table("usuario_sistema")
            .select("id")
            .or_(f"rut.eq.{usuario.rut},email.eq.{usuario.email}")
            .execute()
        )
        if existe.data:
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese rut o email.")

        nuevo = (
            supabase_client
            .table("usuario_sistema")
            .insert({
                "nombre": usuario.nombre,
                "apellido_paterno": usuario.apellido_paterno,
                "apellido_materno": usuario.apellido_materno,
                "rut": usuario.rut,
                "email": usuario.email,
                "celular": usuario.celular,
                "cel_secundario": usuario.cel_secundario,
                "direccion": usuario.direccion,
                "rol_id": usuario.rol_id
            })
            .execute()
        )
        if not nuevo.data:
            raise HTTPException(status_code=500, detail="No se pudo crear el usuario.")

        usuario_id = nuevo.data[0]["id"]

        # Si tiene especialidades (múltiples), agregar a especialidades_doctor
        if usuario.especialidades_ids and len(usuario.especialidades_ids) > 0:
            # Insertar múltiples especialidades
            especialidades_data = [
                {
                    "usuario_sistema_id": usuario_id,
                    "especialidad_id": esp_id
                }
                for esp_id in usuario.especialidades_ids
            ]
            supabase_client.table("especialidades_doctor").insert(especialidades_data).execute()
        elif usuario.especialidad_id and usuario.especialidad_id != "":
            # Compatibilidad con especialidad única
            supabase_client.table("especialidades_doctor").insert({
                "usuario_sistema_id": usuario_id,
                "especialidad_id": int(usuario.especialidad_id)
            }).execute()

        # Si tiene contraseña temporal, crear registro en tabla contraseñas
        if usuario.contraseña_temporal and usuario.contraseña_temporal != "":
            supabase_client.table("contraseñas").insert({
                "id_profesional_salud": usuario_id,
                "contraseña_temporal": usuario.contraseña_temporal,
                "contraseña": None  # La contraseña permanente se establecerá al primer login
            }).execute()

        return {"mensaje": "Usuario creado correctamente.", "usuario": nuevo.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.put("/modificar-usuario/{usuario_id}")
async def modificar_usuario(usuario_id: int, usuario: Usuario):
    """
    Modifica los datos de un usuario existente.
    """
    try:
        existe = (
            supabase_client
            .table("usuario_sistema")
            .select("id")
            .eq("id", usuario_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail="No existe el usuario.")

        # Verificar duplicado de rut o email (en otro usuario)
        duplicado = (
            supabase_client
            .table("usuario_sistema")
            .select("id")
            .or_(f"rut.eq.{usuario.rut},email.eq.{usuario.email}")
            .neq("id", usuario_id)
            .execute()
        )
        if duplicado.data:
            raise HTTPException(status_code=409, detail="Ya existe otro usuario con ese rut o email.")

        actualizado = (
            supabase_client
            .table("usuario_sistema")
            .update({
                "nombre": usuario.nombre,
                "apellido_paterno": usuario.apellido_paterno,
                "apellido_materno": usuario.apellido_materno,
                "rut": usuario.rut,
                "email": usuario.email,
                "celular": usuario.celular,
                "cel_secundario": usuario.cel_secundario,
                "direccion": usuario.direccion,
                "rol_id": usuario.rol_id
            })
            .eq("id", usuario_id)
            .execute()
        )
        if not actualizado.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el usuario.")

        # Actualizar especialidades (en especialidades_doctor)
        if usuario.especialidades_ids is not None:
            # Primero eliminar todas las especialidades existentes
            supabase_client.table("especialidades_doctor").delete().eq("usuario_sistema_id", usuario_id).execute()
            
            # Luego insertar las nuevas especialidades
            if len(usuario.especialidades_ids) > 0:
                especialidades_data = [
                    {
                        "usuario_sistema_id": usuario_id,
                        "especialidad_id": esp_id
                    }
                    for esp_id in usuario.especialidades_ids
                ]
                supabase_client.table("especialidades_doctor").insert(especialidades_data).execute()
        elif usuario.especialidad_id and usuario.especialidad_id != "":
            # Compatibilidad con especialidad única
            # Eliminar todas y agregar solo una
            supabase_client.table("especialidades_doctor").delete().eq("usuario_sistema_id", usuario_id).execute()
            supabase_client.table("especialidades_doctor").insert({
                "usuario_sistema_id": usuario_id,
                "especialidad_id": int(usuario.especialidad_id)
            }).execute()

        return {"mensaje": "Usuario modificado correctamente.", "usuario": actualizado.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.delete("/eliminar-usuario/{usuario_id}")
async def eliminar_usuario(usuario_id: int):
    """
    Desactiva un usuario (soft delete) cambiando su estado a inactivo.
    El usuario y sus relaciones se mantienen en la base de datos pero no aparecerán en listados.
    """
    try:
        existe = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno, activo")
            .eq("id", usuario_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail="No existe el usuario.")

        usuario = existe.data[0]
        if not usuario.get("activo", True):
            raise HTTPException(status_code=400, detail="El usuario ya está inactivo.")

        # Soft delete: marcar como inactivo en lugar de eliminar
        actualizado = (
            supabase_client
            .table("usuario_sistema")
            .update({"activo": False})
            .eq("id", usuario_id)
            .execute()
        )
        if not actualizado.data:
            raise HTTPException(status_code=500, detail="No se pudo desactivar el usuario.")

        nombre_completo = f"{usuario.get('nombre', '')} {usuario.get('apellido_paterno', '')}".strip()
        return {"mensaje": f"Usuario {nombre_completo} desactivado correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@user_router.get("/listar-usuarios")
async def listar_usuarios():
    """
    Devuelve todos los usuarios existentes en la tabla 'usuario_sistema'.
    Para doctores (rol_id=2), incluye su especialidad desde la tabla especialidades_doctor.
    OPTIMIZADO: Bulk query en lugar de N+1.
    """
    try:
        # Obtener todos los usuarios
        res = (
            supabase_client
            .table("usuario_sistema")
            .select("*")
            .order("id", desc=False)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="No hay usuarios registrados.")
        
        usuarios = res.data
        
        # OPTIMIZACIÓN: Obtener IDs de todos los doctores
        doctor_ids = [u["id"] for u in usuarios if u.get("rol_id") == 2]
        
        # OPTIMIZACIÓN: Bulk query de especialidades de TODOS los doctores (1 query en lugar de N)
        especialidades_dict = {}
        if doctor_ids:
            especialidades_response = (
                supabase_client
                .table("especialidades_doctor")
                .select("usuario_sistema_id, especialidad_id, sub_especialidad_id")
                .in_("usuario_sistema_id", doctor_ids)
                .execute()
            )
            
            # Agrupar especialidades por usuario_id
            if especialidades_response.data:
                for item in especialidades_response.data:
                    usuario_id = item["usuario_sistema_id"]
                    if usuario_id not in especialidades_dict:
                        especialidades_dict[usuario_id] = []
                    especialidades_dict[usuario_id].append(item)
        
        # Mapear especialidades usando lookups O(1)
        for usuario in usuarios:
            if usuario.get("rol_id") == 2:
                especialidades_data = especialidades_dict.get(usuario["id"], [])
                
                if especialidades_data:
                    usuario["especialidades_ids"] = [item["especialidad_id"] for item in especialidades_data]
                    # Mantener compatibilidad: primera especialidad como principal
                    usuario["especialidad_id"] = especialidades_data[0].get("especialidad_id")
                    usuario["sub_especialidad_id"] = especialidades_data[0].get("sub_especialidad_id")
                else:
                    usuario["especialidades_ids"] = []
                    usuario["especialidad_id"] = None
                    usuario["sub_especialidad_id"] = None
            else:
                usuario["especialidades_ids"] = []
                usuario["especialidad_id"] = None
                usuario["sub_especialidad_id"] = None
        
        return {"usuarios": usuarios}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/listar-doctores-paginado")
async def listar_doctores_paginado(
    page: int = Query(1, ge=1, description="Número de página (comienza en 1)"),
    page_size: int = Query(6, ge=1, le=50, description="Cantidad de doctores por página (máximo 50)"),
    search: str = Query(None, description="Búsqueda por nombre, apellido o RUT")
):
    """
    Devuelve doctores (rol_id=2) de forma paginada con sus especialidades.
    SUPER OPTIMIZADO: 2 queries totales con LEFT JOINs (antes eran 13 queries).
    """
    try:
        # Calcular offset para la paginación
        offset = (page - 1) * page_size
        
        # QUERY 1: Obtener doctores con contraseña temporal en un solo JOIN
        query = (
            supabase_client
            .table("usuario_sistema")
            .select("""
                *,
                contraseñas!left(contraseña_temporal)
            """, count="exact")
            .eq("rol_id", 2)
        )
        
        # Aplicar búsqueda si existe
        if search:
            query = query.or_(
                f"nombre.ilike.%{search}%,"
                f"apellido_paterno.ilike.%{search}%,"
                f"apellido_materno.ilike.%{search}%,"
                f"rut.ilike.%{search}%"
            )
        
        # Aplicar paginación y ordenar
        res = (
            query
            .order("id", desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        
        if not res.data:
            return {
                "doctores": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }
        
        doctores = res.data
        total_count = res.count if hasattr(res, 'count') else len(doctores)
        
        # Extraer contraseñas del JOIN y limpiar estructura
        for doctor in doctores:
            contraseñas_array = doctor.pop("contraseñas", [])
            doctor["contraseña_temporal"] = contraseñas_array[0].get("contraseña_temporal") if contraseñas_array else None
        
        # QUERY 2: Bulk query de especialidades de TODOS los doctores
        doctor_ids = [doctor["id"] for doctor in doctores]
        
        especialidades_response = (
            supabase_client
            .table("especialidades_doctor")
            .select("usuario_sistema_id, especialidad_id, sub_especialidad_id, especialidad(id, nombre)")
            .in_("usuario_sistema_id", doctor_ids)
            .execute()
        )
        
        # Agrupar especialidades por doctor_id en dict para O(1) lookup
        especialidades_dict = {}
        if especialidades_response.data:
            for item in especialidades_response.data:
                doctor_id = item["usuario_sistema_id"]
                if doctor_id not in especialidades_dict:
                    especialidades_dict[doctor_id] = []
                especialidades_dict[doctor_id].append(item)
        
        # Mapear especialidades usando lookups O(1)
        for doctor in doctores:
            doctor_id = doctor["id"]
            especialidades_data = especialidades_dict.get(doctor_id, [])
            
            if especialidades_data:
                doctor["especialidades"] = [
                    {
                        "id": item["especialidad_id"],
                        "nombre": item["especialidad"]["nombre"] if item.get("especialidad") else "Sin nombre"
                    }
                    for item in especialidades_data
                ]
                doctor["especialidades_ids"] = [item["especialidad_id"] for item in especialidades_data]
                doctor["especialidad_id"] = especialidades_data[0].get("especialidad_id")
                doctor["sub_especialidad_id"] = especialidades_data[0].get("sub_especialidad_id")
            else:
                doctor["especialidades"] = []
                doctor["especialidades_ids"] = []
                doctor["especialidad_id"] = None
                doctor["sub_especialidad_id"] = None
        
        # Calcular total de páginas
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "doctores": doctores,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    except Exception as e:
        import traceback
        print(f"ERROR en listar_doctores_paginado: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error al listar doctores: {str(e)}")
    

@user_router.get("/obtener-usuario/{usuario_id}")
async def obtener_usuario(usuario_id: int):
    """
    Devuelve la información de un usuario específico.
    Para doctores (rol_id=2), incluye sus especialidades.
    """
    try:
        # Obtener el usuario
        res = (
            supabase_client
            .table("usuario_sistema")
            .select("*")
            .eq("id", usuario_id)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail=f"No se encontró el usuario con ID {usuario_id}.")

        usuario = res.data[0]

        # Si es doctor (rol_id=2), obtener sus especialidades
        if usuario.get("rol_id") == 2:
            especialidades_doctor = (
                supabase_client
                .table("especialidades_doctor")
                .select("especialidad_id, sub_especialidad_id")
                .eq("usuario_sistema_id", usuario_id)
                .execute()
            )

            if especialidades_doctor.data:
                # Obtener detalles de cada especialidad
                especialidades_detalle = []
                for esp in especialidades_doctor.data:
                    especialidad = (
                        supabase_client
                        .table("especialidad")
                        .select("id, nombre, descripcion")
                        .eq("id", esp["especialidad_id"])
                        .execute()
                    )
                    if especialidad.data:
                        especialidades_detalle.append(especialidad.data[0])

                usuario["especialidades"] = especialidades_detalle
            else:
                usuario["especialidades"] = []
        else:
            usuario["especialidades"] = []

        return usuario

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/listar-roles")
async def listar_roles():
    """
    Devuelve todos los roles existentes en la tabla 'rol'.
    """
    try:
        res = (
            supabase_client
            .table("rol")
            .select("*")
            .order("id", desc=False)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="No hay roles registrados.")

        return {"roles": res.data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/obtener-clave-temporal/{usuario_id}")
async def obtener_clave_temporal(usuario_id: int):
    """
    Obtiene la contraseña temporal de un usuario si existe.
    """
    try:
        # Verificar que el usuario existe
        usuario = (
            supabase_client
            .table("usuario_sistema")
            .select("id, rol_id")
            .eq("id", usuario_id)
            .execute()
        )

        if not usuario.data:
            raise HTTPException(status_code=404, detail="No existe el usuario.")

        # Buscar registro de contraseña
        registro_password = (
            supabase_client
            .table("contraseñas")
            .select("contraseña_temporal")
            .eq("id_profesional_salud", usuario_id)
            .execute()
        )

        if registro_password.data and registro_password.data[0].get("contraseña_temporal"):
            return {
                "tiene_clave": True,
                "contraseña_temporal": registro_password.data[0]["contraseña_temporal"]
            }
        else:
            return {
                "tiene_clave": False,
                "contraseña_temporal": None
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post("/generar-clave-temporal/{usuario_id}")
async def generar_clave_temporal(usuario_id: int, contraseña_temporal: str = Query(..., description="Contraseña temporal a establecer")):
    """
    Genera o actualiza la contraseña temporal de un usuario (doctor).
    """
    try:
        # Verificar que el usuario existe
        usuario = (
            supabase_client
            .table("usuario_sistema")
            .select("id, rol_id")
            .eq("id", usuario_id)
            .execute()
        )

        if not usuario.data:
            raise HTTPException(status_code=404, detail="No existe el usuario.")

        # Verificar si ya tiene un registro en la tabla contraseñas
        registro_password = (
            supabase_client
            .table("contraseñas")
            .select("id")
            .eq("id_profesional_salud", usuario_id)
            .execute()
        )

        if registro_password.data:
            # Actualizar la contraseña temporal existente
            supabase_client.table("contraseñas").update({
                "contraseña_temporal": contraseña_temporal
            }).eq("id_profesional_salud", usuario_id).execute()
        else:
            # Crear nuevo registro con contraseña temporal
            supabase_client.table("contraseñas").insert({
                "id_profesional_salud": usuario_id,
                "contraseña_temporal": contraseña_temporal,
                "contraseña": None
            }).execute()

        return {
            "mensaje": "Contraseña temporal generada correctamente.",
            "contraseña_temporal": contraseña_temporal
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/usuario/{usuario_id}")
async def obtener_datos_usuario(usuario_id: int):
    """
    Obtiene los datos del usuario para su perfil personal.
    """
    try:
        usuario = (
            supabase_client
            .table("usuario_sistema")
            .select("id, nombre, apellido_paterno, apellido_materno, rut, email, celular, cel_secundario, direccion")
            .eq("id", usuario_id)
            .single()
            .execute()
        )

        if not usuario.data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return usuario.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener usuario: {str(e)}")


@user_router.put("/actualizar-usuario/{usuario_id}")
async def actualizar_usuario(usuario_id: int, datos: dict):
    """
    Actualiza los datos personales del usuario.
    """
    try:
        # Campos permitidos para actualización
        campos_permitidos = {
            "nombre", "apellido_paterno", "apellido_materno", 
            "rut", "email", "celular", "cel_secundario", "direccion"
        }
        
        # Filtrar solo los campos permitidos
        datos_actualizar = {k: v for k, v in datos.items() if k in campos_permitidos}
        
        if not datos_actualizar:
            raise HTTPException(status_code=400, detail="No hay datos válidos para actualizar")

        # Verificar que el usuario existe
        usuario = (
            supabase_client
            .table("usuario_sistema")
            .select("id")
            .eq("id", usuario_id)
            .single()
            .execute()
        )

        if not usuario.data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Si se está actualizando el email, verificar que no esté en uso
        if "email" in datos_actualizar and datos_actualizar["email"]:
            email_existe = (
                supabase_client
                .table("usuario_sistema")
                .select("id")
                .eq("email", datos_actualizar["email"])
                .neq("id", usuario_id)
                .execute()
            )
            if email_existe.data:
                raise HTTPException(status_code=409, detail="El email ya está en uso")

        # Actualizar el usuario
        supabase_client.table("usuario_sistema").update(
            datos_actualizar
        ).eq("id", usuario_id).execute()

        return {"mensaje": "Usuario actualizado correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar usuario: {str(e)}")


@user_router.put("/cambiar-password/{usuario_id}")
async def cambiar_password(usuario_id: int, datos: dict):
    """
    Cambia la contraseña del usuario.
    Requiere la contraseña actual y la nueva contraseña.
    """
    try:
        password_actual = datos.get("password_actual")
        password_nueva = datos.get("password_nueva")

        if not password_actual or not password_nueva:
            raise HTTPException(
                status_code=400, 
                detail="Se requiere la contraseña actual y la nueva contraseña"
            )

        # Verificar que el usuario existe
        usuario = (
            supabase_client
            .table("usuario_sistema")
            .select("id")
            .eq("id", usuario_id)
            .single()
            .execute()
        )

        if not usuario.data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Obtener el registro de contraseñas
        registro_password = (
            supabase_client
            .table("contraseñas")
            .select("id, contraseña")
            .eq("id_profesional_salud", usuario_id)
            .single()
            .execute()
        )

        if not registro_password.data:
            raise HTTPException(
                status_code=404, 
                detail="No se encontró registro de contraseña para este usuario"
            )

        # Verificar que la contraseña actual coincide
        if registro_password.data["contraseña"] != password_actual:
            raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")

        # Actualizar la contraseña
        supabase_client.table("contraseñas").update({
            "contraseña": password_nueva,
            "contraseña_temporal": None  # Limpiar contraseña temporal si existe
        }).eq("id_profesional_salud", usuario_id).execute()

        return {"mensaje": "Contraseña cambiada correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cambiar contraseña: {str(e)}")
