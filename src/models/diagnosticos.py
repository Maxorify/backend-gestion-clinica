from pydantic import BaseModel
from typing import Optional

class Diagnostico(BaseModel):
    nombre_enfermedad: str
    descripcion_enfermedad: Optional[str] = None
