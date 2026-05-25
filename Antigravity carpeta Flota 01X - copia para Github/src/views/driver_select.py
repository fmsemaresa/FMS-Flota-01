import datetime
import flet as ft
from src.database.connection import get_session
from src.database.models import Vehicle, Driver, UsageRecord
from src.utils.gps import get_current_gps
from src.utils.notifications import send_supervisor_email

def get_driver_select_view(page: ft.Page, on_navigate, vehicle_plate: str):
    """Devuelve la vista de selección de conductor asignado para un vehículo."""
    session = get_session()
    
    vehicle = session.query(Vehicle).filter(Vehicle.plate == vehicle_plate).first()
    if not vehicle:
        session.close()
        return ft.View(route="/", controls=[ft.Text("Vehículo no encontrado.")])
        
    # Obtener conductores asignados a este vehículo
    drivers = vehicle.assigned_drivers
    
    # Si no hay conductores asignados específicamente, cargamos todos los conductores de la DB
    if not drivers:
        drivers = session.query(Driver).all()
        
    session.close()

    # Opciones para el Dropdown
    dropdown_options = [ft.dropdown.Option(d.rut, f"{d.name} ({d.role})") for d in drivers]

    driver_dropdown = ft.Dropdown(
        label="Identificación de Conductor",
        hint_text="Seleccione conductor...",
        options=dropdown_options,
        width=320,
        border_color="#3F51B5",
        focused_border_color="#009688",
        border_radius=10,
        color=ft.Colors.WHITE,
    )
    
    error_text = ft.Text(value="", color=ft.Colors.RED_400, size=14, weight=ft.FontWeight.BOLD)

    def handle_confirm(e):
        selected_rut = driver_dropdown.value
        if not selected_rut:
            error_text.value = "Por favor, seleccione un conductor."
            page.update()
            return
            
        error_text.value = ""
        # Desactivar el botón inmediatamente para evitar clics múltiples
        e.control.disabled = True
        page.update()
        
        db_sess = get_session()
        try:
            # Obtener conductor y vehículo frescos
            db_driver = db_sess.query(Driver).filter(Driver.rut == selected_rut).first()
            db_vehicle = db_sess.query(Vehicle).filter(Vehicle.plate == vehicle_plate).first()
            
            # 1. Validar que el vehículo no tenga ya una sesión activa
            existing_vehicle_active = db_sess.query(UsageRecord).filter(
                UsageRecord.vehicle_id == db_vehicle.id,
                UsageRecord.status == "active"
            ).first()
            
            if existing_vehicle_active:
                error_text.value = "El vehículo ya tiene una sesión de uso activa."
                e.control.disabled = False
                page.update()
                return
                
            # 2. Validar que el conductor no tenga ya una sesión activa
            existing_driver_active = db_sess.query(UsageRecord).filter(
                UsageRecord.driver_id == db_driver.id,
                UsageRecord.status == "active"
            ).first()
            
            if existing_driver_active:
                error_text.value = f"Ya tienes una sesión activa en el vehículo {existing_driver_active.vehicle.plate}."
                e.control.disabled = False
                page.update()
                return

            # Generar ubicación GPS inicial
            start_gps = get_current_gps()
            now = datetime.datetime.now()
            
            # Crear registro de uso
            new_record = UsageRecord(
                vehicle_id=db_vehicle.id,
                driver_id=db_driver.id,
                start_time=now,
                start_gps=start_gps,
                status="active"
            )
            
            db_sess.add(new_record)
            db_sess.commit()
            
            # Notificar al supervisor vía email simulado
            send_supervisor_email(
                supervisor_name="Carlos Silva (Supervisor)",
                supervisor_email="carlos.silva@empresa.cl",
                driver_name=db_driver.name,
                vehicle_plate=db_vehicle.plate,
                action="inicio"
            )
            
            # Crear y abrir un SnackBar (Toast) de confirmación premium
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Sesión iniciada con éxito para {db_driver.name}", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.GREEN_700,
                duration=4000,
                show_close_icon=True
            )
            page.snack_bar.open = True
            
            # Reemplazar el contenido de la tarjeta con la pantalla de éxito nativa
            card_container.content = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=60, color=ft.Colors.GREEN_400),
                    ft.Text("¡Uso Iniciado!", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                    ft.Container(height=10),
                    ft.Text(
                        "Su sesión se inició correctamente, ya puede usar este vehículo.",
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.WHITE,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Conductor: {db_driver.name}", size=14, color=ft.Colors.WHITE),
                            ft.Text(f"Vehículo: {vehicle_plate} ({db_vehicle.model})", size=14, color=ft.Colors.WHITE),
                            ft.Text(f"Ubicación GPS: {start_gps}", size=12, color=ft.Colors.BLUE_200, italic=True),
                            ft.Text(f"Fecha/Hora: {now.strftime('%Y-%m-%d %H:%M:%S')}", size=12, color=ft.Colors.GREY_400),
                        ], spacing=6),
                        padding=15,
                        bgcolor="#252538",
                        border_radius=10,
                        width=320
                    ),
                    ft.Container(height=15),
                    ft.ElevatedButton(
                        content=ft.Text("Aceptar / Volver al Inicio", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                        width=320,
                        height=50,
                        style=ft.ButtonStyle(
                            bgcolor="#3F51B5",
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=lambda _: on_navigate("/")
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15
            )
            page.update()
            
        except Exception as ex:
            db_sess.rollback()
            error_text.value = f"Error al registrar sesión: {ex}"
            e.control.disabled = False
            page.update()
        finally:
            db_sess.close()

    card_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.PERSON_PIN, size=50, color="#3F51B5"),
                ft.Text("Inicio de Uso", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text(f"Vehículo: {vehicle.plate} ({vehicle.model})", size=14, color=ft.Colors.GREY_300),
                ft.Divider(height=20, color="#2E2E3E"),
                
                ft.Text("Conductores Asignados:", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE),
                driver_dropdown,
                error_text,
                
                ft.Container(height=10),
                
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.WHITE),
                            ft.Text("Confirmar e Iniciar Uso", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    width=320,
                    height=50,
                    style=ft.ButtonStyle(
                        bgcolor="#3F51B5",
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=handle_confirm
                ),
                
                ft.Divider(height=20, color="#2E2E3E"),
                
                ft.TextButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CLOSE, color=ft.Colors.GREY_400),
                            ft.Text("Cancelar y Volver", color=ft.Colors.GREY_400)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    on_click=lambda _: on_navigate(f"/status/vehicle/{vehicle_plate}")
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15
        ),
        padding=30,
        bgcolor="#1E1E2E",
        border_radius=20,
        shadow=ft.BoxShadow(
            blur_radius=20,
            color="black",
            offset=ft.Offset(0, 10),
            spread_radius=1
        ),
        width=380,
    )

    return ft.View(
        route=f"/driver_select/{vehicle_plate}",
        controls=[card_container],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        bgcolor="#0F0F1A",
        padding=10
    )
