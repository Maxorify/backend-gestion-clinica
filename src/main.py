from fastapi.middleware.cors import CORSMiddleware
from src.utils.supabase import supabase_client
from fastapi import FastAPI
from src.routers.user_administration import user_router
from src.routers.doctor_administration import doctor_router
from src.routers.patient_administration import patient_router
from src.routers.appointment_administration import appointment_router
from src.routers.schedule_administration import schedule_router
from src.routers.auth import auth_router
import os



app = FastAPI()

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(doctor_router)
app.include_router(patient_router)
app.include_router(appointment_router)
app.include_router(schedule_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def inicio() -> dict:
    return {"message": "Gestion de horarios médicos,",
            "Database": "Supabase",
            "Framework": "FastAPI",
            "Version": "0.0.1",
            "Autor": "Max Ovalle"}


@app.get("/connection")
async def test_connection():
    if supabase_client:
        return {"status": "success", "message": "Cliente inicializado correctamente"}
    else:
        return {"status": "error", "message": "Cliente no está inicializado"}
