from fastapi import APIRouter, HTTPException
from src.models.pacientes import Paciente, Prevencion
from src.utils.supabase import supabase_client
import re

patient_router = APIRouter(tags=["Gestión de Pacientes"], prefix="/Pacientes")

def limpiar_rut(rut: str) -> str:
    """
    Limpia el RUT removiendo puntos y guiones.
    Ejemplo: '20.952.457-0' -> '209524570'
    """
    return re.sub(r'[.\-]', '', rut)

@patient_router.post("/crear-paciente")
async def crear_paciente(paciente: Paciente):
    """
    Crea un nuevo paciente en la tabla paciente.
    El RUT debe ser único.
    """
    try:
        # Limpiar RUT antes de guardar
        rut_limpio = limpiar_rut(paciente.rut)

        # Verificar si ya existe el RUT
        existe = (
            supabase_client
            .table("paciente")
            .select("id")
            .eq("rut", rut_limpio)
            .execute()
        )
        if existe.data:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un paciente con el RUT '{paciente.rut}'."
            )

        # Insertar nuevo paciente
        nuevo = (
            supabase_client
            .table("paciente")
            .insert({
                "nombre": paciente.nombre,
                "apellido_paterno": paciente.apellido_paterno,
                "apellido_materno": paciente.apellido_materno,
                "fecha_nacimiento": str(paciente.fecha_nacimiento),
                "sexo": paciente.sexo,
                "estado_civil": paciente.estado_civil,
                "rut": rut_limpio,
                "direccion": paciente.direccion,
                "telefono": paciente.telefono,
                "correo": paciente.correo,
                "ocupacion": paciente.ocupacion,
                "persona_responsable": paciente.persona_responsable,
                "alergias": paciente.alergias,
                "prevencion_id": paciente.prevencion_id
            })
            .execute()
        )

        if not nuevo.data:
            raise HTTPException(status_code=500, detail="No se pudo crear el paciente.")

        return {
            "mensaje": f"Paciente '{paciente.nombre} {paciente.apellido_paterno}' creado correctamente.",
            "paciente": nuevo.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@patient_router.put("/modificar-paciente/{paciente_id}")
async def modificar_paciente(paciente_id: int, paciente: Paciente):
    """
    Modifica los datos de un paciente existente.
    """
    try:
        # Verificar existencia
        existe = (
            supabase_client
            .table("paciente")
            .select("id")
            .eq("id", paciente_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail="No existe el paciente.")

        # Limpiar RUT
        rut_limpio = limpiar_rut(paciente.rut)

        # Verificar duplicado de RUT (en otro paciente)
        duplicado = (
            supabase_client
            .table("paciente")
            .select("id")
            .eq("rut", rut_limpio)
            .neq("id", paciente_id)
            .execute()
        )
        if duplicado.data:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe otro paciente con el RUT '{paciente.rut}'."
            )

        # Actualizar datos
        actualizado = (
            supabase_client
            .table("paciente")
            .update({
                "nombre": paciente.nombre,
                "apellido_paterno": paciente.apellido_paterno,
                "apellido_materno": paciente.apellido_materno,
                "fecha_nacimiento": str(paciente.fecha_nacimiento),
                "sexo": paciente.sexo,
                "estado_civil": paciente.estado_civil,
                "rut": rut_limpio,
                "direccion": paciente.direccion,
                "telefono": paciente.telefono,
                "correo": paciente.correo,
                "ocupacion": paciente.ocupacion,
                "persona_responsable": paciente.persona_responsable,
                "alergias": paciente.alergias,
                "prevencion_id": paciente.prevencion_id
            })
            .eq("id", paciente_id)
            .execute()
        )

        if not actualizado.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el paciente.")

        return {
            "mensaje": f"Paciente '{paciente.nombre} {paciente.apellido_paterno}' modificado correctamente.",
            "paciente": actualizado.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@patient_router.delete("/eliminar-paciente/{paciente_id}")
async def eliminar_paciente(paciente_id: int):
    """
    Elimina un paciente por su ID.
    """
    try:
        # Verificar existencia
        existe = (
            supabase_client
            .table("paciente")
            .select("id, nombre, apellido_paterno")
            .eq("id", paciente_id)
            .execute()
        )
        if not existe.data:
            raise HTTPException(status_code=404, detail="No existe el paciente.")

        nombre_completo = f"{existe.data[0]['nombre']} {existe.data[0]['apellido_paterno']}"

        # Eliminar paciente
        eliminado = (
            supabase_client
            .table("paciente")
            .delete()
            .eq("id", paciente_id)
            .execute()
        )

        if not eliminado.data:
            raise HTTPException(status_code=500, detail="No se pudo eliminar el paciente.")

        return {"mensaje": f"Paciente '{nombre_completo}' eliminado correctamente."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@patient_router.get("/listar-pacientes")
async def listar_pacientes():
    """
    Devuelve todos los pacientes con su información de prevención.
    """
    try:
        res = (
            supabase_client
            .table("paciente")
            .select("*, prevencion(id, nombre, descripcion)")
            .order("id", desc=False)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="No hay pacientes registrados.")

        return {"pacientes": res.data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@patient_router.get("/listar-prevenciones")
async def listar_prevenciones():
    """
    Devuelve todas las prevenciones disponibles (Fonasa, Isapre, etc.).
    """
    try:
        res = (
            supabase_client
            .table("prevencion")
            .select("*")
            .order("id", desc=False)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="No hay prevenciones registradas.")

        return {"prevenciones": res.data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@patient_router.post("/crear-prevencion")
async def crear_prevencion(prevencion: Prevencion):
    """
    Crea una nueva prevención (Fonasa, Isapre, etc.).
    """
    try:
        # Verificar si ya existe
        existe = (
            supabase_client
            .table("prevencion")
            .select("id")
            .eq("nombre", prevencion.nombre)
            .execute()
        )
        if existe.data:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe la prevención '{prevencion.nombre}'."
            )

        # Insertar nueva prevención
        nueva = (
            supabase_client
            .table("prevencion")
            .insert({
                "nombre": prevencion.nombre,
                "descripcion": prevencion.descripcion
            })
            .execute()
        )

        if not nueva.data:
            raise HTTPException(status_code=500, detail="No se pudo crear la prevención.")

        return {
            "mensaje": f"Prevención '{prevencion.nombre}' creada correctamente.",
            "prevencion": nueva.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
