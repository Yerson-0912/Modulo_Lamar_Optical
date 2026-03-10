PLANEACIÓN OPERATIVA - MÓDULO ODOO 17
=====================================

Descripción General
-------------------
Módulo para gestionar actividades operativas y registro de horario de trabajo
por empleado en Odoo 17. Incluye vistas de planificación diaria, agenda,
control de estado de actividades y análisis de horas.

Objetivo Funcional
------------------
- Registrar actividades por franjas horarias.
- Controlar estado de ejecución (Pendiente, En Progreso, Completado).
- Medir duración de actividades y total diario por empleado.
- Identificar sobrecarga diaria cuando supera 8 horas.
- Gestionar duplicación semanal manual y por recurrencia.

Datos del Desarrollador
-----------------------
Nombre: Yerson Vargas Vargas (Desarrollador)
Teléfono: 3122919236
Correo: yervargas@gmail.com

Versión y Dependencias
----------------------
Versión: 1.0.2
Dependencias: base, hr, project, web

Instalación
-----------
1. Copiar la carpeta employee_hourly_schedule dentro de addons.
2. Actualizar lista de aplicaciones en Odoo.
3. Instalar el módulo Planeación Operativa.
4. Refrescar el navegador con Ctrl+Shift+R para limpiar caché de assets.

Ubicación en Odoo
-----------------
Recursos Humanos > Planeación Operativa

Componentes Principales
-----------------------
- Modelo principal: x_employee_hourly_schedule
- Modelo de actividades: x_employee_hourly_schedule_line
- Asistente de duplicación: x_employee_schedule_duplicate_wizard
- Vistas: árbol, formulario, calendario, pivot y búsqueda

Notas Técnicas
--------------
- Licencia: LGPL-3
- El módulo está preparado para despliegue y transferencia a terceros.
