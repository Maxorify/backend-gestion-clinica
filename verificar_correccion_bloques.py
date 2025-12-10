"""
Script para verificar que la corrección funcione correctamente
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Variables de entorno no configuradas")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def verificar_correccion():
    print("\n" + "=" * 80)
    print("✅ VERIFICANDO CORRECCIÓN DEL ENDPOINT")
    print("=" * 80)
    
    fecha_busqueda = "2025-12-09"
    doctor_id = 15  # Darwin Nuñez
    
    fecha_inicio_dt = datetime.fromisoformat(f"{fecha_busqueda}T00:00:00")
    fecha_fin_dt = datetime.fromisoformat(f"{fecha_busqueda}T23:59:59")
    
    # Obtener horarios del doctor
    horarios = supabase.from_("horarios_personal").select(
        "id, inicio_bloque, finalizacion_bloque, usuario_sistema_id"
    ).eq("usuario_sistema_id", doctor_id).lte(
        "inicio_bloque", fecha_fin_dt.isoformat()
    ).gte("finalizacion_bloque", fecha_inicio_dt.isoformat()).order("inicio_bloque", desc=False).execute()
    
    print(f"\n📊 Total de horarios del doctor: {len(horarios.data)}")
    
    # Obtener citas del doctor
    citas_doctor = supabase.from_("cita_medica").select(
        "id, fecha_atencion, doctor_id"
    ).eq("doctor_id", doctor_id).gte(
        "fecha_atencion", fecha_inicio_dt.isoformat()
    ).lte("fecha_atencion", fecha_fin_dt.isoformat()).execute()
    
    print(f"📊 Total de citas del doctor: {len(citas_doctor.data)}\n")
    
    # Simular la lógica CORREGIDA del endpoint
    horarios_ocupados = set()
    
    print("🔍 PROCESANDO CITAS CON LÓGICA CORREGIDA:\n")
    
    for cita in (citas_doctor.data or []):
        # Obtener el estado ACTUAL (más reciente)
        estado_response = supabase.from_("estado").select(
            "estado"
        ).eq("cita_medica_id", cita["id"]).order("id", desc=True).limit(1).execute()
        
        estado_actual = None
        if estado_response.data:
            estado_actual = estado_response.data[0].get("estado")
        
        fecha_cita = datetime.fromisoformat(cita["fecha_atencion"].replace('Z', '+00:00'))
        
        print(f"   Cita ID {cita['id']}: {fecha_cita.strftime('%H:%M')} - Estado: {estado_actual}")
        
        # Ignorar citas canceladas
        if estado_actual == "Cancelada":
            print(f"      ✅ IGNORADA (cancelada) - Libera el bloque")
            continue
        
        print(f"      ⚠️  OCUPA un bloque")
        
        # Verificar qué horario ocupa
        for horario in horarios.data:
            inicio = datetime.fromisoformat(horario["inicio_bloque"].replace('Z', '+00:00'))
            fin = datetime.fromisoformat(horario["finalizacion_bloque"].replace('Z', '+00:00'))
            
            if inicio <= fecha_cita < fin:
                horarios_ocupados.add(horario["id"])
                hora_bloque = inicio.strftime('%H:%M')
                print(f"      └─ Ocupa bloque de las {hora_bloque}")
                break
    
    # Filtrar horarios disponibles
    horarios_disponibles = [
        h for h in horarios.data
        if h["id"] not in horarios_ocupados
    ]
    
    print(f"\n" + "=" * 80)
    print("📊 RESULTADO FINAL:")
    print("=" * 80)
    print(f"   ├─ Total horarios: {len(horarios.data)}")
    print(f"   ├─ Horarios ocupados: {len(horarios_ocupados)}")
    print(f"   └─ Horarios disponibles: {len(horarios_disponibles)}")
    
    print(f"\n📅 HORARIOS DISPONIBLES (primeros 5):")
    for h in horarios_disponibles[:5]:
        inicio = datetime.fromisoformat(h["inicio_bloque"].replace('Z', '+00:00'))
        fin = datetime.fromisoformat(h["finalizacion_bloque"].replace('Z', '+00:00'))
        print(f"   ✅ {inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')} (ID: {h['id']})")
    
    # Verificar específicamente el bloque de 17:30 (20:30 en UTC)
    print(f"\n🎯 VERIFICACIÓN ESPECÍFICA - Bloque de las 17:30:")
    bloque_1730_encontrado = False
    for h in horarios_disponibles:
        inicio = datetime.fromisoformat(h["inicio_bloque"].replace('Z', '+00:00'))
        hora_chile = inicio.hour - 3  # UTC-3 para Chile
        minuto_chile = inicio.minute
        
        if hora_chile == 17 and minuto_chile == 30:
            bloque_1730_encontrado = True
            print(f"   ✅ DISPONIBLE - Bloque ID {h['id']}")
            break
    
    if not bloque_1730_encontrado:
        print(f"   ❌ NO DISPONIBLE - El bloque sigue ocupado")
    
    print("\n" + "=" * 80)
    
    if bloque_1730_encontrado:
        print("✅ CORRECCIÓN EXITOSA - El bloque se liberó correctamente")
    else:
        print("⚠️  PROBLEMA - El bloque NO se liberó")
    
    print("=" * 80)

if __name__ == "__main__":
    verificar_correccion()
