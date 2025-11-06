from fastapi import APIRouter, HTTPException
from src.utils.supabase import supabase_client
from src.models.users import Especialidad, SubEspecialidad, VinculoEspSub

doctor_router = APIRouter(tags=["Funciones de administración de doctores"], prefix="/doctores")

# -----------------------
# ESPECIALIDAD
# -----------------------

@doctor_router.post("/crear-especialidad")
async def crear_especialidad(especialidad: Especialidad):
    try:
        existe = supabase_client.table("especialidad").select("id").eq("nombre", especialidad.nombre).execute()
        if existe.data:
            raise HTTPException(status_code=409, detail=f"La especialidad '{especialidad.nombre}' ya existe.")

        # Crear la especialidad
        creado_esp = supabase_client.table("especialidad").insert({
            "nombre": especialidad.nombre,
            "descripcion": especialidad.descripcion
        }).execute()
        if not creado_esp.data:
            raise HTTPException(status_code=500, detail="No se pudo insertar la especialidad.")

        especialidad_id = creado_esp.data[0]["id"]

        # Si se proporcionó un precio, crear el registro en costos_servicio
        if especialidad.precio is not None and especialidad.precio > 0:
            supabase_client.table("costos_servicio").insert({
                "servicio": f"Consulta {especialidad.nombre}",
                "precio": especialidad.precio,
                "especialidad_id": especialidad_id
            }).execute()

        lista = supabase_client.table("especialidad").select("id,nombre,descripcion").order("id").execute()
        return {"mensaje": f"Especialidad '{especialidad.nombre}' creada.", "especialidades": lista.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@doctor_router.put("/modificar-especialidad/{especialidad_id}")
async def modificar_especialidad(especialidad_id: int, especialidad: Especialidad):
    try:
        existe = supabase_client.table("especialidad").select("id").eq("id", especialidad_id).execute()
        if not existe.data:
            raise HTTPException(status_code=404, detail=f"No existe la especialidad con ID {especialidad_id}.")

        duplicado = (supabase_client.table("especialidad")
                     .select("id").eq("nombre", especialidad.nombre).neq("id", especialidad_id).execute())
        if duplicado.data:
            raise HTTPException(status_code=409, detail=f"Ya existe otra especialidad con nombre '{especialidad.nombre}'.")

        act = (supabase_client.table("especialidad")
               .update({"nombre": especialidad.nombre, "descripcion": especialidad.descripcion})
               .eq("id", especialidad_id).execute())
        if not act.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar la especialidad.")

        # Actualizar o crear el precio en costos_servicio
        if especialidad.precio is not None:
            costo_existe = supabase_client.table("costos_servicio").select("id").eq("especialidad_id", especialidad_id).execute()

            if costo_existe.data:
                # Actualizar precio existente
                supabase_client.table("costos_servicio").update({
                    "servicio": f"Consulta {especialidad.nombre}",
                    "precio": especialidad.precio
                }).eq("especialidad_id", especialidad_id).execute()
            else:
                # Crear nuevo precio
                supabase_client.table("costos_servicio").insert({
                    "servicio": f"Consulta {especialidad.nombre}",
                    "precio": especialidad.precio,
                    "especialidad_id": especialidad_id
                }).execute()

        return {"mensaje": f"Especialidad '{especialidad.nombre}' modificada.", "especialidad": act.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@doctor_router.delete("/eliminar-especialidad/{especialidad_id}")
async def eliminar_especialidad(especialidad_id: int):
    try:
        esp = supabase_client.table("especialidad").select("id,nombre").eq("id", especialidad_id).execute()
        if not esp.data:
            raise HTTPException(status_code=404, detail=f"No existe la especialidad con ID {especialidad_id}.")
        nombre = esp.data[0]["nombre"]


        # Bloquea si hay vínculos o referencias
        ref_vinculos = (supabase_client.table("especialidad_con_subespecialidad")
                        .select("id").eq("especialidad_id", especialidad_id).limit(1).execute())
        if ref_vinculos.data:
            raise HTTPException(status_code=409, detail=f"No puedes eliminar '{nombre}' porque tiene subespecialidades vinculadas.")

        # Cambiado: revisa si hay usuarios asignados a la especialidad en especialidades_doctor
        ref_users = (supabase_client.table("especialidades_doctor")
                     .select("id").eq("especialidad_id", especialidad_id).limit(1).execute())
        if ref_users.data:
            raise HTTPException(status_code=409, detail=f"No puedes eliminar '{nombre}' porque está asignada a usuarios.")

        ref_costos = (supabase_client.table("costos_servicio")
                      .select("id").eq("especialidad_id", especialidad_id).limit(1).execute())
        if ref_costos.data:
            raise HTTPException(status_code=409, detail=f"No puedes eliminar '{nombre}' porque está referenciada por costos de servicio.")

        delr = supabase_client.table("especialidad").delete().eq("id", especialidad_id).execute()
        if not delr.data:
            raise HTTPException(status_code=500, detail="No se pudo eliminar la especialidad.")

        return {"mensaje": f"Especialidad '{nombre}' eliminada correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------
# SUB_ESPECIALIDAD
# -----------------------

@doctor_router.post("/crear-subespecialidad")
async def crear_subespecialidad(sub: SubEspecialidad):
    try:
        existe = supabase_client.table("sub_especialidad").select("id").eq("nombre", sub.nombre).execute()
        if existe.data:
            raise HTTPException(status_code=409, detail=f"La subespecialidad '{sub.nombre}' ya existe.")

        creado = supabase_client.table("sub_especialidad").insert({
            "nombre": sub.nombre,
            "descripcion": sub.descripcion
        }).execute()
        if not creado.data:
            raise HTTPException(status_code=500, detail="No se pudo insertar la subespecialidad.")

        lista = supabase_client.table("sub_especialidad").select("id,nombre,descripcion").order("id").execute()
        return {"mensaje": f"Subespecialidad '{sub.nombre}' creada.", "subespecialidades": lista.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@doctor_router.put("/modificar-subespecialidad/{sub_id}")
async def modificar_subespecialidad(sub_id: int, sub: SubEspecialidad):
    try:
        existe = supabase_client.table("sub_especialidad").select("id").eq("id", sub_id).execute()
        if not existe.data:
            raise HTTPException(status_code=404, detail=f"No existe la subespecialidad con ID {sub_id}.")

        duplicado = (supabase_client.table("sub_especialidad")
                     .select("id").eq("nombre", sub.nombre).neq("id", sub_id).execute())
        if duplicado.data:
            raise HTTPException(status_code=409, detail=f"Ya existe otra subespecialidad con nombre '{sub.nombre}'.")

        act = (supabase_client.table("sub_especialidad")
               .update({"nombre": sub.nombre, "descripcion": sub.descripcion})
               .eq("id", sub_id).execute())
        if not act.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar la subespecialidad.")

        return {"mensaje": f"Subespecialidad '{sub.nombre}' modificada.", "subespecialidad": act.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@doctor_router.delete("/eliminar-subespecialidad/{sub_id}")
async def eliminar_subespecialidad(sub_id: int):
    try:
        sub = supabase_client.table("sub_especialidad").select("id,nombre").eq("id", sub_id).execute()
        if not sub.data:
            raise HTTPException(status_code=404, detail=f"No existe la subespecialidad con ID {sub_id}.")
        nombre = sub.data[0]["nombre"]

        ref_vinculos = (supabase_client.table("especialidad_con_subespecialidad")
                        .select("id").eq("sub_especialidad_id", sub_id).limit(1).execute())
        if ref_vinculos.data:
            raise HTTPException(status_code=409, detail=f"No puedes eliminar '{nombre}' porque está vinculada a especialidades.")

        delr = supabase_client.table("sub_especialidad").delete().eq("id", sub_id).execute()
        if not delr.data:
            raise HTTPException(status_code=500, detail="No se pudo eliminar la subespecialidad.")

        return {"mensaje": f"Subespecialidad '{nombre}' eliminada correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------
# VÍNCULOS ESPECIALIDAD <-> SUB_ESPECIALIDAD
# -----------------------

@doctor_router.post("/vincular-subespecialidad")
async def vincular_subespecialidad(v: VinculoEspSub):
    """
    Crea el vínculo especialidad <-> sub_especialidad.
    Evita duplicados.
    """
    try:
        # Evitar duplicados
        ya = (supabase_client.table("especialidad_con_subespecialidad")
              .select("id").eq("especialidad_id", v.especialidad_id)
              .eq("sub_especialidad_id", v.sub_especialidad_id).execute())
        if ya.data:
            raise HTTPException(status_code=409, detail="Ya existe ese vínculo.")

        creado = (supabase_client.table("especialidad_con_subespecialidad")
                  .insert({"especialidad_id": v.especialidad_id, "sub_especialidad_id": v.sub_especialidad_id})
                  .execute())
        if not creado.data:
            raise HTTPException(status_code=500, detail="No se pudo crear el vínculo.")

        return {"mensaje": "Vínculo creado."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@doctor_router.delete("/desvincular-subespecialidad")
async def desvincular_subespecialidad(v: VinculoEspSub):
    try:
        delr = (supabase_client.table("especialidad_con_subespecialidad")
                .delete().eq("especialidad_id", v.especialidad_id)
                .eq("sub_especialidad_id", v.sub_especialidad_id).execute())
        if delr.data == []:
            raise HTTPException(status_code=404, detail="El vínculo no existe.")
        return {"mensaje": "Vínculo eliminado."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@doctor_router.get("/especialidades/{especialidad_id}/subespecialidades")
async def listar_subespecialidades_de_especialidad(especialidad_id: int):
    """
    Lista las subespecialidades vinculadas a una especialidad.
    """
    try:
        vinculos = (supabase_client.table("especialidad_con_subespecialidad")
                    .select("sub_especialidad_id").eq("especialidad_id", especialidad_id).execute())
        ids = [row["sub_especialidad_id"] for row in (vinculos.data or [])]
        if not ids:
            return {"subespecialidades": []}

        # Trae las subespecialidades por sus IDs
        res = supabase_client.table("sub_especialidad").select("id,nombre,descripcion").in_("id", ids).execute()
        return {"subespecialidades": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- LISTAR ESPECIALIDADES ---
@doctor_router.get("/especialidades")
async def listar_especialidades():
    """
    Devuelve todas las especialidades con sus precios.
    """
    try:
        res = (
            supabase_client
            .table("especialidad")
            .select("id,nombre,descripcion")
            .order("id", desc=False)
            .execute()
        )

        # Para cada especialidad, obtener el precio desde costos_servicio
        especialidades_con_precio = []
        for esp in (res.data or []):
            costo = supabase_client.table("costos_servicio").select("precio").eq("especialidad_id", esp["id"]).execute()
            esp["precio"] = costo.data[0]["precio"] if costo.data else None
            especialidades_con_precio.append(esp)

        return {"especialidades": especialidades_con_precio}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- LISTAR DOCTORES ---
@doctor_router.get("/listar")
async def listar_doctores():
    """
    Devuelve la lista de todos los doctores con su información básica.
    """
    try:
        res = (
            supabase_client
            .table("doctores")
            .select("""
                id,
                persona:persona_id (
                    id, nombre, apellido_paterno, apellido_materno, rut, email
                ),
                especialidad_principal,
                estado
            """)
            .execute()
        )
        
        # Transformar los datos para el frontend
        doctores = []
        for doctor in res.data or []:
            persona = doctor.get("persona", {})
            doctores.append({
                "id": doctor.get("id"),
                "nombre": f"{persona.get('nombre', '')} {persona.get('apellido_paterno', '')} {persona.get('apellido_materno', '')}".strip(),
                "email": persona.get("email", ""),
                "persona": {
                    "rut": persona.get("rut", "")
                },
                "especialidades": doctor.get("especialidad_principal", "")
            })
            
        return doctores
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- LISTAR SUBESPECIALIDADES ---
@doctor_router.get("/subespecialidades")
async def listar_subespecialidades():
    """
    Devuelve todas las subespecialidades.
    """
    try:
        res = (
            supabase_client
            .table("sub_especialidad")
            .select("id,nombre,descripcion")
            .order("id", desc=False)
            .execute()
        )
        return {"subespecialidades": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- LISTAR SUBESPECIALIDADES DE UNA ESPECIALIDAD ---
@doctor_router.get("/especialidades/{especialidad_id}/subespecialidades")
async def listar_subespecialidades_de_especialidad(especialidad_id: int):
    """
    Devuelve las subespecialidades vinculadas a una especialidad dada.
    """
    try:
        vinculos = (
            supabase_client
            .table("especialidad_con_subespecialidad")
            .select("sub_especialidad_id")
            .eq("especialidad_id", especialidad_id)
            .execute()
        )
        ids = [r["sub_especialidad_id"] for r in (vinculos.data or [])]
        if not ids:
            return {"subespecialidades": []}

        res = (
            supabase_client
            .table("sub_especialidad")
            .select("id,nombre,descripcion")
            .in_("id", ids)
            .order("id", desc=False)
            .execute()
        )
        return {"subespecialidades": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))