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
            
        driver_id = driver.id
        driver_name = driver.name
        
        # Buscar si el conductor tiene algún uso activo
        driver_active_record = session.query(UsageRecord).filter(
            and_(UsageRecord.driver_id == driver_id, UsageRecord.status == "active")
        ).first()
            
        # Definir diálogos de confirmación
        def show_confirm_dialog(title, text, on_confirm):
            def handle_yes(e):
                page.dialog.open = False
                page.update()
                on_confirm()
                
            def handle_no(e):
                page.dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                title=ft.Text(title, weight=ft.FontWeight.BOLD),
                content=ft.Text(text),
                actions=[
                    ft.TextButton(content=ft.Text("Cancelar", color=ft.Colors.GREY_400), on_click=handle_no),
                    ft.TextButton(content=ft.Text("Confirmar", weight=ft.FontWeight.BOLD), on_click=handle_yes)
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.dialog = dialog
            dialog.open = True
            page.update()

        def show_success_screen(driver_name_val, plate, model, title, desc):
            content_area.controls = [
                ft.Icon(ft.Icons.CHECK_CIRCLE, size=60, color=ft.Colors.GREEN_400),
                ft.Text(title, size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                ft.Container(height=10),
                ft.Text(
                    desc,
                    size=14,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.WHITE,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Conductor: {driver_name_val}", size=14, color=ft.Colors.WHITE),
                        ft.Text(f"Vehículo: {plate} ({model})", size=14, color=ft.Colors.WHITE),
                        ft.Text(f"Ubicación GPS: {current_coords}", size=12, color=ft.Colors.BLUE_200, italic=True),
                        ft.Text(f"Fecha/Hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", size=12, color=ft.Colors.GREY_400),
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
            ]
            page.update()

        # Acción 1: Activar un vehículo
        def handle_activate(plate_val):
            plate_val = plate_val.strip().upper().replace(" ", "")
            if len(plate_val) == 6 and "-" not in plate_val:
                plate_val = f"{plate_val[:2]}-{plate_val[2:4]}-{plate_val[4:]}"
                
            if not plate_val:
                show_alert_dialog("Falta patente", "Por favor ingrese una patente para activar.")
                return

            db_sess = get_session()
            try:
                db_driver = db_sess.query(Driver).filter(Driver.id == driver_id).first()
                db_vehicle = db_sess.query(Vehicle).filter(Vehicle.plate == plate_val).first()
                if not db_vehicle:
                    show_alert_dialog("Patente no registrada", "El vehículo ingresado no pertenece a la flota.")
                    return
                
                if not db_vehicle.is_active:
                    show_alert_dialog("VEHÍCULO INACTIVO", f"El vehículo {db_vehicle.plate} está inactivo ({db_vehicle.status}). No puede ser utilizado.")
                    return
                    
                # Comprobar si está ocupado por otro conductor
                other_active = db_sess.query(UsageRecord).filter(
                    and_(UsageRecord.vehicle_id == db_vehicle.id, UsageRecord.status == "active")
                ).first()
                
                if other_active:
                    other_driver_name = other_active.driver.name
                    other_driver_rut = other_active.driver.rut
                    other_driver_phone = other_active.driver.phone or "+56999999999"
                    other_active_id = other_active.id
                    target_vehicle_id = db_vehicle.id
                    target_vehicle_plate = db_vehicle.plate
                    target_vehicle_model = db_vehicle.model
                    
                    def confirm_take_over():
                        db_sess2 = get_session()
                        try:
                            db_act = db_sess2.query(UsageRecord).filter(UsageRecord.id == other_active_id).first()
                            
                            # Terminar sesión anterior
                            db_act.end_time = datetime.datetime.now()
                            db_act.end_gps = current_coords
                            db_act.status = "completed"
                            
                            # Notificar al conductor anterior
                            send_driver_sms(
                                driver_name=other_driver_name,
                                driver_phone=other_driver_phone,
                                message=f"Hola {other_driver_name}. Tu sesión activa en el vehículo [{target_vehicle_plate}] ha sido cerrada por otro conductor ({driver_name})."
                            )
                            
                            # Iniciar nueva sesión para el conductor actual
                            new_rec = UsageRecord(
                                vehicle_id=target_vehicle_id,
                                driver_id=driver_id,
                                start_time=datetime.datetime.now(),
                                start_gps=current_coords,
                                status="active"
                            )
                            db_sess2.add(new_rec)
                            db_sess2.commit()
                            
                            # Notificar supervisor
                            send_supervisor_email(
                                supervisor_name="Carlos Silva (Supervisor)",
                                supervisor_email="carlos.silva@empresa.cl",
                                driver_name=driver_name,
                                vehicle_plate=target_vehicle_plate,
                                action="inicio"
                            )
                            
                            show_success_screen(
                                driver_name, 
                                target_vehicle_plate, 
                                target_vehicle_model, 
                                "¡Activación Exitosa!", 
                                f"el vehiculo {target_vehicle_plate.replace('-', '')} estaba asignado a {other_driver_name}, pero ahora ha sido asignado a ti"
                            )
                        except Exception as ex:
                            db_sess2.rollback()
                            show_alert_dialog("Error", f"No se pudo completar la activación: {ex}")
                        finally:
                            db_sess2.close()
                    
                    show_confirm_dialog(
                        "Vehículo en Uso",
                        f"El vehículo [{target_vehicle_plate}] está en uso por {other_driver_name} ({other_driver_rut}).\n\nSi confirmas, se cerrará su uso anterior, se le enviará una notificación y se activará para ti.",
                        confirm_take_over
                    )
                else:
                    # Caso libre
                    new_rec = UsageRecord(
                        vehicle_id=db_vehicle.id,
                        driver_id=db_driver.id,
                        start_time=datetime.datetime.now(),
                        start_gps=current_coords,
                        status="active"
                    )
                    db_sess.add(new_rec)
                    db_sess.commit()
                    
                    # Notificar supervisor
                    send_supervisor_email(
                        supervisor_name="Carlos Silva (Supervisor)",
                        supervisor_email="carlos.silva@empresa.cl",
                        driver_name=db_driver.name,
                        vehicle_plate=db_vehicle.plate,
                        action="inicio"
                    )
                    
                    show_success_screen(db_driver.name, db_vehicle.plate, db_vehicle.model, "¡Activación Exitosa!", "Tu período de uso se ha iniciado correctamente.")
                    
            except Exception as ex:
                db_sess.rollback()
                show_alert_dialog("Error", f"No se pudo activar: {ex}")
            finally:
                db_sess.close()

        # Acción 2: Prolongar sesión actual
        def handle_prolong():
            db_sess = get_session()
            try:
                db_driver = db_sess.query(Driver).filter(Driver.id == driver_id).first()
                # Buscar el registro activo actual
                active_rec = db_sess.query(UsageRecord).filter(
                    and_(UsageRecord.driver_id == db_driver.id, UsageRecord.status == "active")
                ).first()
                
                if not active_rec:
                    show_alert_dialog("Error", "No se encontró tu sesión activa.")
                    return
                    
                vehicle_plate = active_rec.vehicle.plate
                vehicle_model = active_rec.vehicle.model
                vehicle_id = active_rec.vehicle_id
                
                # 1. Finalizar uso actual
                active_rec.end_time = datetime.datetime.now()
                active_rec.end_gps = current_coords
                active_rec.status = "completed"
                
                # 2. Iniciar nuevo uso (prolongación)
                new_rec = UsageRecord(
                    vehicle_id=vehicle_id,
                    driver_id=db_driver.id,
                    start_time=datetime.datetime.now(),
                    start_gps=current_coords,
                    status="active"
                )
                db_sess.add(new_rec)
                db_sess.commit()
                
                # Enviar notificación al supervisor
                send_supervisor_email(
                    supervisor_name="Carlos Silva (Supervisor)",
                    supervisor_email="carlos.silva@empresa.cl",
                    driver_name=db_driver.name,
                    vehicle_plate=vehicle_plate,
                    action="prolongación"
                )
                
                show_success_screen(db_driver.name, vehicle_plate, vehicle_model, "¡Prolongación Exitosa!", "Se registró el término del período anterior e inicio del prolongado en el historial.")
            except Exception as ex:
                db_sess.rollback()
                show_alert_dialog("Error", f"No se pudo prolongar: {ex}")
            finally:
                db_sess.close()

        # Acción 3: Cambiar de patente (cerrando la anterior)
        def handle_change_plate(new_plate_val):
            new_plate_val = new_plate_val.strip().upper().replace(" ", "")
            if len(new_plate_val) == 6 and "-" not in new_plate_val:
                new_plate_val = f"{new_plate_val[:2]}-{new_plate_val[2:4]}-{new_plate_val[4:]}"
                
            if not new_plate_val:
                show_alert_dialog("Falta patente", "Por favor ingrese la nueva patente.")
                return

            db_sess = get_session()
            try:
                db_driver = db_sess.query(Driver).filter(Driver.id == driver_id).first()
                db_vehicle = db_sess.query(Vehicle).filter(Vehicle.plate == new_plate_val).first()
                if not db_vehicle:
                    show_alert_dialog("Patente no registrada", "El vehículo ingresado no pertenece a la flota.")
                    return
                    
                if not db_vehicle.is_active:
                    show_alert_dialog("VEHÍCULO INACTIVO", f"El vehículo {db_vehicle.plate} está inactivo ({db_vehicle.status}). No puede ser utilizado.")
                    return
                    
                # Buscar el uso activo del conductor actual para cerrarlo
                active_rec = db_sess.query(UsageRecord).filter(
                    and_(UsageRecord.driver_id == db_driver.id, UsageRecord.status == "active")
                ).first()
                
                # Comprobar si el vehículo nuevo está en uso por otro conductor (Driver B)
                other_active = db_sess.query(UsageRecord).filter(
                    and_(UsageRecord.vehicle_id == db_vehicle.id, UsageRecord.status == "active")
                ).first()
                
                if other_active:
                    other_driver_name = other_active.driver.name
                    other_driver_rut = other_active.driver.rut
                    other_driver_phone = other_active.driver.phone or "+56999999999"
                    other_active_id = other_active.id
                    target_vehicle_id = db_vehicle.id
                    target_vehicle_plate = db_vehicle.plate
                    target_vehicle_model = db_vehicle.model
                    
                    active_rec_id = active_rec.id if active_rec else None
                    active_rec_plate = active_rec.vehicle.plate if (active_rec and active_rec.vehicle) else ""
                    
                    def confirm_take_over_and_change():
                        db_sess2 = get_session()
                        try:
                            # 1. Terminar sesión de Driver B
                            db_act_other = db_sess2.query(UsageRecord).filter(UsageRecord.id == other_active_id).first()
                            db_act_other.end_time = datetime.datetime.now()
                            db_act_other.end_gps = current_coords
                            db_act_other.status = "completed"
                            
                            # Notificar a Driver B
                            send_driver_sms(
                                driver_name=other_driver_name,
                                driver_phone=other_driver_phone,
                                message=f"Hola {other_driver_name}. Tu sesión activa en el vehículo [{target_vehicle_plate}] ha sido cerrada por otro conductor ({driver_name})."
                            )
                            
                            # 2. Terminar sesión de Driver A (actual) en vehículo anterior
                            if active_rec_id:
                                db_act_current = db_sess2.query(UsageRecord).filter(UsageRecord.id == active_rec_id).first()
                                db_act_current.end_time = datetime.datetime.now()
                                db_act_current.end_gps = current_coords
                                db_act_current.status = "completed"
                                
                                # Notificar supervisor del cierre anterior
                                send_supervisor_email(
                                    supervisor_name="Carlos Silva (Supervisor)",
                                    supervisor_email="carlos.silva@empresa.cl",
                                    driver_name=driver_name,
                                    vehicle_plate=active_rec_plate,
                                    action="término"
                                )
                            
                            # 3. Iniciar nueva sesión para Driver A (actual) en nuevo vehículo
                            new_rec = UsageRecord(
                                vehicle_id=target_vehicle_id,
                                driver_id=driver_id,
                                start_time=datetime.datetime.now(),
                                start_gps=current_coords,
                                status="active"
                            )
                            db_sess2.add(new_rec)
                            db_sess2.commit()
                            
                            # Notificar supervisor del inicio nuevo
                            send_supervisor_email(
                                supervisor_name="Carlos Silva (Supervisor)",
                                supervisor_email="carlos.silva@empresa.cl",
                                driver_name=driver_name,
                                vehicle_plate=target_vehicle_plate,
                                action="inicio"
                            )
                            
                            show_success_screen(
                                driver_name, 
                                target_vehicle_plate, 
                                target_vehicle_model, 
                                "¡Activación Exitosa!", 
                                f"Se cerró tu sesión anterior en el vehículo {active_rec_plate}. El vehículo {target_vehicle_plate.replace('-', '')} estaba asignado a {other_driver_name}, pero ahora ha sido asignado a ti."
                            )
                        except Exception as ex:
                            db_sess2.rollback()
                            show_alert_dialog("Error", f"No se pudo cambiar de vehículo: {ex}")
                        finally:
                            db_sess2.close()
                    
                    show_confirm_dialog(
                        "Vehículo en Uso",
                        f"El vehículo [{target_vehicle_plate}] está en uso por {other_driver_name} ({other_driver_rut}).\n\nSi confirmas, se cerrará su uso anterior, se le notificará y se cerrará tu uso activo actual en {active_rec_plate} para activar este nuevo vehículo.",
                        confirm_take_over_and_change
                    )
                else:
                    # Caso nuevo libre
                    # 1. Terminar sesión anterior
                    if active_rec:
                        db_act_current = db_sess.query(UsageRecord).filter(UsageRecord.id == active_rec.id).first()
                        db_act_current.end_time = datetime.datetime.now()
                        db_act_current.end_gps = current_coords
                        db_act_current.status = "completed"
                        
                        # Notificar supervisor del cierre anterior
                        send_supervisor_email(
                            supervisor_name="Carlos Silva (Supervisor)",
                            supervisor_email="carlos.silva@empresa.cl",
                            driver_name=db_driver.name,
                            vehicle_plate=active_rec.vehicle.plate,
                            action="término"
                        )
                        
                    # 2. Iniciar sesión nueva
                    new_rec = UsageRecord(
                        vehicle_id=db_vehicle.id,
                        driver_id=db_driver.id,
                        start_time=datetime.datetime.now(),
                        start_gps=current_coords,
                        status="active"
                    )
                    db_sess.add(new_rec)
                    db_sess.commit()
                    
                    # Notificar supervisor del inicio nuevo
                    send_supervisor_email(
                        supervisor_name="Carlos Silva (Supervisor)",
                        supervisor_email="carlos.silva@empresa.cl",
                        driver_name=db_driver.name,
                        vehicle_plate=db_vehicle.plate,
                        action="inicio"
                    )
                    
                    show_success_screen(
                        db_driver.name, 
                        db_vehicle.plate, 
                        db_vehicle.model, 
                        "¡Activación Exitosa!", 
                        f"Se cerró tu sesión anterior en {active_rec.vehicle.plate if active_rec else ''} e iniciaste un nuevo período de uso en {db_vehicle.plate}."
                    )
            except Exception as ex:
                db_sess.rollback()
                show_alert_dialog("Error", f"No se pudo cambiar de vehículo: {ex}")
            finally:
                db_sess.close()

        # Vistas secundarias dinámicas
        def show_no_active_session_view():
            patente_input = ft.TextField(
                label="Patente del Vehículo a Activar",
                hint_text="Ej: AB-CD-12",
                width=320,
                height=60,
                text_align=ft.TextAlign.CENTER,
                border_color="#3F51B5",
                focused_border_color="#009688",
                border_radius=12,
                color=ft.Colors.WHITE,
                focused_border_width=2,
            )
            
            def on_plate_change(e):
                val = e.control.value.upper().replace("-", "").replace(" ", "")
                if len(val) > 6:
                    val = val[:6]
                if len(val) == 6:
                    formatted = f"{val[:2]}-{val[2:4]}-{val[4:]}"
                    e.control.value = formatted
                else:
                    e.control.value = val
                page.update()
                
            patente_input.on_change = on_plate_change

            def simulate_qr_selection(e):
                patente_input.value = "SL-DS-66"
                page.update()

            content_area.controls = [
                ft.Icon(ft.Icons.PERSON, size=50, color="#009688"),
                ft.Text(f"Hola, {driver_name}", size=22, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                ft.Text("No tienes ningún vehículo activo actualmente.", size=14, color=ft.Colors.GREY_300),
                ft.Divider(height=10, color="#2E2E3E"),
                ft.Text("Ingresar Patente para Iniciar Uso", size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                patente_input,
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
                    on_click=lambda _: handle_activate(patente_input.value)
                ),
                ft.Text("O bien:", size=12, color=ft.Colors.GREY_500),
                ft.OutlinedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.QR_CODE_SCANNER, color="#009688"),
                            ft.Text("Simular QR (SL-DS-66)", color="#009688", weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    width=320,
                    height=50,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=simulate_qr_selection
                )
            ]
            page.update()

        def show_active_session_options_view():
            db_sess = get_session()
            fresh_record = db_sess.query(UsageRecord).filter(
                and_(UsageRecord.driver_id == driver_id, UsageRecord.status == "active")
            ).first()
            
            if not fresh_record:
                db_sess.close()
                show_no_active_session_view()
                return
                
            vehicle_plate = fresh_record.vehicle.plate
            vehicle_model = fresh_record.vehicle.model
            start_time_str = fresh_record.start_time.strftime('%H:%M:%S (%Y-%m-%d)')
            db_sess.close()
            
            content_area.controls = [
                ft.Icon(ft.Icons.WATCH_LATER, size=50, color=ft.Colors.AMBER_400),
                ft.Text("SESIÓN EN CURSO", size=22, color=ft.Colors.AMBER_400, weight=ft.FontWeight.BOLD),
                ft.Text(f"Hola, {driver_name}", size=16, color=ft.Colors.WHITE),
                
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Vehículo Activo: {vehicle_plate}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"Modelo: {vehicle_model}", size=14, color=ft.Colors.GREY_300),
                        ft.Text(f"Inicio: {start_time_str}", size=12, color=ft.Colors.GREY_400),
                    ], spacing=8),
                    padding=20,
                    bgcolor="#252538",
                    border_radius=12,
                    width=320,
                ),
                
                ft.Text("¿Qué desea hacer?", size=14, color=ft.Colors.GREY_300),
                
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.REPLAY, color=ft.Colors.WHITE),
                            ft.Text("Prolongar uso anterior", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
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
                    on_click=lambda _: handle_prolong()
                ),
                
                ft.OutlinedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ADD, color=ft.Colors.GREEN_400),
                            ft.Text("Activar una nueva patente", color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    width=320,
                    height=50,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=lambda _: show_enter_new_plate_view(vehicle_plate)
                )
            ]
            page.update()

        def show_enter_new_plate_view(old_plate):
            nueva_patente_input = ft.TextField(
                label="Nueva Patente a Activar",
                hint_text="Ej: AB-CD-12",
                width=320,
                height=60,
                text_align=ft.TextAlign.CENTER,
                border_color="#3F51B5",
                focused_border_color="#009688",
                border_radius=12,
                color=ft.Colors.WHITE,
                focused_border_width=2,
            )
            
            def on_plate_change(e):
                val = e.control.value.upper().replace("-", "").replace(" ", "")
                if len(val) > 6:
                    val = val[:6]
                if len(val) == 6:
                    formatted = f"{val[:2]}-{val[2:4]}-{val[4:]}"
                    e.control.value = formatted
                else:
                    e.control.value = val
                page.update()
                
            nueva_patente_input.on_change = on_plate_change

            def simulate_qr_selection(e):
                nueva_patente_input.value = "SL-DS-66"
                page.update()

            content_area.controls = [
                ft.Icon(ft.Icons.TRANSFER_WITHIN_A_STATION, size=50, color=ft.Colors.GREEN_400),
                ft.Text("Cambiar de Vehículo", size=22, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                ft.Text(f"Se cerrará el uso activo actual en {old_plate}.", size=12, color=ft.Colors.AMBER_400, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=10, color="#2E2E3E"),
                
                nueva_patente_input,
                
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.WHITE),
                            ft.Text("Confirmar Cambio y Activar", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
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
                    on_click=lambda _: handle_change_plate(nueva_patente_input.value)
                ),
                ft.Text("O bien:", size=12, color=ft.Colors.GREY_500),
                ft.OutlinedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.QR_CODE_SCANNER, color="#009688"),
                            ft.Text("Simular QR (SL-DS-66)", color="#009688", weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    width=320,
                    height=50,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=simulate_qr_selection
                ),
                ft.TextButton(
                    content=ft.Text("Volver a Opciones", color=ft.Colors.GREY_400),
                    on_click=lambda _: show_active_session_options_view()
                )
            ]
            page.update()

        # Cargar vista inicial según si tiene sesión activa
        if not driver_active_record:
            show_no_active_session_view()
        else:
            show_active_session_options_view()

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
