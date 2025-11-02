from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    redirect_url: Optional[str] = None

class UserData(BaseModel):
    id: int
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    email: str
    rol_id: int
    rol_nombre: str
    especialidad_id: Optional[int] = None
    especialidad_nombre: Optional[str] = None
