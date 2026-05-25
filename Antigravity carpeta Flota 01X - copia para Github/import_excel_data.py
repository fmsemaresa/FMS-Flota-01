import os
import sys
import random
import datetime
import unicodedata
import openpyxl
from sqlalchemy import text

# Agregar el directorio raíz al path de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import init_db, get_session
from src.database.models import Vehicle, Driver, UsageRecord, vehicle_driver_association

def clean_text(val):
    if val is None:
        return ""
    return str(val).strip()

def strip_accents(text_str):
    text_str = clean_text(text_str)
    # Normalizar y quitar acentos
    normalized = unicodedata.normalize('NFD', text_str)
    cleaned = "".join(c for c in normalized if unicodedata.category(c) != 'Mn')
    # Reemplazar caracteres comunes
    cleaned = cleaned.replace("ñ", "n").replace("Ñ", "N")
    return cleaned

def clean_name_for_email(name):
    clean = strip_accents(name).lower()
    clean = "".join(c for c in clean if c.isalnum() or c in (" ", ".", "_", "-"))
    # Reemplazar espacios por puntos
    parts = [p for p in clean.split() if p]
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[-1]}@empresa.cl"
    elif parts:
        return f"{parts[0]}@empresa.cl"
    return "contacto@empresa.cl"

def calculate_dv(rut_num):
    reversed_digits = map(int, reversed(str(rut_num)))
    factors = [2, 3, 4, 5, 6, 7]
    s = sum(d * factors[i % 6] for i, d in enumerate(reversed_digits))
    r = 11 - (s % 11)
    if r == 11:
        return '0'
    elif r == 10:
        return 'K'
    else:
        return str(r)

def generate_rut(idx):
    # Genera un RUT único a partir de un índice secuencial
    base = 15234000 + idx
    dv = calculate_dv(base)
    # Formatear como XX.XXX.XXX-X
    base_str = str(base)
    formatted = f"{base_str[:2]}.{base_str[2:5]}.{base_str[5:8]}-{dv}"
    return formatted

def import_data():
    print("Iniciando la importación de datos desde el archivo Excel...")
    
    excel_path = os.path.join("DB vehiculos y conductores", "BD flota FMS 26 05 24 901.xlsx")
    if not os.path.exists(excel_path):
        print(f"Error: El archivo Excel no se encuentra en la ruta: {excel_path}")
        return False
    
    # Inicializar las tablas de la BD si no existen
    init_db()
    
    session = get_session()
    
    try:
        # 1. Limpiar datos antiguos
        print("Limpiando base de datos existente...")
        session.query(UsageRecord).delete()
        # Truncar tabla de asociación
        session.execute(text("DELETE FROM vehicle_driver_association"))
        session.query(Vehicle).delete()
        session.query(Driver).delete()
        session.commit()
        print("Base de datos limpia.")
        
        # Cargar libro de Excel
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        
        # 2. Importar Conductores de 'Hoja2'
        print("Importando conductores de la hoja 'Hoja2'...")
        ws_drivers = wb['Hoja2']
        drivers_rows = list(ws_drivers.iter_rows(values_only=True))[1:]
        
        driver_mapping = {} # conductor_name_upper -> Driver object
        imported_drivers_count = 0
        
        for idx, row in enumerate(drivers_rows, start=1):
            raw_name = row[0]
            raw_dept = row[1]
            
            if not raw_name:
                continue
                
            name = clean_text(raw_name)
            dept = clean_text(raw_dept)
            
            # Generar RUT, email y teléfono únicos
            rut = generate_rut(idx)
            email = clean_name_for_email(name)
            phone = f"+569{80000000 + idx}"
            
            # El rol será Conductor por defecto, o basado en algún patrón si quisiéramos
            driver = Driver(
                rut=rut,
                name=name,
                role="Conductor",
                email=email,
                phone=phone
            )
            session.add(driver)
            driver_mapping[name.upper()] = driver
            imported_drivers_count += 1
            
        print(f"Total conductores importados: {imported_drivers_count}")
        
        # 3. Importar Vehículos de 'BD flota '
        print("Importando vehículos de la hoja 'BD flota '...")
        ws_vehicles = wb['BD flota ']
        # Obtener los encabezados de las columnas para buscar por nombre
        headers = [clean_text(h) for h in next(ws_vehicles.iter_rows(max_row=1, values_only=True))]
        
        # Índices de columnas críticas
        try:
            col_plate = headers.index("Patente")
            col_type = headers.index("Tipo")
            col_brand = headers.index("Marca")
            col_model = headers.index("Modelo")
            col_status = headers.index("ESTADO")
            col_driver = headers.index("Conductor")
        except ValueError as ve:
            print(f"Error: No se encontraron las columnas necesarias en los encabezados: {headers}. Detalles: {ve}")
            return False
            
        vehicle_rows = list(ws_vehicles.iter_rows(values_only=True))[1:]
        imported_vehicles_count = 0
        assigned_drivers_count = 0
        
        for row in vehicle_rows:
            raw_plate = row[col_plate]
            if not raw_plate:
                continue
                
            plate = clean_text(raw_plate).upper().replace(" ", "").replace("-", "")
            # Formatear patente chilena (ej: ABCD12 o AB1234 o AB-CD-12)
            # Para visualización agregaremos guiones si es necesario, pero guardarla limpia e indexada es mejor.
            # Vamos a formatearla como XX-XX-XX o XX-XXX-X si tiene 6 letras o números.
            if len(plate) == 6:
                formatted_plate = f"{plate[:2]}-{plate[2:4]}-{plate[4:]}"
            else:
                formatted_plate = plate
                
            brand = clean_text(row[col_brand])
            model_name = clean_text(row[col_model])
            vehicle_type = clean_text(row[col_type])
            status = clean_text(row[col_status]).lower()
            raw_driver_name = row[col_driver]
            
            # Construir modelo
            if brand and model_name:
                full_model = f"{brand} {model_name}"
            elif brand:
                full_model = brand
            elif model_name:
                full_model = model_name
            else:
                full_model = "Modelo Desconocido"
                
            if not vehicle_type:
                vehicle_type = "Otro"
                
            # Determinar si está disponible/activo
            is_active = (status == "en flota")
            
            vehicle = Vehicle(
                plate=formatted_plate,
                model=full_model,
                vehicle_type=vehicle_type,
                is_active=is_active,
                status=status if status else "en flota"
            )
            
            # Asociar conductor si corresponde
            if raw_driver_name:
                driver_name = clean_text(raw_driver_name).upper()
                if driver_name in driver_mapping:
                    driver_obj = driver_mapping[driver_name]
                    vehicle.assigned_drivers.append(driver_obj)
                    assigned_drivers_count += 1
                    
            session.add(vehicle)
            imported_vehicles_count += 1
            
        print(f"Total vehículos importados: {imported_vehicles_count} (Activos: {session.query(Vehicle).filter(Vehicle.is_active == True).count()})")
        print(f"Total asignaciones de conductor-vehículo realizadas: {assigned_drivers_count}")
        
        session.commit()
        
        # 4. Crear registros de uso semilla (historial realista)
        print("Generando registros de uso semilla basados en la nueva base de datos...")
        active_vehicles = session.query(Vehicle).filter(Vehicle.is_active == True).all()
        all_drivers = session.query(Driver).all()
        
        if not active_vehicles or not all_drivers:
            print("Advertencia: No hay suficientes datos activos para generar historial.")
            return True
            
        # Generar historial de los últimos 5 días
        now = datetime.datetime.now()
        gps_coords_list = [
            "-33.4372,-70.6506", # Santiago Centro
            "-33.0456,-71.6133", # Valparaíso
            "-36.8201,-73.0443", # Concepción
            "-29.9027,-71.2520", # La Serena
            "-23.6509,-70.3975", # Antofagasta
            "-38.7397,-72.5901", # Temuco
            "-41.4689,-72.9411", # Puerto Montt
        ]
        
        # Crear unos 30 registros terminados
        records_to_add = []
        for i in range(30):
            days_ago = random.randint(1, 5)
            hours_ago = random.randint(1, 23)
            duration_minutes = random.randint(15, 300)
            
            start_time = now - datetime.timedelta(days=days_ago, hours=hours_ago)
            end_time = start_time + datetime.timedelta(minutes=duration_minutes)
            
            veh = random.choice(active_vehicles)
            # Buscar un conductor asignado a este vehículo, si no, uno aleatorio
            if veh.assigned_drivers:
                drv = random.choice(veh.assigned_drivers)
            else:
                drv = random.choice(all_drivers)
                
            start_gps = random.choice(gps_coords_list)
            # Modificar ligeramente las coordenadas para el fin
            lat, lon = map(float, start_gps.split(','))
            end_gps = f"{lat + random.uniform(-0.05, 0.05):.4f},{lon + random.uniform(-0.05, 0.05):.4f}"
            
            record = UsageRecord(
                vehicle_id=veh.id,
                driver_id=drv.id,
                start_time=start_time,
                end_time=end_time,
                start_gps=start_gps,
                end_gps=end_gps,
                status="completed"
            )
            records_to_add.append(record)
            
        # Crear 3 registros activos (en uso en este momento) con conductores y vehículos diferentes
        used_vehicles = set()
        used_drivers = set()
        
        active_records_count = 0
        for i in range(10): # intentar crear hasta 3
            if active_records_count >= 3:
                break
                
            veh = random.choice(active_vehicles)
            drv = random.choice(all_drivers)
            
            # Regla: vehículo debe tener conductores asignados, y no estar ocupado ni el driver ocupado
            if veh.id in used_vehicles or drv.id in used_drivers:
                continue
                
            start_time = now - datetime.timedelta(hours=random.randint(1, 3))
            start_gps = random.choice(gps_coords_list)
            
            record = UsageRecord(
                vehicle_id=veh.id,
                driver_id=drv.id,
                start_time=start_time,
                end_time=None,
                start_gps=start_gps,
                end_gps=None,
                status="active"
            )
            records_to_add.append(record)
            used_vehicles.add(veh.id)
            used_drivers.add(drv.id)
            active_records_count += 1
            
        session.bulk_save_objects(records_to_add)
        session.commit()
        print(f"Se crearon {len(records_to_add)} registros de uso semilla ({active_records_count} activos).")
        print("Importación finalizada con éxito.")
        return True
        
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error durante la importación: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = import_data()
    sys.exit(0 if success else 1)
