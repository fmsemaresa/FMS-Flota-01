import flet as ft
from src.database.connection import get_session
from src.database.models import Vehicle, Driver

def get_entry_view(page: ft.Page, on_navigate):
    """Devuelve la vista de ingreso inicial (RUT / Patente / QR)."""
    
    # Controladores de texto
    input_field = ft.TextField(
        label="RUT o Patente del Vehículo",
        hint_text="Ej: 12.345.678-9 o AB-CD-12",
        width=320,
        height=60,
        text_align=ft.TextAlign.CENTER,
        border_color="#3F51B5",
        focused_border_color="#009688",
        border_radius=12,
        color=ft.Colors.WHITE,
        focused_border_width=2,
    )
    
    error_text = ft.Text(value="", color=ft.Colors.RED_400, size=14, weight=ft.FontWeight.BOLD)
    
    def process_input(e):
        value = input_field.value.strip().upper()
        if not value:
            error_text.value = "Por favor, ingrese un RUT o Patente."
            page.update()
            return
            
        session = get_session()
        # Verificar si es una patente
        vehicle = session.query(Vehicle).filter(Vehicle.plate == value).first()
        if vehicle:
            error_text.value = ""
            session.close()
            on_navigate(f"/status/vehicle/{value}")
            return
            
        # Verificar si es un RUT
        driver = session.query(Driver).filter(Driver.rut == value).first()
        if driver:
            error_text.value = ""
            session.close()
            on_navigate(f"/status/driver/{value}")
            return
            
        # Si no se encuentra
        error_text.value = "RUT o Patente no registrados en la flota."
        session.close()
        page.update()

    def simulate_qr(e):
        # Simular lectura del QR de la Toyota Hilux (AB-CD-12)
        error_text.value = ""
        on_navigate("/status/vehicle/AB-CD-12")

    # Contenido principal de la tarjeta
    card_content = ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.LOCAL_SHIPPING, size=64, color="#009688"),
                ft.Text("FMS FLOTA 0.1", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text("Gestión de Inicio y Término de Uso", size=14, color=ft.Colors.GREY_400),
                ft.Divider(height=20, color="#2E2E3E"),
                
                ft.Text("Ingresar al Vehículo", size=16, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE),
                input_field,
                error_text,
                
                ft.Container(height=10),
                
                ft.ElevatedButton(
                    content=ft.Text("Ingresar", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    width=320,
                    height=50,
                    style=ft.ButtonStyle(
                        bgcolor="#3F51B5",
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=process_input
                ),
                
                ft.Text("O bien:", size=12, color=ft.Colors.GREY_500),
                
                ft.OutlinedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.QR_CODE_SCANNER, color="#009688"),
                            ft.Text("Simular Escaneo Código QR", color="#009688", weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    width=320,
                    height=50,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=simulate_qr
                ),
                
                ft.Divider(height=30, color="#2E2E3E"),
                
                ft.TextButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, color="#9FA8DA"),
                            ft.Text("Consola de Administración e Historial", color="#9FA8DA")
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    on_click=lambda _: on_navigate("/admin")
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
        route="/",
        controls=[card_content],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        bgcolor="#0F0F1A",
        padding=10
    )
