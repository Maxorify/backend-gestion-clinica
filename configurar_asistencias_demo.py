"""
Script para configurar asistencias de demo para el 9-12-2025.
Este script identifica los doctores y prepara datos para mostrar diferentes estados.
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, date, time, timezone, timedelta

# Cargar variables de entorno
load_dotenv()

# Configurar Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Variables de entorno SUPABASE_URL y SUPABASE_KEY no configuradas")
    print("Por favor, crea un archivo .env con las credenciales de Supabase.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Timezone de Chile (UTC-3)
CHILE_OFFSET = timedelta(hours=-3)

def identificar_doctores():
    """Identifica los doctores que aparecen en la pantalla"""
    nombres_pantalla = [
        "Victor Camero Gamboa",
        "Antonio Cosela Mamaa", 
        "Maxi Ovalle Oyarce",
        "Juan Rivas Lopez",
        "Darwin Nuñez Felicevich",
        "Monica Oyarce Poblete"
    ]
    
    print("\n🔍 IDENTIFICANDO DOCTORES EN LA BASE DE DATOS...")
    print("=" * 80)
    
    # Buscar doctores con rol de doctor (rol_id = 2)
    response = supabase.from_("usuario_sistema").select("*").eq("rol_id", 2).execute()
    
    doctores_encontrados = []
    
    for doctor in response.data:
        nombre_completo = f"{doctor['nombre']} {doctor['apellido_paterno']} {doctor.get('apellido_materno', '')}".strip()
        
        # Verificar si el nombre está en la lista
        for nombre in nombres_pantalla:
            # Comparación flexible
            if nombre.lower() in nombre_completo.lower() or nombre_completo.lower() in nombre.lower():
                doctores_encontrados.append({
                    'id': doctor['id'],
                    'nombre': doctor['nombre'],
                    'apellido_paterno': doctor['apellido_paterno'],
                    'apellido_materno': doctor.get('apellido_materno'),
                    'nombre_completo': nombre_completo,
                    'rut': doctor.get('rut'),
                    'email': doctor.get('email')
                })
                print(f"✅ Encontrado: {nombre_completo} (ID: {doctor['id']})")
                break
    
    print(f"\n📊 Total doctores encontrados: {len(doctores_encontrados)}")
    return doctores_encontrados


def verificar_horarios_existentes(doctores, fecha_objetivo):
    """Verifica si existen horarios para los doctores en la fecha objetivo"""
    print(f"\n📅 VERIFICANDO HORARIOS PARA {fecha_objetivo}...")
    print("=" * 80)
    
    # Ampliar rango para cubrir todos los bloques
    fecha_inicio = fecha_objetivo - timedelta(days=1)
    fecha_fin = fecha_objetivo + timedelta(days=1)
    
    doctor_ids = [d['id'] for d in doctores]
    
    response = supabase.from_("horarios_personal").select("*") \
        .in_("usuario_sistema_id", doctor_ids) \
        .gte("inicio_bloque", f"{fecha_inicio}T00:00:00") \
        .lte("inicio_bloque", f"{fecha_fin}T23:59:59") \
        .execute()
    
    horarios_por_doctor = {}
    
    for horario in response.data:
        # Convertir a hora Chile (UTC-3)
        inicio_utc = datetime.fromisoformat(horario['inicio_bloque'].replace('Z', '+00:00'))
        inicio_chile = inicio_utc + CHILE_OFFSET
        
        if inicio_chile.date() == fecha_objetivo:
            doctor_id = horario['usuario_sistema_id']
            if doctor_id not in horarios_por_doctor:
                horarios_por_doctor[doctor_id] = []
            horarios_por_doctor[doctor_id].append(horario)
    
    for doctor in doctores:
        horarios = horarios_por_doctor.get(doctor['id'], [])
        if horarios:
            print(f"✅ {doctor['nombre_completo']}: {len(horarios)} bloques programados")
            for h in horarios[:2]:  # Mostrar solo los primeros 2
                inicio = datetime.fromisoformat(h['inicio_bloque'].replace('Z', '+00:00')) + CHILE_OFFSET
                fin = datetime.fromisoformat(h['finalizacion_bloque'].replace('Z', '+00:00')) + CHILE_OFFSET
                print(f"   └─ {inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')}")
        else:
            print(f"⚠️  {doctor['nombre_completo']}: SIN horarios programados")
    
    return horarios_por_doctor


def verificar_asistencias_existentes(doctores, fecha_objetivo):
    """Verifica si existen asistencias para los doctores en la fecha objetivo"""
    print(f"\n🕐 VERIFICANDO ASISTENCIAS PARA {fecha_objetivo}...")
    print("=" * 80)
    
    fecha_inicio = fecha_objetivo - timedelta(days=1)
    fecha_fin = fecha_objetivo + timedelta(days=1)
    
    doctor_ids = [d['id'] for d in doctores]
    
    response = supabase.from_("asistencia").select("*") \
        .in_("usuario_sistema_id", doctor_ids) \
        .gte("inicio_turno", f"{fecha_inicio}T00:00:00") \
        .lte("inicio_turno", f"{fecha_fin}T23:59:59") \
        .execute()
    
    asistencias_por_doctor = {}
    
    for asistencia in response.data:
        inicio_utc = datetime.fromisoformat(asistencia['inicio_turno'].replace('Z', '+00:00'))
        inicio_chile = inicio_utc + CHILE_OFFSET
        
        if inicio_chile.date() == fecha_objetivo:
            doctor_id = asistencia['usuario_sistema_id']
            asistencias_por_doctor[doctor_id] = asistencia
    
    for doctor in doctores:
        asistencia = asistencias_por_doctor.get(doctor['id'])
        if asistencia:
            inicio = datetime.fromisoformat(asistencia['inicio_turno'].replace('Z', '+00:00')) + CHILE_OFFSET
            fin_str = asistencia.get('finalizacion_turno')
            fin = datetime.fromisoformat(fin_str.replace('Z', '+00:00')) + CHILE_OFFSET if fin_str else None
            
            print(f"✅ {doctor['nombre_completo']}: Asistencia registrada")
            print(f"   └─ Entrada: {inicio.strftime('%H:%M')}")
            if fin:
                print(f"   └─ Salida: {fin.strftime('%H:%M')}")
            else:
                print(f"   └─ Salida: SIN REGISTRAR (en turno)")
        else:
            print(f"⚠️  {doctor['nombre_completo']}: SIN asistencia registrada")
    
    return asistencias_por_doctor


if __name__ == "__main__":
    
    fecha_objetivo = date(2025, 12, 9)
    
    print("\n" + "=" * 80)
    print("🎯 ANÁLISIS DE CONFIGURACIÓN DE ASISTENCIAS PARA DEMO")
    print("=" * 80)
    
    # Paso 1: Identificar doctores
    doctores = identificar_doctores()
    
    if len(doctores) < 6:
        print(f"\n⚠️  ADVERTENCIA: Solo se encontraron {len(doctores)} de 6 doctores esperados")
    
    # Paso 2: Verificar horarios
    horarios = verificar_horarios_existentes(doctores, fecha_objetivo)
    
    # Paso 3: Verificar asistencias
    asistencias = verificar_asistencias_existentes(doctores, fecha_objetivo)
    
    print("\n" + "=" * 80)
    print("📋 RESUMEN Y PLAN DE ACCIÓN")
    print("=" * 80)
    
    print(f"\n🎯 OBJETIVO: Configurar 6 doctores con diferentes estados para el {fecha_objetivo}")
    print("\nEstados objetivo:")
    print("  1. AUSENTE - Doctor no marcó entrada ni salida")
    print("  2. ATRASO - Doctor marcó entrada tarde")
    print("  3. ASISTIO (OK) - Doctor marcó entrada y salida a tiempo")
    print("  4. EN_TURNO - Doctor marcó entrada pero aún no salida")
    print("  5. ASISTIO - Otro doctor que completó turno")
    print("  6. AUSENTE - Otro doctor ausente")
    
    print("\n📊 Doctores identificados:")
    for i, doctor in enumerate(doctores, 1):
        tiene_horario = doctor['id'] in horarios
        tiene_asistencia = doctor['id'] in asistencias
        print(f"  {i}. {doctor['nombre_completo']} (ID: {doctor['id']})")
        print(f"     ├─ Horario programado: {'✅ SÍ' if tiene_horario else '❌ NO'}")
        print(f"     └─ Asistencia registrada: {'✅ SÍ' if tiene_asistencia else '❌ NO'}")
    
    print("\n" + "=" * 80)
    print("⚠️  ANTES DE CONTINUAR:")
    print("=" * 80)
    print("1. Verifica que todos los doctores tengan horarios programados para el 9-12-2025")
    print("2. Si faltan horarios, créalos primero con el script correspondiente")
    print("3. Este script modificará/creará registros de asistencia según sea necesario")
    print("\n¿Deseas continuar con la configuración? (El script actual solo analiza)")
