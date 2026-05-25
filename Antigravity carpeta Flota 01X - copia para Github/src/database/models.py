from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Tabla intermedia de asignación de Conductores a Vehículos (Muchos a Muchos)
vehicle_driver_association = Table(
    'vehicle_driver_association',
    Base.metadata,
    Column('vehicle_id', Integer, ForeignKey('vehicles.id', ondelete="CASCADE"), primary_key=True),
    Column('driver_id', Integer, ForeignKey('drivers.id', ondelete="CASCADE"), primary_key=True)
)

class Vehicle(Base):
    __tablename__ = 'vehicles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plate = Column(String(50), unique=True, nullable=False, index=True) # Patente
    model = Column(String(100), nullable=False) # Ej: Toyota Hilux
    vehicle_type = Column(String(50), nullable=False) # Ej: Camioneta, Furgón
    is_active = Column(Boolean, default=True) # Si está disponible para operar
    status = Column(String(50), default="en flota") # Estado: en flota, a la venta, vendido y entregado
    
    # Relación de conductores asignados
    assigned_drivers = relationship('Driver', secondary=vehicle_driver_association, back_populates='assigned_vehicles')
    # Relación con los registros de uso
    usage_records = relationship('UsageRecord', back_populates='vehicle')

    def __repr__(self):
        return f"<Vehicle {self.plate} - {self.model}>"

class Driver(Base):
    __tablename__ = 'drivers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rut = Column(String(20), unique=True, nullable=False, index=True) # RUT identificador
    name = Column(String(100), nullable=False) # Nombre completo
    role = Column(String(50), default="Conductor") # Conductor, Supervisor A, Supervisor B, Jefatura, Gerente, Administrador de APP
    email = Column(String(100), nullable=True) # Correo para notificaciones
    phone = Column(String(20), nullable=True) # Teléfono para notificaciones SMS
    
    # Relación de vehículos asignados
    assigned_vehicles = relationship('Vehicle', secondary=vehicle_driver_association, back_populates='assigned_drivers')
    # Relación con los registros de uso
    usage_records = relationship('UsageRecord', back_populates='driver')

    def __repr__(self):
        return f"<Driver {self.name} - RUT: {self.rut}>"

class UsageRecord(Base):
    __tablename__ = 'usage_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), nullable=False)
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=False)
    
    start_time = Column(DateTime, nullable=False) # Fecha y hora de inicio de uso
    end_time = Column(DateTime, nullable=True) # Fecha y hora de término de uso
    
    start_gps = Column(String(100), nullable=True) # Coordenadas GPS inicio: "lat,lon"
    end_gps = Column(String(100), nullable=True) # Coordenadas GPS término
    
    status = Column(String(20), default="active") # "active" (en uso) o "completed" (terminado)
    
    # Relaciones
    vehicle = relationship('Vehicle', back_populates='usage_records')
    driver = relationship('Driver', back_populates='usage_records')

    def __repr__(self):
        return f"<UsageRecord Vehicle: {self.vehicle_id} Driver: {self.driver_id} Status: {self.status}>"

