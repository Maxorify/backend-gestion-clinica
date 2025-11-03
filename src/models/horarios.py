from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HorarioBloque(BaseModel):
    inicio_bloque: datetime
    finalizacion_bloque: datetime
    usuario_sistema_id: int

class CrearHorarioSemanal(BaseModel):
    usuario_sistema_id: int
    dia_semana: int  # 0=Lunes, 1=Martes, ..., 6=Domingo
    hora_inicio: str  # Formato "HH:MM"
    hora_fin: str  # Formato "HH:MM"
    duracion_bloque_minutos: int  # Duración de cada bloque (ej: 30 minutos)
    fecha_inicio: str  # Fecha desde la cual aplicar (YYYY-MM-DD)
    fecha_fin: Optional[str] = None  # Fecha hasta la cual aplicar (opcional)

class ActualizarHorario(BaseModel):
    inicio_bloque: datetime
    finalizacion_bloque: datetime
