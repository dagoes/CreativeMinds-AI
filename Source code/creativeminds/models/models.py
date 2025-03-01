from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date
import re


class Proyecto(models.Model):
    _name = 'creativeminds.proyecto'
    _description = 'Proyecto'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos básicos
    proyecto_id = fields.Integer(string='Id del Proyecto', required=True)
    nombre = fields.Char(string='Nombre del Proyecto', required=True)
    empleado_id = fields.Many2many('creativeminds.empleado', string='Empleado')
    costo_por_hora = fields.Float(string='Costo por Hora')
    horas_asignadas = fields.Float(string='Horas Asignadas') 
    costo_total = fields.Float(string='Costo Total', compute='_calcular_costo_total', store=True) 
    descripcion = fields.Text(string='Descripción del Proyecto')
    cliente = fields.Char(string='Cliente')
    horas_trabajadas_ids = fields.One2many(
        'creativeminds.horas_trabajadas',
        'proyecto_id',
        String="Horas Trabajadas"
    )

    @api.depends('costo_por_hora', 'horas_asignadas')
    def _calcular_costo_total(self):
        self.costo_total = self.costo_por_hora * self.horas_asignadas


    @api.constrains('costo_por_hora', 'horas_asignadas')
    def _verificar_costo_y_horas(self):
        if self.costo_por_hora < 0 or self.horas_asignadas < 0:
            raise ValidationError("El costo por hora y las horas asignadas deben ser valores positivos.")
   
    # Estados y seguimiento
    estado = fields.Selection([
        ('planificacion', 'En planificación'),
        ('en_progreso', 'En progreso'),
        ('finalizado', 'Finalizado'),
        ('detenido', 'Detenido'),
    ], string='Estado del Proyecto', default='planificacion', tracking=True)
    
    porcentaje_progreso = fields.Float(
        string='Porcentaje de Progreso',
        compute='_calcular_progreso',
        store=True,
        tracking=True
    )
    
    # Fechas
    fecha_inicio = fields.Date(string='Fecha de Inicio')
    fecha_fin = fields.Date(string='Fecha de Finalización')
    
    # Prioridad y responsables
    prioridad = fields.Selection([
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
    ], string='Prioridad', default='media')
    responsable_id = fields.Many2one('creativeminds.empleado', string='Responsable')
    
    # Presupuesto y recursos
    presupuesto_estimado = fields.Float(string='Presupuesto Estimado')
    recursos_ids = fields.One2many('creativeminds.recurso', 'proyecto_id', string='Recursos Asignados')
    costo_total_recursos = fields.Float(string='Costo Total de Recursos', 
                                     compute='_calcular_costo_total_recursos', 
                                     store=True)

    @api.depends('recursos_ids.costo_total')
    def _calcular_costo_total_recursos(self):
        self.costo_total_recursos = sum(self.recursos_ids.mapped('costo_total'))

    @api.constrains('presupuesto_estimado', 'costo_total_recursos')
    def _verificar_presupuesto(self):
        if self.costo_total_recursos > self.presupuesto_estimado:
            raise ValidationError(
                f"El costo total de recursos ({self.costo_total_recursos}) "
                f"excede el presupuesto estimado ({self.presupuesto_estimado})"
            )


    # Relaciones
    tareas_ids = fields.One2many('creativeminds.tarea', 'proyecto_id', string='Tareas')
    indicadores_ids = fields.One2many('creativeminds.kpi', 'proyecto_id', string='Indicadores de Desempeño')


    imagen_proyecto = fields.Binary(string='Imagen del Proyecto', attachment=True)
    imagen_filename = fields.Char(string='Nombre del archivo de imagen')

    documentacion_tecnica = fields.Binary(string='Documentación Técnica', attachment=True)
    documentacion_filename = fields.Char(string='Nombre del archivo de documentación')

    archivos_adicionales = fields.Many2many(
        'ir.attachment',
        'creativeminds_attachment_rel',
        'creativeminds_id',
        'attachment_id',
        string='Archivos Adicionales'
    )
    
    # Campos de texto adicionales
    colaboradores = fields.Text(string='Agencias Colaboradoras')
    riesgos = fields.Text(string='Riesgos')
    hitos = fields.Text(string='Hitos/Entregables')
    dependencias = fields.Text(string='Dependencias')
    comentarios = fields.Text(string='Comentarios y Notas')
    
    # Configuración
    recordatorios_automaticos = fields.Boolean(string='Activar Recordatorios Automáticos')

    @api.constrains('fecha_inicio', 'fecha_fin')
    def _verificar_fechas_proyecto(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError("La fecha de inicio no puede ser posterior a la fecha de finalización.")

    @api.constrains('presupuesto_estimado')
    def _verificar_presupuesto_estimado(self):
        if self.presupuesto_estimado <= 0:
            raise ValidationError("El presupuesto estimado debe ser mayor que cero.")
        num_recursos = len(self.recursos_ids)
        num_tareas = len(self.tareas_ids)
        presupuesto_requerido = (num_recursos * 500) + (num_tareas * 200)
        if (num_recursos > 0 or num_tareas > 0) and self.presupuesto_estimado < presupuesto_requerido:
            raise ValidationError(
                f"El presupuesto ({self.presupuesto_estimado}) es insuficiente. "
                f"Se requieren al menos {round(presupuesto_requerido, 2)} para cubrir recursos y tareas."
            )


    @api.model
    def create(self, valores):
        proyecto = super(Proyecto, self).create(valores)
        if proyecto.recordatorios_automaticos and proyecto.responsable_id:
            self.env['creativeminds.tarea'].create({
                'nombre': f'Tarea inicial de proyecto: {proyecto.nombre}',
                'proyecto_id': proyecto.id,
                'responsable_id': proyecto.responsable_id.id,
                'estado': 'pendiente',
            })
            self._enviar_recordatorio(proyecto)
        return proyecto

    
    def actualizar_progreso_indicador(self):
        indicador = self.env['creativeminds.indicador'].search([
            ('proyecto_id', '=', self.id),
            ('nombre', '=', 'Progreso del Proyecto')
        ], limit=1)
        if indicador:
            indicador.write({'valor': self.porcentaje_progreso})
        return True

    def enviar_notificacion_proyecto(self, tipo_notificacion='estado'):
        if not self.responsable_id:
            return
        asunto = f"Cambio de Estado: Proyecto {self.nombre}" if tipo_notificacion == 'estado' else f"Actualización de Progreso: Proyecto {self.nombre}"
        mensaje = f"<p>Hola {self.responsable_id.name},</p>"
        mensaje += f"<p>El estado del proyecto <b>{self.nombre}</b> ha cambiado a <b>{dict(self._fields['estado'].selection).get(self.estado)}</b>.</p>"
        mensaje += f"<p>Progreso actual: {round(self.porcentaje_progreso, 2)}%</p>"
        self.message_post(
            body=mensaje,
            subject=asunto,
            partner_ids=[self.responsable_id.partner_id.id]
        )

    def enviar_recordatorio(self, proyecto):
        if not proyecto.responsable_id:
            return
        mensaje = f"""
            <p>Estimado {proyecto.responsable_id.name},</p>
            <p>Este es un recordatorio de que el proyecto <b>{proyecto.nombre}</b> tiene tareas pendientes.</p>
            <p>Por favor, asegúrese de revisar el progreso y continuar con las tareas.</p>
            <p>Saludos,<br>Equipo de gestión de proyectos</p>
        """
        proyecto.message_post(
            body=mensaje,
            subject=f"Recordatorio: Proyecto {proyecto.nombre} - Tareas pendientes",
            partner_ids=[proyecto.responsable_id.partner_id.id]
        )
        actividad_tipo = self.env.ref('mail.mail_activity_data_todo')
        modelo_id = self.env['ir.model']._get_id('creativeminds.proyecto')
        self.env['mail.activity'].create({
            'activity_type_id': actividad_tipo.id,
            'res_model_id': modelo_id,
            'res_id': proyecto.id,
            'user_id': proyecto.responsable_id.id,
            'summary': f"Recordatorio: {proyecto.nombre} - Tareas pendientes",
            'note': f"Este es un recordatorio para que revises las tareas pendientes del proyecto {proyecto.nombre}.",
        })

    @api.depends('tareas_ids.estado')
    def _calcular_progreso(self):
        total_tareas = len(self.tareas_ids)
        tareas_completadas = len(self.tareas_ids.filtered(lambda t: t.estado == 'completada'))
        self.porcentaje_progreso = (tareas_completadas / total_tareas * 100) if total_tareas > 0 else 0.0
 
    def obtener_resumen_proyecto(self):
        self.ensure_one()
        return {
            'nombre': self.nombre,
            'estado': self.estado,
            'progreso': self.porcentaje_progreso,
            'presupuesto': {
                'estimado': self.presupuesto_estimado,
                'actual': self.costo_total_recursos,
                'disponible': self.presupuesto_estimado - self.costo_total_recursos
            },
            'tareas': {
                'total': len(self.tareas_ids),
                'completadas': len(self.tareas_ids.filtered(lambda t: t.estado == 'completada')),
                'en_progreso': len(self.tareas_ids.filtered(lambda t: t.estado == 'en_progreso')),
                'pendientes': len(self.tareas_ids.filtered(lambda t: t.estado == 'pendiente'))
            }
        }

    def duplicar_proyecto(self, proyecto_id):
        proyecto = self.browse(proyecto_id)
        if not proyecto.exists():
            raise ValidationError("El proyecto especificado no existe.")
        nuevo_proyecto = proyecto.copy() 
        for tarea in proyecto.tareas_ids:
            tarea.copy({'proyecto_id': nuevo_proyecto.id})
        return nuevo_proyecto


    @api.constrains('descripcion', 'cliente', 'responsable_id')
    def _verificar_campos_importantes(self):
        if self.descripcion and len(self.descripcion.strip()) < 10:
            raise ValidationError("La descripción del proyecto debe tener al menos 10 caracteres.")
        if self.estado in ['en_progreso', 'finalizado'] and not self.cliente:
            raise ValidationError("Debe especificar un cliente antes de cambiar el proyecto a 'En progreso' o 'Finalizado'.")
        if self.estado != 'planificacion' and not self.responsable_id:
            raise ValidationError("Debe asignar un responsable antes de avanzar con el proyecto.")

    @api.constrains('riesgos', 'hitos')
    def _verificar_campos_planificacion(self):
        if self.prioridad == 'alta':
            if not self.riesgos:
                raise ValidationError("Para proyectos de alta prioridad, es obligatorio definir los riesgos.")
            if not self.hitos:
                raise ValidationError("Para proyectos de alta prioridad, es obligatorio definir los hitos/entregables.")

    @api.constrains('recursos_ids')
    def _verificar_recursos_minimos(self):
        if self.estado != 'planificacion' and not self.recursos_ids:
            raise ValidationError("Debe asignar al menos un recurso antes de iniciar el proyecto.")

    @api.constrains('fecha_inicio', 'fecha_fin', 'estado', 'tareas_ids')
    def _verificar_fechas_y_tareas(self):
        if self.estado == 'en_progreso':
            if not self.fecha_inicio:
                raise ValidationError("Debe establecer una fecha de inicio antes de comenzar el proyecto.")
            if not self.fecha_fin:
                raise ValidationError("Debe establecer una fecha de finalización antes de comenzar el proyecto.")
            if not self.tareas_ids:
                raise ValidationError("Debe crear al menos una tarea antes de iniciar el proyecto.")
            for tarea in self.tareas_ids:
                if tarea.fecha_inicio and tarea.fecha_inicio < self.fecha_inicio:
                    raise ValidationError(f"La tarea '{tarea.nombre}' tiene una fecha de inicio anterior a la fecha de inicio del proyecto.")
                if tarea.fecha_fin and tarea.fecha_fin > self.fecha_fin:
                    raise ValidationError(f"La tarea '{tarea.nombre}' tiene una fecha de finalización posterior a la fecha de fin del proyecto.")


     # Para ver tareas del proyecto
    def ver_tareas(self):
        return {
            'name': 'Tareas del Proyecto',
            'type': 'ir.actions.act_window',
            'res_model': 'creativeminds.tarea',
            'view_mode': 'tree,form',
            'domain': [('proyecto_id', '=', self.id)],
            'context': {'default_proyecto_id': self.id},
            'target': 'current',
        }

    # Para ver miembros del proyecto
    def ver_miembros(self):
        return {
            'name': 'Miembros del Proyecto',
            'type': 'ir.actions.act_window',
            'res_model': 'creativeminds.empleado',
            'view_mode': 'tree,form',
            'domain': [('proyecto_id', '=', self.id)],
            'target': 'current',
        }

class Recurso(models.Model):
    _name = 'creativeminds.recurso'
    _description = 'Recursos del Proyecto'

    nombre = fields.Char(string='Nombre del Recurso', required=True)
    empleado_id = fields.Many2many('creativeminds.empleado', string='Empleado')
    proyecto_id = fields.Many2one('creativeminds.proyecto', string='Proyecto')
    
    # Costos y presupuesto
    costo_por_hora = fields.Float(string='Costo por Hora')
    horas_asignadas = fields.Float(string='Horas Asignadas')
    costo_total = fields.Float(string='Costo Total', compute='_compute_costo_total', store=True)
    
    @api.depends('costo_por_hora', 'horas_asignadas')
    def _compute_costo_total(self):
        for record in self:
            record.costo_total = record.costo_por_hora * record.horas_asignadas

    # Fechas de asignación
    fecha_inicio = fields.Date(string='Fecha de Inicio')
    fecha_fin = fields.Date(string='Fecha de Fin')
    
    # Estado del recurso
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('asignado', 'Asignado'),
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado')
    ], string='Estado', default='borrador')

    
class Tarea(models.Model):
    _name = 'creativeminds.tarea'
    _description = 'Tareas del Proyecto'

    proyecto_id = fields.Many2one('creativeminds.proyecto', string='Proyecto')
    nombre = fields.Char(string='Nombre de la Tarea', required=True)
    descripcion = fields.Text(string='Descripción')
    responsable_id = fields.Many2one('creativeminds.empleado', string='Responsable')
    fecha_comienzo = fields.Date(string='Fecha de Inicio')
    fecha_final = fields.Date(string='Fecha de Finalización')
    estado = fields.Selection([
        ('pendiente', 'Por hacer'),
        ('en_progreso', 'En progreso'),
        ('completada', 'Completada'),
    ], string='Estado', default='pendiente')


#Indicadores de Desempeño
class KPI(models.Model):
    _name = 'creativeminds.kpi'
    _description = 'Indicadores Clave de Rendimiento'

    proyecto_id = fields.Many2one('creativeminds.proyecto', string='Proyecto')
    nombre = fields.Char(string='Nombre del KPI', required=True)
    valor = fields.Float(string='Valor')
    objetivo = fields.Float(string='Objetivo')

class Empleado(models.Model):
    _name = 'creativeminds.empleado'
    _description = 'Empleados del Proyecto'
    _inherit = ['mail.thread']

    empleado_id = fields.Integer(string='ID',required=True)
    nombre = fields.Char(string='Nombre', required=True)
    dni = fields.Char(string ='DNI',size = 9, required=True)
    apellido1  = fields.Char(string='Primer apellido')
    apellido2  = fields.Char(string='Sgundo apellido')
    fecha_nacimiento = fields.Date(string='Fecha de nacimiento')
    fecha_incorporacion  = fields.Date(string='Fecha incorporacion',default=lambda self: fields.Datetime.now(),readonly = True,)
    foto  = fields.Image(string='Foto',max_width=200,max_height=200,)
    proyecto_id = fields.Many2many('creativeminds.proyecto', string='Proyectos')
    departamento = fields.Char(string='Departamento')
    puesto = fields.Char(string='Puesto')
    equipo_id = fields.Many2many('creativeminds.equipo', string='Equipos')
    disponibilidad = fields.Selection([
        ('disponible', 'Disponible'),
        ('asignado', 'Asignado'),
        ('parcial', 'Parcialmente Disponible'),
        ('no_disponible', 'No Disponible')
    ], string='Disponibilidad', default='disponible')
    horas_trabajadas_ids = fields.One2many(
        'creativeminds.horas_trabajadas',
        'empleado_id',
        string="Horas Trabajadas"
    )
    
    @api.constrains('dni')
    def _check_dni(self):
        regex = re.compile('[0-9]{8}[A-Z]\Z',re.I)
        for record in self:
            if not regex.match(record.dni):
                raise ValidationError('ERROR. Formato DNI incorrecto. ')

    _sql_constraints = [
        ('DNI_unico', 'UNIQUE(dni)', "El DNI debe ser único")
    ]

class HorasTrabajadas(models.Model):
    _name = 'creativeminds.horas_trabajadas'
    _description = 'Horas Trabajadas'

    horas = fields.Float("Horas Trabajadas")
    empleado_id = fields.Many2one('creativeminds.empleado', string="Empleado", required=True)
    proyecto_id = fields.Many2one('creativeminds.proyecto', string="Proyecto", required=True)
    fecha = fields.Date("Fecha de Registro")
    
    @api.model
    def create(self, values):
        if values.get('empleado_id') and values.get('proyecto_id'):
            existing_record = self.search([
                ('empleado_id', '=', values['empleado_id']),
                ('proyecto_id', '=', values['proyecto_id']),
            ], limit=1)
            if existing_record:
                raise ValidationError("Ya existe un registro de horas trabajadas para este proyecto y empleado.")

        if not values.get("Fecha"):
            values['fecha'] = fields.Date.today()

        return super(HorasTrabajadas, self).create(values)

class Equipo(models.Model):
    _name = 'creativeminds.equipo'
    _description = 'Equipos de Trabajo'

    equipo_id = fields.Integer(string='ID Grupo', required=True)
    nombre = fields.Char(string='Nombre', required=True)
    empleado_id = fields.Many2many('creativeminds.empleado', string='Empleado')
    responsable_id = fields.Many2one('creativeminds.empleado', string='Responsable')
    descripcion = fields.Text(string='Descripcion del equipo')
    n_miembros = fields.Integer(string='Número de Miembros', compute='_compute_n_miembros')

    def _compute_n_miembros(self):
        for equipo in self:
            equipo.n_miembros = len(equipo.empleado_id)

class PanelDeControl(models.Model):
    _name = 'creativeminds.control.panel'
    _description = 'Panel de Control'

    nombre = fields.Char(string='Nombre', required=True)
    proyectos_ids = fields.Many2many('creativeminds.proyecto', string='Proyectos en el Panel')
