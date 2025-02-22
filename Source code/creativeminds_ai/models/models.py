from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class CreativeMindsAI(models.Model):
    _name = 'creativeminds.ai'
    _description = 'Creative Minds AI'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos básicos
    nombre = fields.Char(string='Nombre del Proyecto', required=True)
    empleado_id = fields.Many2one('creativeminds.empleado', string='Empleado')
    costo_por_hora = fields.Float(string='Costo por Hora')
    horas_asignadas = fields.Float(string='Horas Asignadas') 
    costo_total = fields.Float(string='Costo Total', compute='_calcular_costo_total', store=True) 
    descripcion = fields.Text(string='Descripción del Proyecto')
    cliente = fields.Char(string='Cliente')
    
    @api.depends('costo_por_hora', 'horas_asignadas')
    def _calcular_costo_total(self):
        for registro in self:
            registro.costo_total = registro.costo_por_hora * registro.horas_asignadas


    @api.constrains('costo_por_hora', 'horas_asignadas')
    def _verificar_costo_y_horas(self):
        for registro in self:
            if registro.costo_por_hora < 0 or registro.horas_asignadas < 0:
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
    responsable_id = fields.Many2one('res.users', string='Responsable')
    
    # Presupuesto y recursos
    presupuesto_estimado = fields.Float(string='Presupuesto Estimado')
    recursos_ids = fields.One2many('creativeminds.recurso', 'proyecto_id', string='Recursos Asignados')
    costo_total_recursos = fields.Float(string='Costo Total de Recursos', 
                                     compute='_calcular_costo_total_recursos', 
                                     store=True)

    @api.depends('recursos_ids.costo_total')
    def _calcular_costo_total_recursos(self):
        for registro in self:
            registro.costo_total_recursos = sum(registro.recursos_ids.mapped('costo_total'))

    @api.constrains('presupuesto_estimado', 'costo_total_recursos')
    def _verificar_presupuesto(self):
        for registro in self:
            if registro.costo_total_recursos > registro.presupuesto_estimado:
                raise ValidationError(
                    f"El costo total de recursos ({registro.costo_total_recursos}) "
                    f"excede el presupuesto estimado ({registro.presupuesto_estimado})"
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
    riesgos = fields.Text(string='Riesgos')
    hitos = fields.Text(string='Hitos/Entregables')
    dependencias = fields.Text(string='Dependencias')
    comentarios = fields.Text(string='Comentarios y Notas')
    
    # Configuración
    recordatorios_automaticos = fields.Boolean(string='Activar Recordatorios Automáticos')

    @api.constrains('fecha_inicio', 'fecha_fin')
    def _verificar_fechas_proyecto(self):
        for registro in self:
            if registro.fecha_inicio and registro.fecha_fin and registro.fecha_inicio > registro.fecha_fin:
                raise ValidationError("La fecha de inicio no puede ser posterior a la fecha de finalización.")

    @api.constrains('presupuesto_estimado')
    def _verificar_presupuesto_estimado(self):
        for registro in self:
            if registro.presupuesto_estimado <= 0:
                raise ValidationError("El presupuesto estimado debe ser mayor que cero.")

            num_recursos = len(registro.recursos_ids)
            num_tareas = len(registro.tareas_ids)
            presupuesto_requerido = (num_recursos * 500) + (num_tareas * 200)

            if (num_recursos > 0 or num_tareas > 0) and registro.presupuesto_estimado < presupuesto_requerido:
                raise ValidationError(
                    f"El presupuesto ({registro.presupuesto_estimado}) es insuficiente. "
                    f"Se requieren al menos {round(presupuesto_requerido, 2)} para cubrir recursos y tareas."
                )


    @api.model
    def create(self, valores):
        proyecto = super(CreativeMindsAI, self).create(valores)
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
        modelo_id = self.env['ir.model']._get_id('creativeminds.ai')

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
        for registro in self:
            total_tareas = len(registro.tareas_ids)
            tareas_completadas = len(registro.tareas_ids.filtered(lambda t: t.estado == 'completada'))

            registro.porcentaje_progreso = (tareas_completadas / total_tareas * 100) if total_tareas > 0 else 0.0
 
    def detener_proyecto(self):
        for registro in self:
            if registro.estado in ['finalizado', 'detenido']:
                raise ValidationError("El proyecto ya está finalizado o detenido.")
            
            registro.estado = 'detenido'
            # Notificar al responsable
            self.enviar_notificacion_proyecto(tipo_notificacion='estado')

    def reactivar_proyecto(self):
        for registro in self:
            if registro.estado != 'detenido':
                raise ValidationError("Solo se pueden reactivar proyectos detenidos.")
            
            registro.estado = 'en_progreso'
            self.enviar_notificacion_proyecto(tipo_notificacion='estado')

    def finalizar_proyecto(self):
        self.write({
            'estado': 'finalizado',
            'fecha_fin': fields.Date.context_today(self)
        })
    
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
        for registro in self:
            if registro.descripcion and len(registro.descripcion.strip()) < 10:
                raise ValidationError("La descripción del proyecto debe tener al menos 10 caracteres.")
                
            if registro.estado in ['en_progreso', 'finalizado'] and not registro.cliente:
                raise ValidationError("Debe especificar un cliente antes de cambiar el proyecto a 'En progreso' o 'Finalizado'.")
                
            if registro.estado != 'planificacion' and not registro.responsable_id:
                raise ValidationError("Debe asignar un responsable antes de avanzar con el proyecto.")

    @api.constrains('riesgos', 'hitos')
    def _verificar_campos_planificacion(self):
        for registro in self:
            if registro.prioridad == 'alta':
                if not registro.riesgos:
                    raise ValidationError("Para proyectos de alta prioridad, es obligatorio definir los riesgos.")
                if not registro.hitos:
                    raise ValidationError("Para proyectos de alta prioridad, es obligatorio definir los hitos/entregables.")

    @api.constrains('recursos_ids')
    def _verificar_recursos_minimos(self):
        for registro in self:
            if registro.estado != 'planificacion' and not registro.recursos_ids:
                raise ValidationError("Debe asignar al menos un recurso antes de iniciar el proyecto.")

    @api.constrains('fecha_inicio', 'fecha_fin', 'estado', 'tareas_ids')
    def _verificar_fechas_y_tareas(self):
        for registro in self:
            if registro.estado == 'en_progreso':
                if not registro.fecha_inicio:
                    raise ValidationError("Debe establecer una fecha de inicio antes de comenzar el proyecto.")
                if not registro.fecha_fin:
                    raise ValidationError("Debe establecer una fecha de finalización antes de comenzar el proyecto.")
                
                if not registro.tareas_ids:
                    raise ValidationError("Debe crear al menos una tarea antes de iniciar el proyecto.")
                
                for tarea in registro.tareas_ids:
                    if tarea.fecha_inicio and tarea.fecha_inicio < registro.fecha_inicio:
                        raise ValidationError(f"La tarea '{tarea.nombre}' tiene una fecha de inicio anterior a la fecha de inicio del proyecto.")
                    if tarea.fecha_fin and tarea.fecha_fin > registro.fecha_fin:
              
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
    empleado_id = fields.Many2one('creativeminds.empleado', string='Empleado')
    proyecto_id = fields.Many2one('creativeminds.ai', string='Proyecto')
    
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

    proyecto_id = fields.Many2one('creativeminds.ai', string='Proyecto')
    nombre = fields.Char(string='Nombre de la Tarea', required=True)
    descripcion = fields.Text(string='Descripción')
    responsable_id = fields.Many2one('res.users', string='Responsable')
    fecha_comienzo = fields.Date(string='Fecha de Inicio')
    fecha_final = fields.Date(string='Fecha de Finalización')
    estado = fields.Selection([
        ('pendiente', 'Por hacer'),
        ('en_progreso', 'En progreso'),
        ('completada', 'Completada'),
    ], string='Estado', default='pendiente')


class KPI(models.Model):
    _name = 'creativeminds.kpi'
    _description = 'Indicadores Clave de Rendimiento'

    proyecto_id = fields.Many2one('creativeminds.ai', string='Proyecto')
    nombre = fields.Char(string='Nombre del KPI', required=True)
    valor = fields.Float(string='Valor')
    objetivo = fields.Float(string='Objetivo')

class Empleado(models.Model):
    _name = 'creativeminds.empleado'
    _description = 'Empleados del Proyecto'


    nombre = fields.Char(string='Nombre', required=True)
    proyecto_id = fields.Many2many('creativeminds.ai', string='Proyectos')
    departamento = fields.Char(string='Departamento')
    puesto = fields.Char(string='Puesto')


class Equipo(models.Model):
    _name = 'creativeminds.equipo'
    _description = 'Equipos de Trabajo'

    nombre = fields.Char(string='Nombre', required=True)


class PanelDeControl(models.Model):
    _name = 'creativeminds.control.panel'
    _description = 'Panel de Control'

    nombre = fields.Char(string='Nombre', required=True)

    proyectos_ids = fields.Many2many('creativeminds.ai', string='Proyectos en el Panel')
