from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from src.utils.supabase import supabase_client

settings_router = APIRouter(tags=["Configuración del Sistema"], prefix="/Configuracion")

class ConfiguracionBase(BaseModel):
    clave: str
    valor: Optional[str] = None
    tipo: str = "texto"
    categoria: str = "general"
    descripcion: Optional[str] = None

class ActualizarConfiguracion(BaseModel):
    valor: str

@settings_router.get("/listar")
async def listar_configuraciones(categoria: Optional[str] = None):
    """
    Lista todas las configuraciones del sistema, opcionalmente filtradas por categoría.
    """
    try:
        query = supabase_client.table("configuracion_sistema").select("*")
        
        if categoria:
            query = query.eq("categoria", categoria)
        
        resultado = query.order("categoria").order("clave").execute()
        
        return {
            "total": len(resultado.data) if resultado.data else 0,
            "configuraciones": resultado.data or []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@settings_router.get("/obtener/{clave}")
async def obtener_configuracion(clave: str):
    """
    Obtiene una configuración específica por su clave.
    """
    try:
        resultado = (
            supabase_client
            .table("configuracion_sistema")
            .select("*")
            .eq("clave", clave)
            .execute()
        )
        
        if not resultado.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe la configuración con clave '{clave}'."
            )
        
        return resultado.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@settings_router.put("/actualizar/{clave}")
async def actualizar_configuracion(clave: str, datos: ActualizarConfiguracion):
    """
    Actualiza el valor de una configuración existente.
    """
    try:
        # Verificar que existe
        existe = (
            supabase_client
            .table("configuracion_sistema")
            .select("id, clave")
            .eq("clave", clave)
            .execute()
        )
        
        if not existe.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe la configuración con clave '{clave}'."
            )
        
        # Actualizar valor
        resultado = (
            supabase_client
            .table("configuracion_sistema")
            .update({"valor": datos.valor})
            .eq("clave", clave)
            .execute()
        )
        
        if not resultado.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar la configuración.")
        
        return {
            "mensaje": "Configuración actualizada correctamente.",
            "configuracion": resultado.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@settings_router.post("/crear")
async def crear_configuracion(config: ConfiguracionBase):
    """
    Crea una nueva configuración del sistema.
    """
    try:
        # Verificar que no existe
        existe = (
            supabase_client
            .table("configuracion_sistema")
            .select("id")
            .eq("clave", config.clave)
            .execute()
        )
        
        if existe.data:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe una configuración con la clave '{config.clave}'."
            )
        
        # Crear nueva configuración
        nuevo = {
            "clave": config.clave,
            "valor": config.valor,
            "tipo": config.tipo,
            "categoria": config.categoria,
            "descripcion": config.descripcion
        }
        
        resultado = (
            supabase_client
            .table("configuracion_sistema")
            .insert(nuevo)
            .execute()
        )
        
        if not resultado.data:
            raise HTTPException(status_code=500, detail="No se pudo crear la configuración.")
        
        return {
            "mensaje": "Configuración creada correctamente.",
            "configuracion": resultado.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@settings_router.put("/actualizar-multiple")
async def actualizar_multiple_configuraciones(configuraciones: List[dict]):
    """
    Actualiza múltiples configuraciones de una vez.
    Espera una lista de objetos con { clave, valor }
    """
    try:
        actualizados = []
        errores = []
        
        for config in configuraciones:
            try:
                clave = config.get("clave")
                valor = config.get("valor")
                
                if not clave:
                    errores.append({"clave": "unknown", "error": "Clave no proporcionada"})
                    continue
                
                # Actualizar
                resultado = (
                    supabase_client
                    .table("configuracion_sistema")
                    .update({"valor": valor})
                    .eq("clave", clave)
                    .execute()
                )
                
                if resultado.data:
                    actualizados.append(resultado.data[0])
                else:
                    errores.append({"clave": clave, "error": "No se pudo actualizar"})
                    
            except Exception as e:
                errores.append({"clave": config.get("clave", "unknown"), "error": str(e)})
        
        return {
            "mensaje": f"Se actualizaron {len(actualizados)} configuraciones correctamente.",
            "actualizados": actualizados,
            "errores": errores if errores else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
