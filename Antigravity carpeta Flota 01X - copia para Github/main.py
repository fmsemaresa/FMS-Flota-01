import flet as ft
from src.database.connection import init_db
from src.views.entry import get_entry_view
from src.views.status import get_status_view
from src.views.driver_select import get_driver_select_view
from src.views.admin import get_admin_view

def main(page: ft.Page):
    page.title = "FMS Flota 0.1"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    
    # Configurar diseño adaptativo
    page.window_width = 420
    page.window_height = 800
    page.window_resizable = True
    
    # Inicializar base de datos
    init_db()

    def route_change(route):
        page.views.clear()
        
        # Enrutador
        troute = ft.TemplateRoute(page.route)
        
        if troute.match("/"):
            page.views.append(get_entry_view(page, page.go))
            
        elif troute.match("/status/vehicle/:plate"):
            page.views.append(get_status_view(page, page.go, "vehicle", troute.plate))
            
        elif troute.match("/status/driver/:rut"):
            page.views.append(get_status_view(page, page.go, "driver", troute.rut))
            
        elif troute.match("/driver_select/:plate"):
            page.views.append(get_driver_select_view(page, page.go, troute.plate))
            
        elif troute.match("/admin"):
            page.views.append(get_admin_view(page, page.go))
            
        else:
            # Ruta no encontrada, volver al inicio
            page.views.append(get_entry_view(page, page.go))
            
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Forzar el renderizado de la ruta inicial en el arranque
    route_change(None)


if __name__ == "__main__":
    # Ejecutar en modo navegador web por defecto para que sea fácil probar la vista de PC/Móvil
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550, assets_dir="assets")
