"""
Script para configurar asistencias de demo para el 9-12-2025.
Este script creará registros de asistencia con diferentes estados.
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
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Timezone de Chile (UTC-3)
CHILE_OFFSET = timedelta(hours=-3)

def chile_to_utc(fecha_chile: datetime) -> str:
    """Convierte datetime de Chile a UTC en formato ISO"""
    utc_time = fecha_chile - CHILE_OFFSET
    return utc_time.replace(tzinfo=timezone.utc).isoformat()

def eliminar_asistencias_existentes(doctor_ids, fecha_objetivo):
    """Elimina asistencias existentes para los doctores en la fecha objetivo"""
    print("\n🗑️  ELIMINANDO ASISTENCIAS EXISTENTES...")
    print("=" * 80)
    
    fecha_inicio = fecha_objetivo - timedelta(days=1)
    fecha_fin = fecha_objetivo + timedelta(days=1)
    
    # Buscar asistencias existentes
    response = supabase.from_("asistencia").select("id, usuario_sistema_id") \
        .in_("usuario_sistema_id", doctor_ids) \
        .gte("inicio_turno", f"{fecha_inicio}T00:00:00") \
        .lte("inicio_turno", f"{fecha_fin}T23:59:59") \
        .execute()
    
    if response.data:
        print(f"Encontradas {len(response.data)} asistencias existentes")
        for asist in response.data:
            result = supabase.from_("asistencia").delete().eq("id", asist['id']).execute()
            print(f"  ✅ Eliminada asistencia ID {asist['id']} del doctor {asist['usuario_sistema_id']}")
    else:
        print("No hay asistencias existentes para eliminar")
    
    return len(response.data) if response.data else 0

def crear_asistencia(doctor_id, nombre_doctor, fecha_base, hora_entrada, hora_salida=None):
    """Crea un registro de asistencia"""
    # Construir datetime en hora Chile
    entrada_chile = datetime.combine(fecha_base, hora_entrada)
    
    # Convertir a UTC
    entrada_utc = chile_to_utc(entrada_chile)
    
    data = {
        "usuario_sistema_id": doctor_id,
        "inicio_turno": entrada_utc
    }
    
    if hora_salida:
        salida_chile = datetime.combine(fecha_base, hora_salida)
        salida_utc = chile_to_utc(salida_chile)
        data["finalizacion_turno"] = salida_utc
    
    try:
        result = supabase.from_("asistencia").insert(data).execute()
        
        if hora_salida:
            print(f"  ✅ {nombre_doctor}: Entrada {hora_entrada.strftime('%H:%M')} - Salida {hora_salida.strftime('%H:%M')}")
        else:
            print(f"  ✅ {nombre_doctor}: Entrada {hora_entrada.strftime('%H:%M')} - EN TURNO (sin salida)")
        
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"  ❌ Error al crear asistencia para {nombre_doctor}: {str(e)}")
        return None

def configurar_asistencias_demo(fecha_objetivo):
    """Configura las asistencias de demo"""
    print("\n" + "=" * 80)
    print("🎬 CONFIGURANDO ASISTENCIAS DE DEMO")
    print("=" * 80)
    print(f"📅 Fecha objetivo: {fecha_objetivo}")
    print()
    
    # Definición de doctores y sus configuraciones
    configuraciones = [
        # (ID, Nombre, Hora entrada, Hora salida, Estado esperado)
        (7, "Victor Camero Gamboa", None, None, "AUSENTE"),
        (17, "Maxi Ovalle Oyarce", time(8, 35), time(18, 0), "ATRASO"),
        (22, "Antonio Cosela Mamaa", time(8, 0), time(18, 0), "ASISTIO"),
        (24, "Juan Rivas Lopez", time(8, 0), None, "EN_TURNO"),
        (25, "Monica Oyarce Poblete", time(12, 0), time(16, 0), "ASISTIO"),
    ]
    
    doctor_ids = [c[0] for c in configuraciones]
    
    # Paso 1: Eliminar asistencias existentes
    eliminadas = eliminar_asistencias_existentes(doctor_ids, fecha_objetivo)
    
    # Paso 2: Crear nuevas asistencias
    print("\n➕ CREANDO NUEVAS ASISTENCIAS...")
    print("=" * 80)
    
    creadas = 0
    for doctor_id, nombre, hora_entrada, hora_salida, estado_esperado in configuraciones:
        if hora_entrada is None:
            print(f"  ⏭️  {nombre}: NO SE CREA (estado {estado_esperado})")
        else:
            result = crear_asistencia(doctor_id, nombre, fecha_objetivo, hora_entrada, hora_salida)
            if result:
                creadas += 1
    
    # Paso 3: Verificar resultados
    print("\n✅ VERIFICANDO RESULTADOS...")
    print("=" * 80)
    
    fecha_inicio = fecha_objetivo - timedelta(days=1)
    fecha_fin = fecha_objetivo + timedelta(days=1)
    
    response = supabase.from_("asistencia").select("*") \
        .in_("usuario_sistema_id", doctor_ids) \
        .gte("inicio_turno", f"{fecha_inicio}T00:00:00") \
        .lte("inicio_turno", f"{fecha_fin}T23:59:59") \
        .execute()
    
    asistencias_verificadas = {}
    for asist in (response.data or []):
        inicio_utc = datetime.fromisoformat(asist['inicio_turno'].replace('Z', '+00:00'))
        inicio_chile = inicio_utc + CHILE_OFFSET
        
        if inicio_chile.date() == fecha_objetivo:
            asistencias_verificadas[asist['usuario_sistema_id']] = asist
    
    print("\n📊 RESUMEN FINAL:")
    print("=" * 80)
    for doctor_id, nombre, hora_entrada, hora_salida, estado_esperado in configuraciones:
        asist = asistencias_verificadas.get(doctor_id)
        
        if asist:
            inicio = datetime.fromisoformat(asist['inicio_turno'].replace('Z', '+00:00')) + CHILE_OFFSET
            fin_str = asist.get('finalizacion_turno')
            fin = datetime.fromisoformat(fin_str.replace('Z', '+00:00')) + CHILE_OFFSET if fin_str else None
            
            print(f"✅ {nombre}:")
            print(f"   ├─ Entrada: {inicio.strftime('%H:%M')}")
            if fin:
                print(f"   ├─ Salida: {fin.strftime('%H:%M')}")
            else:
                print(f"   ├─ Salida: SIN REGISTRAR")
            print(f"   └─ Estado esperado: {estado_esperado}")
        else:
            if estado_esperado == "AUSENTE":
                print(f"✅ {nombre}:")
                print(f"   └─ SIN ASISTENCIA (estado: {estado_esperado}) ✓")
            else:
                print(f"❌ {nombre}:")
                print(f"   └─ ERROR: Debería tener asistencia pero no se encontró")
    
    print("\n" + "=" * 80)
    print(f"📊 ESTADÍSTICAS:")
    print(f"   ├─ Asistencias eliminadas: {eliminadas}")
    print(f"   ├─ Asistencias creadas: {creadas}")
    print(f"   └─ Asistencias verificadas: {len(asistencias_verificadas)}")
    print("=" * 80)
    
    print("\n🎉 CONFIGURACIÓN COMPLETADA")
    print("\n💡 Ahora puedes:")
    print("   1. Llamar al endpoint /asistencia/turnos-trabajados?fecha=2025-12-09")
    print("   2. Ver los diferentes estados reflejados en el frontend")
    print("   3. Grabar tu video de demostración")

if __name__ == "__main__":
    fecha_objetivo = date(2025, 12, 9)
    configurar_asistencias_demo(fecha_objetivo)
