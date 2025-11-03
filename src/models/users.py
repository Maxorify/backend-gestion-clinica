from pydantic import BaseModel
from typing import List, Optional

class Usuario(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    rut: str
    email: str
    celular: str
    cel_secundario: Optional[str] = None
    direccion: str
    rol_id: int
    especialidad_id: Optional[str] = None  # Mantener para compatibilidad
    especialidades_ids: Optional[List[int]] = None  # Nueva: múltiples especialidades
    contraseña_temporal: Optional[str] = None  # Nueva: para crear doctores con clave temporal

class Rol(BaseModel):
    nombre: str
    descripcion: str    

class Especialidad(BaseModel):
    nombre: str
    descripcion: str


class SubEspecialidad(BaseModel):
    nombre: str
    descripcion: str

class VinculoEspSub(BaseModel):
    especialidad_id: int
    sub_especialidad_id: int    


class VinculoEspSubBatch(BaseModel):
    especialidad_id: int
    sub_especialidad_ids: List[int]    