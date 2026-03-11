{
    # Metadatos visibles en Apps y en la ficha técnica del módulo.
    "name": "Planeación Operativa",
    "summary": "Planeación operativa por horas para registrar actividades y jornadas laborales",
    "description": """
Planeación Operativa - Gestión de Horarios por Empleado
========================================================

Módulo portable para Odoo 17 orientado al registro de actividades y horario de trabajo por empleado.

Datos del desarrollador:
- Nombre: Yerson Vargas Vargas
- Rol: Desarrollador
- Teléfono: 3122919236
- Correo: yervargas@gmail.com

Características principales:
* Planificación por horas con alertas de sobrecarga (>8h)
* Integración con proyectos y tareas
* Reportes por empleado, fecha y estado
* Duplicación semanal y recurrencia configurable

Estados:
* Pendiente (Naranja): Tareas por iniciar
* En Progreso (Azul): Tareas en ejecución (con animación)
* Completado (Verde): Tareas finalizadas

INSTALACIÓN:
============
1. Copiar la carpeta del módulo a /addons
2. Actualizar lista de aplicaciones
3. Instalar el módulo
4. Refrescar el navegador (Ctrl+Shift+R) para limpiar caché de assets
    """,
    "version": "1.0.3",
    "category": "Human Resources/Employees",
    "author": "Yerson Vargas Vargas",
    "maintainer": "Yerson Vargas Vargas",
    "support": "yervargas@gmail.com",
    "website": "mailto:yervargas@gmail.com",
    "license": "LGPL-3",
    # Dependencias mínimas para empleados, proyectos y assets backend.
    "depends": [
        "base",
        "hr",
        "project",
        "web",
    ],
    # Orden de carga funcional: seguridad, acciones, vistas, wizard y automatización.
    "data": [
        "security/ir.model.access.csv",
        "data/employee_schedule_actions.xml",
        "views/employee_schedule_views.xml",
        "wizard/employee_schedule_duplicate_wizard_views.xml",
        "data/employee_schedule_cron.xml",
    ],
    # Assets frontend usados para reforzar la lectura visual del calendario.
    "assets": {
        "web.assets_backend": [
            "employee_hourly_schedule/static/src/css/employee_schedule.css",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
