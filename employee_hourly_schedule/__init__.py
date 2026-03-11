# -*- coding: utf-8 -*-
"""
Planeación Operativa - Employee Hourly Schedule

Módulo para control de actividades y jornada laboral por empleado.

Desarrollador:
- Nombre: Yerson Vargas Vargas
- Teléfono: 3122919236
- Correo: yervargas@gmail.com
"""

from . import models
from . import wizard

# El orden de import asegura que los modelos persistentes queden cargados
# antes de registrar los asistentes transitorios que dependen de ellos.
