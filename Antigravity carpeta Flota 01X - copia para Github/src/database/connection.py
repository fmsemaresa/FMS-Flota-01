from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from src.config import DATABASE_URL
from src.database.models import Base

# Crear motor de base de datos (SQLite requiere check_same_thread=False)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

# Configurar fábricas de sesión
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    Base.metadata.create_all(engine)
    
    # Auto-sembrado automático si la base de datos está recién creada y vacía
    session = get_session()
    try:
        from src.database.models import Vehicle, Driver, UsageRecord
        if session.query(Vehicle).count() == 0:
            print("Base de datos vacía. Sembrando datos iniciales...")
            import datetime
            
            # 5 Vehículos de ejemplo
            v1 = Vehicle(plate="AB-CD-12", model="Toyota Hilux", vehicle_type="Camioneta")
            v2 = Vehicle(plate="EF-GH-34", model="Hyundai H-1", vehicle_type="Furgón")
            v3 = Vehicle(plate="JK-LM-56", model="Chevrolet Spark", vehicle_type="City Car")
            v4 = Vehicle(plate="NP-QR-78", model="Ford Ranger", vehicle_type="Camioneta")
            v5 = Vehicle(plate="ST-UV-90", model="Peugeot Partner", vehicle_type="Furgón")
            
            session.add_all([v1, v2, v3, v4, v5])
            session.commit()
            
            # 5 Conductores de ejemplo
            d1 = Driver(rut="12.345.678-9", name="Eduardo Maino", role="Conductor / Administrador", email="eduardo.maino@empresa.cl", phone="+56987654321")
            d2 = Driver(rut="15.678.901-2", name="Juan Pérez", role="Conductor", email="juan.perez@empresa.cl", phone="+56998877665")
            d3 = Driver(rut="18.234.567-8", name="María González", role="Conductora", email="maria.gonzalez@empresa.cl", phone="+56955443322")
            d4 = Driver(rut="10.987.654-3", name="Carlos Silva", role="Supervisor A", email="carlos.silva@empresa.cl", phone="+56944332211")
            d5 = Driver(rut="14.567.890-K", name="Ana Morales", role="Gerente", email="ana.morales@empresa.cl", phone="+56922110099")
            
            session.add_all([d1, d2, d3, d4, d5])
            session.commit()
            
            # Asignaciones
            v1.assigned_drivers.extend([d1, d2])
            v2.assigned_drivers.extend([d3, d4])
            v3.assigned_drivers.extend([d5])
            v4.assigned_drivers.extend([d1, d4])
            v5.assigned_drivers.extend([d2, d3])
            session.commit()
            
            # Registros históricos
            r1 = UsageRecord(
                vehicle_id=v1.id,
                driver_id=d1.id,
                start_time=datetime.datetime.now() - datetime.timedelta(days=1, hours=4),
                end_time=datetime.datetime.now() - datetime.timedelta(days=1, hours=2),
                start_gps="-33.450123,-70.665123",
                end_gps="-33.447890,-70.669812",
                status="completed"
            )
            r2 = UsageRecord(
                vehicle_id=v2.id,
                driver_id=d3.id,
                start_time=datetime.datetime.now() - datetime.timedelta(hours=6),
                end_time=datetime.datetime.now() - datetime.timedelta(hours=5, minutes=15),
                start_gps="-33.461234,-70.623456",
                end_gps="-33.458901,-70.634567",
                status="completed"
            )
            r3 = UsageRecord(
                vehicle_id=v5.id,
                driver_id=d2.id,
                start_time=datetime.datetime.now() - datetime.timedelta(hours=2),
                start_gps="-33.440234,-70.654321",
                status="active"
            )
            r4 = UsageRecord(
                vehicle_id=v4.id,
                driver_id=d4.id,
                start_time=datetime.datetime.now() - datetime.timedelta(hours=1),
                start_gps="-33.472890,-70.612019",
                status="active"
            )
            
            session.add_all([r1, r2, r3, r4])
            session.commit()
            print("Datos semilla sembrados automáticamente.")
    except Exception as e:
        print(f"Error al auto-sembrar base de datos: {e}")
    finally:
        session.close()

def get_session():
    """Devuelve una nueva sesión de base de datos."""
    return Session()
