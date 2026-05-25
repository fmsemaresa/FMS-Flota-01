import datetime
from sqlalchemy import and_
import flet as ft
from src.database.connection import get_session
from src.database.models import Vehicle, Driver, UsageRecord
from src.utils.gps import get_current_gps
from src.utils.notifications import send_supervisor_email, send_driver_sms

def get_status_view(page: ft.Page, on_navigate, entry_type: str, identifier: str):
    """Devuelve la vista de estado basada en un RUT o una Patente."""
    session = get_session()
    
    # Contenedor para inyectar la interfaz dinámica
    content_area = ft.Column(spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    # Obtener ubicación simulada para las operaciones
    current_coords = get_current_gps()

    def show_alert_dialog(title, text, on_confirm=None):
        def close_dialog(e):
            page.dialog.open = False
            page.update()
            if on_confirm:
                on_confirm()

        dialog = ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Text(text),
            actions=[
                ft.TextButton(
                    content=ft.Text("Entendido", weight=ft.FontWeight.BOLD),
                    on_click=close_dialog
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def terminate_usage(record_id, callback_route=None, callback_msg=None):
        """Cierra una sesión de uso activa."""
        db_sess = get_session()
        record = db_sess.query(UsageRecord).filter(UsageRecord.id == record_id).first()
        if record:
            record.end_time = datetime.datetime.now()
            record.end_gps = current_coords
            record.status = "completed"
            
            # Enviar notificación simulada al supervisor
            send_supervisor_email(
                supervisor_name="Carlos Silva (Supervisor)",
                supervisor_email="carlos.silva@empresa.cl",
                driver_name=record.driver.name,
                vehicle_plate=record.vehicle.plate,
                action="término"
            )
            
            db_sess.commit()
            db_sess.close()
            
            if callback_msg:
                show_alert_dialog("Sesión Finalizada", callback_msg, lambda: on_navigate(callback_route or "/"))
            else:
                on_navigate(callback_route or "/")
        else:
            db_sess.close()

    # =========================================================================
    # CASO DE USO 1: INGRESO POR PATENTE DE VEHÍCULO
    # =========================================================================
    if entry_type == "vehicle":
        vehicle = session.query(Vehicle).filter(Vehicle.plate == identifier).first()
        if not vehicle:
            session.close()
            return ft.View(route="/", controls=[ft.Text("Vehículo no encontrado.")])
            
        if not vehicle.is_active:
            content_area.controls = [
                ft.Icon(ft.Icons.BLOCK, size=50, color=ft.Colors.RED_400),
                ft.Text("VEHÍCULO INACTIVO", size=22, color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Patente: {vehicle.plate}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"Modelo: {vehicle.model}", size=16, color=ft.Colors.GREY_300),
                        ft.Text(f"Tipo: {vehicle.vehicle_type}", size=14, color=ft.Colors.GREY_400),
                        ft.Text(f"Estado de Flota: {vehicle.status.upper() if vehicle.status else 'INACTIVO'}", size=14, color=ft.Colors.RED_200, weight=ft.FontWeight.BOLD),
                    ], spacing=8),
                    padding=20,
                    bgcolor="#252538",
                    border_radius=12,
                    width=320,
                ),
                ft.Text("Este vehículo no se encuentra disponible para operaciones.", size=12, color=ft.Colors.GREY_400, text_align=ft.TextAlign.CENTER)
            ]
            session.close()
            card_container = ft.Container(
                content=ft.Column(
                    controls=[
                        content_area,
                        ft.Divider(height=20, color="#2E2E3E"),
                        ft.TextButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.ARROW_BACK, color=ft.Colors.GREY_400),
                                    ft.Text("Volver al Inicio", color=ft.Colors.GREY_400)
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=10
                            ),
                            on_click=lambda _: on_navigate("/")
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
                route=f"/status/vehicle/{identifier}",
                controls=[card_container],
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                bgcolor="#0F0F1A",
                padding=10
            )

        # Comprobar si tiene algún uso activo
        active_record = session.query(UsageRecord).filter(
            and_(UsageRecord.vehicle_id == vehicle.id, UsageRecord.status == "active")
        ).first()
        
        if not active_record:
            # ----------------------------------------------------
            # VEHÍCULO DISPONIBLE
            # ----------------------------------------------------
            # Mostrar datos del vehículo e inicio de uso
            content_area.controls = [
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=50, color=ft.Colors.GREEN_400),
                ft.Text(f"VEHÍCULO DISPONIBLE", size=22, color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Patente: {vehicle.plate}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"Modelo: {vehicle.model}", size=16, color=ft.Colors.GREY_300),
                        ft.Text(f"Tipo: {vehicle.vehicle_type}", size=14, color=ft.Colors.GREY_400),
                        ft.Text(f"Ubicación GPS: {current_coords}", size=12, color=ft.Colors.BLUE_200, italic=True),
                    ], spacing=8),
                    padding=20,
                    bgcolor="#252538",
                    border_radius=12,
                    width=320,
                ),
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.WHITE),
                            ft.Text("Iniciar Período de Uso", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
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
                    on_click=lambda _: on_navigate(f"/driver_select/{vehicle.plate}")
                )
            ]
        else:
            # ----------------------------------------------------
            # VEHÍCULO EN USO POR OTRO CONDUCTOR
            # ----------------------------------------------------
            # El vehículo tiene un uso activo. Mostrar quién lo tiene.
            active_driver = active_record.driver
            
            def handle_force_new_period(e):
                # Flujo: Otro RUT tiene uso activo. Se notifica al conductor anterior y al supervisor.
                # 1. Enviar SMS al conductor anterior
                send_driver_sms(
                    driver_name=active_driver.name,
                    driver_phone=active_driver.phone or "+56999999999",
                    message=f"Hola {active_driver.name}. Tu sesión activa en el vehículo [{vehicle.plate}] ha sido cerrada por otro conductor. Por favor verifica."
                )
                
                # 2. Terminar la sesión anterior programáticamente
                terminate_usage(
                    record_id=active_record.id,
                    callback_route=f"/driver_select/{vehicle.plate}",
                    callback_msg=f"El conductor anterior ({active_driver.name}) ha sido notificado para que cierre su uso. Iniciando nuevo período de uso."
                )

            content_area.controls = [
                ft.Icon(ft.Icons.WARNING_AMBER, size=50, color=ft.Colors.AMBER_400),
                ft.Text(f"VEHÍCULO EN USO", size=22, color=ft.Colors.AMBER_400, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Patente: {vehicle.plate}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"Conductor Actual: {active_driver.name}", size=16, color=ft.Colors.WHITE),
                        ft.Text(f"RUT Conductor: {active_driver.rut}", size=14, color=ft.Colors.GREY_300),
                        ft.Text(f"Inicio: {active_record.start_time.strftime('%H:%M:%S (%Y-%m-%d)')}", size=12, color=ft.Colors.GREY_400),
                    ], spacing=8),
                    padding=20,
                    bgcolor="#252538",
                    border_radius=12,
                    width=320,
                ),
                
                ft.Text("¿Es usted el conductor actual?", size=14, color=ft.Colors.GREY_300),
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.STOP, color=ft.Colors.WHITE),
                            ft.Text("Terminar Mi Uso", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    width=320,
                    height=50,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_500,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=lambda _: terminate_usage(
                        active_record.id, 
                        "/", 
                        f"Tu sesión de uso del vehículo {vehicle.plate} ha sido finalizada con éxito."
                    )
                ),
                
                ft.Divider(height=10, color="#2E2E3E"),
                
                ft.Text("Si otro conductor olvidó cerrar la sesión:", size=12, color=ft.Colors.GREY_400),
                ft.OutlinedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.TRANSFER_WITHIN_A_STATION, color=ft.Colors.AMBER_400),
                            ft.Text("Cerrar Uso Anterior", color=ft.Colors.AMBER_400, weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    width=320,
                    height=50,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=handle_force_new_period
                )
            ]

    # =========================================================================
    # CASO DE USO 2: INGRESO POR RUT DE CONDUCTOR
    # =========================================================================
    elif entry_type == "driver":
        driver = session.query(Driver).filter(Driver.rut == identifier).first()
        if not driver:
            session.close()
            return ft.View(route="/", controls=[ft.Text("Conductor no encontrado.")])
            
        # Buscar si el conductor tiene algún uso activo (en cualquier vehículo)
        active_record = session.query(UsageRecord).filter(
            and_(UsageRecord.driver_id == driver.id, UsageRecord.status == "active")
        ).first()
        
        if not active_record:
            # ----------------------------------------------------
            # CONDUCTOR SIN USOS ACTIVOS
            # ----------------------------------------------------
            # El RUT ingresado no tiene usos activos. Debe elegir un vehículo.
            assigned_vehicles = driver.assigned_vehicles
            
            # Si no hay asignados, listamos todos los disponibles
            if not assigned_vehicles:
                assigned_vehicles = session.query(Vehicle).filter(Vehicle.is_active == True).all()

            dropdown_options = [ft.dropdown.Option(v.plate, f"{v.plate} ({v.model})") for v in assigned_vehicles]
            
            vehicle_dropdown = ft.Dropdown(
                label="Seleccione el Vehículo",
                options=dropdown_options,
                width=320,
                border_color="#3F51B5",
                border_radius=10,
                color=ft.Colors.WHITE
            )
            
            def handle_vehicle_submit(e):
                selected_plate = vehicle_dropdown.value
                if not selected_plate:
                    show_alert_dialog("Falta selección", "Por favor seleccione un vehículo para iniciar.")
                    return
                
                # Desactivar el botón inmediatamente para evitar clics múltiples
                e.control.disabled = True
                page.update()
                
                db_sess = get_session()
                try:
                    # Obtener vehículo y conductor frescos
                    db_vehicle = db_sess.query(Vehicle).filter(Vehicle.plate == selected_plate).first()
                    db_driver = db_sess.query(Driver).filter(Driver.id == driver.id).first()
                    
                    # 1. Verificar si el vehículo ya está ocupado por otro conductor
                    active_record = db_sess.query(UsageRecord).filter(
                        and_(UsageRecord.vehicle_id == db_vehicle.id, UsageRecord.status == "active")
                    ).first()
                    
                    if active_record:
                        # Si está ocupado, navegamos a la pantalla de estado del vehículo
                        # para que decida si quiere cerrar el uso anterior
                        e.control.disabled = False
                        page.update()
                        on_navigate(f"/status/vehicle/{selected_plate}")
                        return
                        
                    # 2. Verificar si el conductor ya tiene otra sesión activa
                    existing_driver_active = db_sess.query(UsageRecord).filter(
                        UsageRecord.driver_id == db_driver.id,
                        UsageRecord.status == "active"
                    ).first()
                    
                    if existing_driver_active:
                        show_alert_dialog("Conductor Ocupado", f"Ya tienes una sesión activa en el vehículo {existing_driver_active.vehicle.plate}.")
                        e.control.disabled = False
                        page.update()
                        return
                        
                    # 3. Si está disponible, creamos la sesión inmediatamente
                    start_gps = get_current_gps()
                    now = datetime.datetime.now()
                    
                    new_rec = UsageRecord(
                        vehicle_id=db_vehicle.id,
                        driver_id=db_driver.id,
                        start_time=now,
                        start_gps=start_gps,
                        status="active"
                    )
                    
                    db_sess.add(new_rec)
                    db_sess.commit()
                    
                    # Notificar al supervisor
                    send_supervisor_email(
                        supervisor_name="Carlos Silva (Supervisor)",
                        supervisor_email="carlos.silva@empresa.cl",
                        driver_name=db_driver.name,
                        vehicle_plate=db_vehicle.plate,
                        action="inicio"
                    )
                    
                    # Mostrar SnackBar de éxito
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Sesión iniciada con éxito para {db_driver.name}", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.GREEN_700,
                        duration=4000,
                        show_close_icon=True
                    )
                    page.snack_bar.open = True
                    
                    # Reemplazar el contenido completo de la tarjeta por la pantalla de éxito
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
                                    ft.Text(f"Vehículo: {selected_plate} ({db_vehicle.model})", size=14, color=ft.Colors.WHITE),
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
                    show_alert_dialog("Error", f"No se pudo iniciar la sesión: {ex}")
                    e.control.disabled = False
                    page.update()
                finally:
                    db_sess.close()

            content_area.controls = [
                ft.Icon(ft.Icons.PERSON, size=50, color="#009688"),
                ft.Text(f"Hola, {driver.name}", size=22, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                ft.Text(f"Rol: {driver.role}", size=14, color=ft.Colors.GREY_400),
                ft.Text("No tienes ningún vehículo activo actualmente.", size=14, color=ft.Colors.GREY_300),
                
                ft.Container(height=10),
                
                ft.Text("Iniciar uso en un vehículo:", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE),
                vehicle_dropdown,
                
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
                        bgcolor="#009688",
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=handle_vehicle_submit
                )
            ]
        else:
            # ----------------------------------------------------
            # CONDUCTOR CON USO ACTIVO
            # ----------------------------------------------------
            # El conductor tiene una sesión activa.
            vehicle_in_use = active_record.vehicle
            
            def confirm_close_active(e):
                # Cerrar sesión de uso
                terminate_usage(
                    active_record.id, 
                    "/", 
                    f"Su sesión de uso del vehículo {vehicle_in_use.plate} ha sido terminada."
                )

            content_area.controls = [
                ft.Icon(ft.Icons.WATCH_LATER, size=50, color=ft.Colors.AMBER_400),
                ft.Text(f"SESIÓN EN CURSO", size=22, color=ft.Colors.AMBER_400, weight=ft.FontWeight.BOLD),
                ft.Text(f"Conductor: {driver.name}", size=16, color=ft.Colors.WHITE),
                
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Vehículo Activo: {vehicle_in_use.plate}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"Modelo: {vehicle_in_use.model}", size=14, color=ft.Colors.GREY_300),
                        ft.Text(f"Inicio: {active_record.start_time.strftime('%H:%M:%S (%Y-%m-%d)')}", size=12, color=ft.Colors.GREY_400),
                    ], spacing=8),
                    padding=20,
                    bgcolor="#252538",
                    border_radius=12,
                    width=320,
                ),
                
                ft.Text("¿Desea seguir usando este vehículo?", size=14, color=ft.Colors.GREY_300),
                
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CHECK, color=ft.Colors.WHITE),
                            ft.Text("Sí, seguir usando", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
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
                    on_click=lambda _: on_navigate("/")
                ),
                
                ft.OutlinedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.STOP, color=ft.Colors.RED_400),
                            ft.Text("No, terminar uso", color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    width=320,
                    height=50,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=confirm_close_active
                )
            ]

    # Cerrar la sesión de la base de datos
    session.close()

    # Contenedor de la Tarjeta Principal
    card_container = ft.Container(
        content=ft.Column(
            controls=[
                content_area,
                ft.Divider(height=20, color="#2E2E3E"),
                ft.TextButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ARROW_BACK, color=ft.Colors.GREY_400),
                            ft.Text("Volver al Inicio", color=ft.Colors.GREY_400)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    on_click=lambda _: on_navigate("/")
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
        route=f"/status/{entry_type}/{identifier}",
        controls=[card_container],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        bgcolor="#0F0F1A",
        padding=10
    )
