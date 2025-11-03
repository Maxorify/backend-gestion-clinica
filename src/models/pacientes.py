from pydantic import BaseModel
from typing import Optional
from datetime import date

class Paciente(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    fecha_nacimiento: date
    sexo: str
    estado_civil: str
    rut: str
    direccion: str
    telefono: str
    correo: str
    ocupacion: str
    persona_responsable: Optional[str] = None
    alergias: Optional[str] = None
    prevencion_id: int

class Prevencion(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
