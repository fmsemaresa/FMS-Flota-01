import datetime
from src.config import NOTIFICATIONS_LOG

def _log_notification(channel, recipient, subject, body):
    """Escribe la notificación en un archivo de log para simulación."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = (
        f"==================================================\n"
        f"[{timestamp}] NOTIFICACIÓN ENVIADA POR {channel.upper()}\n"
        f"Destinatario: {recipient}\n"
        f"Asunto/Detalle: {subject}\n"
        f"Mensaje: {body}\n"
        f"==================================================\n\n"
    )
    print(f"[Notificación Sim] {channel.upper()} a {recipient}: {subject} - {body}")
    
    with open(NOTIFICATIONS_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)

def send_supervisor_email(supervisor_name, supervisor_email, driver_name, vehicle_plate, action):
    """Simula el envío de un correo al supervisor cuando se inicia o termina el uso."""
    subject = f"Alerta FMS: {action.upper()} de Uso - Patente {vehicle_plate}"
    body = (
        f"Estimado/a {supervisor_name},\n\n"
        f"Le informamos que el conductor {driver_name} ha realizado el {action.upper()} de uso "
        f"para el vehículo con patente [{vehicle_plate}].\n"
        f"Esta acción fue registrada exitosamente en el sistema de gestión de flota."
    )
    _log_notification("Email", supervisor_email, subject, body)

def send_driver_sms(driver_name, driver_phone, message):
    """Simula el envío de un mensaje de texto (SMS) al teléfono del conductor."""
    subject = f"Mensaje SMS a {driver_name}"
    _log_notification("SMS", driver_phone, subject, message)
