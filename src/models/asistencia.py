from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RegistroAsistencia(BaseModel):
    usuario_sistema_id: int
    inicio_turno: datetime
    finalizacion_turno: Optional[datetime] = None

class ActualizarAsistencia(BaseModel):
    inicio_turno: Optional[datetime] = None
    finalizacion_turno: Optional[datetime] = None
