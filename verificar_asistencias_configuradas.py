"""
Script para verificar las asistencias configuradas
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, date, timedelta

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Variables de entorno no configuradas")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CHILE_OFFSET = timedelta(hours=-3)

def verificar_asistencias():
    fecha_objetivo = date(2025, 12, 9)
    
    print("\n" + "=" * 80)
    print("📊 VERIFICACIÓN DE ASISTENCIAS CONFIGURADAS")
    print("=" * 80)
    print(f"📅 Fecha: {fecha_objetivo}\n")
    
    # IDs de doctores
    doctores = [
        (7, "Victor Camero Gamboa", "AUSENTE"),
        (17, "Maxi Ovalle Oyarce", "ATRASO"),
        (22, "Antonio Cosela Mamaa", "ASISTIO"),
        (24, "Juan Rivas Lopez", "EN_TURNO"),
        (25, "Monica Oyarce Poblete", "ASISTIO"),
    ]
    
    doctor_ids = [d[0] for d in doctores]
    
    # Buscar horarios
    fecha_inicio = fecha_objetivo - timedelta(days=1)
    fecha_fin = fecha_objetivo + timedelta(days=1)
    
    horarios_response = supabase.from_("horarios_personal").select("usuario_sistema_id, inicio_bloque, finalizacion_bloque") \
        .in_("usuario_sistema_id", doctor_ids) \
        .gte("inicio_bloque", f"{fecha_inicio}T00:00:00") \
        .lte("inicio_bloque", f"{fecha_fin}T23:59:59") \
        .execute()
    
    # Agrupar horarios por doctor
    horarios_por_doctor = {}
    for h in horarios_response.data:
        inicio_utc = datetime.fromisoformat(h['inicio_bloque'].replace('Z', '+00:00'))
        inicio_chile = inicio_utc + CHILE_OFFSET
        
        if inicio_chile.date() == fecha_objetivo:
            doctor_id = h['usuario_sistema_id']
            if doctor_id not in horarios_por_doctor:
                horarios_por_doctor[doctor_id] = {
                    'inicio': h['inicio_bloque'],
                    'fin': h['finalizacion_bloque']
                }
    
    # Buscar asistencias
    asistencias_response = supabase.from_("asistencia").select("*") \
        .in_("usuario_sistema_id", doctor_ids) \
        .gte("inicio_turno", f"{fecha_inicio}T00:00:00") \
        .lte("inicio_turno", f"{fecha_fin}T23:59:59") \
        .execute()
    
    asistencias_por_doctor = {}
    for a in asistencias_response.data:
        inicio_utc = datetime.fromisoformat(a['inicio_turno'].replace('Z', '+00:00'))
        inicio_chile = inicio_utc + CHILE_OFFSET
        
        if inicio_chile.date() == fecha_objetivo:
            asistencias_por_doctor[a['usuario_sistema_id']] = a
    
    # Mostrar resultados
    from datetime import timezone as tz
    ahora_utc = datetime.now(tz.utc)
    
    for doctor_id, nombre, estado_esperado in doctores:
        print(f"\n👤 {nombre} (ID: {doctor_id})")
        print(f"   Estado esperado: {estado_esperado}")
        print("   " + "-" * 76)
        
        # Horario programado
        horario = horarios_por_doctor.get(doctor_id)
        if horario:
            inicio_prog = datetime.fromisoformat(horario['inicio'].replace('Z', '+00:00')) + CHILE_OFFSET
            fin_prog = datetime.fromisoformat(horario['fin'].replace('Z', '+00:00')) + CHILE_OFFSET
            print(f"   ⏰ Horario programado: {inicio_prog.strftime('%H:%M')} - {fin_prog.strftime('%H:%M')}")
        else:
            print(f"   ⚠️  Sin horario programado")
        
        # Asistencia
        asistencia = asistencias_por_doctor.get(doctor_id)
        if asistencia:
            inicio_real = datetime.fromisoformat(asistencia['inicio_turno'].replace('Z', '+00:00')) + CHILE_OFFSET
            fin_str = asistencia.get('finalizacion_turno')
            
            print(f"   ✅ Marca entrada: {inicio_real.strftime('%H:%M')}")
            
            if fin_str:
                fin_real = datetime.fromisoformat(fin_str.replace('Z', '+00:00')) + CHILE_OFFSET
                print(f"   ✅ Marca salida: {fin_real.strftime('%H:%M')}")
                
                # Calcular minutos trabajados
                minutos = int((fin_real - inicio_real).total_seconds() / 60)
                horas = minutos / 60
                print(f"   ⏱️  Horas trabajadas: {horas:.1f}h ({minutos} min)")
            else:
                print(f"   🔄 Marca salida: EN TURNO (sin salida)")
            
            # Calcular atraso
            if horario:
                inicio_prog = datetime.fromisoformat(horario['inicio'].replace('Z', '+00:00')) + CHILE_OFFSET
                atraso = max(0, int((inicio_real - inicio_prog).total_seconds() / 60))
                if atraso > 0:
                    print(f"   ⚠️  Atraso: {atraso} minutos")
                else:
                    print(f"   ✅ Puntual (0 min atraso)")
        else:
            print(f"   ❌ Sin marca de asistencia (AUSENTE)")
    
    print("\n" + "=" * 80)
    print("✅ VERIFICACIÓN COMPLETADA")
    print("=" * 80)

if __name__ == "__main__":
    verificar_asistencias()
