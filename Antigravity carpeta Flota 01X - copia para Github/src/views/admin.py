import os
import datetime
import flet as ft
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from src.database.connection import get_session
from src.database.models import UsageRecord, Vehicle, Driver
from src.utils.excel_exporter import export_db_to_excel
from src.config import BASE_DIR, ASSETS_DIR

def get_admin_view(page: ft.Page, on_navigate):
    """Devuelve la vista del panel de administración, historial y gestión de vehículos."""
    
    # ----------------------------------------------------
    # TABLA 1: HISTORIAL DE USOS
    # ----------------------------------------------------
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Patente", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Modelo", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Conductor", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Rol", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Inicio", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Fin", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Duración", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Estado", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
        ],
        rows=[],
        heading_row_color="#151520",
        divider_thickness=1,
        border_radius=10,
        horizontal_lines=ft.BorderSide(1, "#2E2E3E")
    )

    def refresh_history_list():
        db_sess = get_session()
        try:
            records = (
                db_sess.query(UsageRecord)
                .options(joinedload(UsageRecord.vehicle), joinedload(UsageRecord.driver))
                .order_by(UsageRecord.start_time.desc())
                .all()
            )
            
            table_rows = []
            for r in records:
                duration_str = "-"
                if r.end_time:
                    diff = r.end_time - r.start_time
                    duration_str = f"{round(diff.total_seconds() / 60)} min"
                
                status_chip = ft.Container(
                    content=ft.Text("Activo" if r.status == "active" else "Terminado", size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.GREEN_600 if r.status == "active" else ft.Colors.BLUE_GREY_700,
                    padding=ft.Padding(left=12, top=6, right=12, bottom=6),
                    border_radius=8
                )
                
                table_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(r.vehicle.plate, color=ft.Colors.WHITE)),
                            ft.DataCell(ft.Text(r.vehicle.model, color=ft.Colors.GREY_300)),
                            ft.DataCell(ft.Text(r.driver.name, color=ft.Colors.WHITE)),
                            ft.DataCell(ft.Text(r.driver.role, color=ft.Colors.GREY_300)),
                            ft.DataCell(ft.Text(r.start_time.strftime("%Y-%m-%d %H:%M"), color=ft.Colors.GREY_400)),
                            ft.DataCell(ft.Text(r.end_time.strftime("%Y-%m-%d %H:%M") if r.end_time else "En curso", color=ft.Colors.GREY_400)),
                            ft.DataCell(ft.Text(duration_str, color=ft.Colors.GREY_300)),
                            ft.DataCell(status_chip)
                        ]
                    )
                )
            data_table.rows = table_rows
            page.update()
        except Exception as ex:
            print(f"Error al cargar historial: {ex}")
        finally:
            db_sess.close()

    # ----------------------------------------------------
    # TABLA 2: GESTIÓN DE VEHÍCULOS
    # ----------------------------------------------------
    vehicles_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Patente", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Modelo", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Tipo", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
            ft.DataColumn(ft.Text("Estado Actual", weight=ft.FontWeight.BOLD, color="#9FA8DA")),
        ],
        rows=[],
        heading_row_color="#151520",
        divider_thickness=1,
        border_radius=10,
        horizontal_lines=ft.BorderSide(1, "#2E2E3E")
    )

    def handle_status_change(e, vehicle_id):
        new_status = e.control.value
        db_sess = get_session()
        try:
            vehicle = db_sess.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if vehicle:
                vehicle.status = new_status
                vehicle.is_active = (new_status == "en flota")
                
                # Si el vehículo ya no está "en flota" (es decir, se da de baja/venta),
                # deberíamos cerrar cualquier período de uso activo inmediatamente.
                if not vehicle.is_active:
                    active_uses = db_sess.query(UsageRecord).filter(
                        UsageRecord.vehicle_id == vehicle.id,
                        UsageRecord.status == "active"
                    ).all()
                    for use in active_uses:
                        use.end_time = datetime.datetime.now()
                        use.status = "completed"
                
                db_sess.commit()
                
                # Feedback visual
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Estado de {vehicle.plate} actualizado a '{new_status}'", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.GREEN_700,
                    duration=3000,
                    show_close_icon=True
                )
                page.snack_bar.open = True
                
                # Refrescar ambas vistas
                refresh_vehicles_list(search_input.value)
                refresh_history_list()
        except Exception as ex:
            db_sess.rollback()
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Error al cambiar estado: {ex}", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED_700,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
        finally:
            db_sess.close()

    def refresh_vehicles_list(search_query=""):
        db_sess = get_session()
        try:
            query = db_sess.query(Vehicle)
            if search_query:
                clean_query = search_query.strip().upper().replace("-", "").replace(" ", "")
                query = query.filter(func.replace(Vehicle.plate, "-", "").like(f"%{clean_query}%"))
            
            # Ordenar por patente y limitar a 100 para rendimiento fluido
            vehicles = query.order_by(Vehicle.plate).limit(100).all()
            
            table_rows = []
            for v in vehicles:
                # Crear selector de estados disponible
                status_drop = ft.Dropdown(
                    options=[
                        ft.dropdown.Option("en flota"),
                        ft.dropdown.Option("a la venta"),
                        ft.dropdown.Option("vendido y entregado")
                    ],
                    value=v.status or "en flota",
                    width=200,
                    height=45,
                    border_color="#3F51B5",
                    border_radius=8,
                    color=ft.Colors.WHITE,
                    content_padding=5,
                    on_change=lambda e, v_id=v.id: handle_status_change(e, v_id)
                )
                
                table_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(v.plate, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(v.model, color=ft.Colors.GREY_300)),
                            ft.DataCell(ft.Text(v.vehicle_type, color=ft.Colors.GREY_400)),
                            ft.DataCell(status_drop)
                        ]
                    )
                )
            vehicles_table.rows = table_rows
            page.update()
        except Exception as ex:
            print(f"Error al cargar vehículos: {ex}")
        finally:
            db_sess.close()

    # Inputs para agregar nuevo vehículo
    plate_input = ft.TextField(
        label="Patente",
        hint_text="Ej: AB-CD-12",
        width=150,
        border_color="#3F51B5",
        border_radius=10,
        color=ft.Colors.WHITE,
        focused_border_color="#009688"
    )
    brand_input = ft.TextField(
        label="Marca",
        hint_text="Ej: Toyota",
        width=150,
        border_color="#3F51B5",
        border_radius=10,
        color=ft.Colors.WHITE,
        focused_border_color="#009688"
    )
    model_input = ft.TextField(
        label="Modelo",
        hint_text="Ej: Hilux",
        width=150,
        border_color="#3F51B5",
        border_radius=10,
        color=ft.Colors.WHITE,
        focused_border_color="#009688"
    )
    type_dropdown = ft.Dropdown(
        label="Tipo de Vehículo",
        options=[
            ft.dropdown.Option("Camioneta"),
            ft.dropdown.Option("Furgón"),
            ft.dropdown.Option("SUV"),
            ft.dropdown.Option("Sedán"),
            ft.dropdown.Option("Otro")
        ],
        width=150,
        border_color="#3F51B5",
        border_radius=10,
        color=ft.Colors.WHITE,
        focused_border_color="#009688"
    )
    status_dropdown = ft.Dropdown(
        label="Estado Inicial",
        options=[
            ft.dropdown.Option("en flota"),
            ft.dropdown.Option("a la venta"),
            ft.dropdown.Option("vendido y entregado")
        ],
        value="en flota",
        width=150,
        border_color="#3F51B5",
        border_radius=10,
        color=ft.Colors.WHITE,
        focused_border_color="#009688"
    )

    def handle_add_vehicle(e):
        plate = plate_input.value.strip().upper().replace(" ", "").replace("-", "")
        if not plate:
            page.snack_bar = ft.SnackBar(content=ft.Text("Por favor, ingresa una Patente.", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_700)
            page.snack_bar.open = True
            page.update()
            return
            
        # Formatear patente chilena (ej: ABCD12 -> AB-CD-12)
        if len(plate) == 6:
            formatted_plate = f"{plate[:2]}-{plate[2:4]}-{plate[4:]}"
        else:
            formatted_plate = plate
            
        brand = brand_input.value.strip()
        model_name = model_input.value.strip()
        v_type = type_dropdown.value
        initial_status = status_dropdown.value
        
        if not brand or not model_name or not v_type or not initial_status:
            page.snack_bar = ft.SnackBar(content=ft.Text("Por favor, completa Marca, Modelo, Tipo y Estado.", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_700)
            page.snack_bar.open = True
            page.update()
            return
            
        full_model = f"{brand} {model_name}"
        is_active = (initial_status == "en flota")
        
        db_sess = get_session()
        try:
            # Validar si ya existe
            existing = db_sess.query(Vehicle).filter(Vehicle.plate == formatted_plate).first()
            if existing:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"La patente {formatted_plate} ya está registrada.", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_700)
                page.snack_bar.open = True
                page.update()
                return
                
            new_veh = Vehicle(
                plate=formatted_plate,
                model=full_model,
                vehicle_type=v_type,
                is_active=is_active,
                status=initial_status
            )
            db_sess.add(new_veh)
            db_sess.commit()
            
            # Limpiar entradas
            plate_input.value = ""
            brand_input.value = ""
            model_input.value = ""
            type_dropdown.value = None
            status_dropdown.value = "en flota"
            
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Vehículo [{formatted_plate}] agregado con éxito", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.GREEN_700,
                duration=3000
            )
            page.snack_bar.open = True
            
            refresh_vehicles_list(search_input.value)
        except Exception as ex:
            db_sess.rollback()
            page.snack_bar = ft.SnackBar(content=ft.Text(f"Error al agregar vehículo: {ex}", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_700)
            page.snack_bar.open = True
            page.update()
        finally:
            db_sess.close()

    # Buscador de vehículos por patente
    search_input = ft.TextField(
        label="Buscar por Patente",
        hint_text="Ej: AB-CD",
        width=200,
        border_color="#3F51B5",
        border_radius=10,
        color=ft.Colors.WHITE,
        focused_border_color="#009688",
        on_change=lambda e: refresh_vehicles_list(e.control.value)
    )

    # ----------------------------------------------------
    # EXPORTAR A EXCEL
    # ----------------------------------------------------
    def handle_excel_export(e):
        output_file_name = "Reporte_FMS_Flota.xlsx"
        output_path = os.path.join(ASSETS_DIR, output_file_name)
        
        success = export_db_to_excel(output_path)
        
        def close_dialog(evt):
            page.dialog.open = False
            page.update()

        if success:
            # Trigger browser download of the Excel file via run_task with an async helper
            async def start_download():
                await page.launch_url(f"/{output_file_name}")
            page.run_task(start_download)
            
            dialog = ft.AlertDialog(
                title=ft.Text("Descargando Excel", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                content=ft.Text(
                    f"Se ha generado el reporte y debería comenzar la descarga en tu navegador.\n\n"
                    f"Archivo: {output_file_name}\n"
                    f"Ruta servidor: {output_path}"
                ),
                actions=[
                    ft.TextButton(
                        content=ft.Text("Entendido", weight=ft.FontWeight.BOLD),
                        on_click=close_dialog
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            page.dialog = dialog
            dialog.open = True
            page.update()
        else:
            dialog = ft.AlertDialog(
                title=ft.Text("Error al Exportar", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                content=ft.Text("Ocurrió un error inesperado al intentar escribir el archivo Excel. Verifique que no esté abierto."),
                actions=[
                    ft.TextButton(
                        content=ft.Text("Entendido", weight=ft.FontWeight.BOLD),
                        on_click=close_dialog
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            page.dialog = dialog
            dialog.open = True
            page.update()

    # Botones superiores de la cabecera
    top_buttons_row = ft.Row(
        controls=[
            ft.ElevatedButton(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DOWNLOAD, color=ft.Colors.WHITE),
                        ft.Text("Exportar Historial a Excel (.xlsx)", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10
                ),
                bgcolor="#2E7D32", # Verde oscuro
                height=50,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=handle_excel_export
            ),
            ft.OutlinedButton(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ARROW_BACK, color=ft.Colors.GREY_400),
                        ft.Text("Volver al Inicio", color=ft.Colors.GREY_400, weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10
                ),
                height=50,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
                on_click=lambda _: on_navigate("/")
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    # ----------------------------------------------------
    # ESTRUCTURA DE TABS PERSONALIZADA (EVITA ERRORES DE VERSION EN FLET)
    # ----------------------------------------------------
    
    # 1. Contenidos de cada pestaña
    historial_content = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[data_table],
                    scroll=ft.ScrollMode.ADAPTIVE
                )
            ],
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True
        ),
        bgcolor="#151520",
        padding=15,
        border_radius=12,
        margin=ft.Margin(top=15)
    )

    gestion_content = ft.Container(
        content=ft.Column(
            controls=[
                # Subsección A: Agregar Vehículo
                ft.Text("Agregar Nuevo Vehículo", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Row(
                    controls=[
                        plate_input,
                        brand_input,
                        model_input,
                        type_dropdown,
                        status_dropdown,
                        ft.ElevatedButton(
                            content=ft.Text("Agregar", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                            bgcolor="#3F51B5",
                            height=48,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                            on_click=handle_add_vehicle
                        )
                    ],
                    spacing=10,
                    wrap=True
                ),
                ft.Divider(height=25, color="#2E2E3E"),
                
                # Subsección B: Lista de Vehículos
                ft.Row(
                    controls=[
                        ft.Text("Flota de Vehículos (Primeros 100)", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        search_input
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Container(height=5),
                ft.Row(
                    controls=[vehicles_table],
                    scroll=ft.ScrollMode.ADAPTIVE
                )
            ],
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
            spacing=10
        ),
        bgcolor="#151520",
        padding=20,
        border_radius=12,
        margin=ft.Margin(top=15),
        expand=True
    )

    # 2. Contenedor dinámico de contenido
    tab_content_container = ft.Container(
        content=historial_content,
        expand=True
    )

    # 3. Cabeceras de pestañas personalizadas con estilo premium
    historial_text = ft.Text("Historial de Usos", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    historial_icon = ft.Icon(ft.Icons.HISTORY, size=20, color=ft.Colors.WHITE)
    
    gestion_text = ft.Text("Gestión de Vehículos", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_400)
    gestion_icon = ft.Icon(ft.Icons.DRIVE_ETA, size=20, color=ft.Colors.GREY_400)

    # Definimos la función de cambio de pestaña
    def switch_tab(tab_index):
        if tab_index == 0:
            historial_btn.bgcolor = "#3F51B5"
            historial_icon.color = ft.Colors.WHITE
            historial_text.color = ft.Colors.WHITE
            
            gestion_btn.bgcolor = "#2E2E3E"
            gestion_icon.color = ft.Colors.GREY_400
            gestion_text.color = ft.Colors.GREY_400
            
            tab_content_container.content = historial_content
            refresh_history_list()
        else:
            historial_btn.bgcolor = "#2E2E3E"
            historial_icon.color = ft.Colors.GREY_400
            historial_text.color = ft.Colors.GREY_400
            
            gestion_btn.bgcolor = "#3F51B5"
            gestion_icon.color = ft.Colors.WHITE
            gestion_text.color = ft.Colors.WHITE
            
            tab_content_container.content = gestion_content
            refresh_vehicles_list(search_input.value)
            
        page.update()

    historial_btn = ft.Container(
        content=ft.Row(
            controls=[historial_icon, historial_text],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        padding=ft.Padding.symmetric(horizontal=20, vertical=12),
        border_radius=10,
        bgcolor="#3F51B5",
        on_click=lambda _: switch_tab(0)
    )

    gestion_btn = ft.Container(
        content=ft.Row(
            controls=[gestion_icon, gestion_text],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        padding=ft.Padding.symmetric(horizontal=20, vertical=12),
        border_radius=10,
        bgcolor="#2E2E3E",
        on_click=lambda _: switch_tab(1)
    )

    tab_headers = ft.Row(
        controls=[
            historial_btn,
            gestion_btn
        ],
        spacing=10
    )

    # Cargar pestaña inicial
    refresh_history_list()

    # Contenido principal de la consola de administración
    admin_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, size=36, color="#3F51B5"),
                        ft.Text("Consola de Administración FMS", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.Text("Historial de movimientos y gestión de estado de vehículos", size=14, color=ft.Colors.GREY_400),
                ft.Divider(height=20, color="#2E2E3E"),
                
                top_buttons_row,
                
                ft.Container(height=10),
                
                # Tabs que ocupan todo el espacio restante e impiden caídas de layout
                tab_headers,
                tab_content_container
            ],
            spacing=15,
            expand=True
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
        expand=True,
    )

    return ft.View(
        route="/admin",
        controls=[admin_card],
        bgcolor="#0F0F1A",
        padding=10
    )
