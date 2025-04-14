from django.db import models
from datetime import date
import logging
from django.db.models import Q

logger = logging.getLogger(__name__)

class DatosPersonales(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('CC', 'Cédula de Ciudadanía'),
        ('PA', 'Pasaporte'),
    ]

    CAMA_CHOICES = [
        ('T/O', 'Terapia Ocupacional'),
        ('INF', 'Infantil'),
        ('CL2', 'Clínica Nivel 2'),
        ('CL1', 'Clínica Nivel 1'),
        ('ONC', 'Oncología'),
        ('NEU', 'Neurología'),
        ('UNEO', 'Unidad Neonatal'),
        ('CARD', 'Cardiología'),
        ('QUEM', 'Unidad de Quemados'),
        ('UCI', 'Unidad de Cuidados Intensivos'),
        ('HDD', 'Hospitalización Domiciliaria'),
        ('CIR', 'Cirugía'),
        ('EMER', 'Emergencias'),
        ('DIA', 'Diálisis'),
        ('OAMB', 'Otros Ambulatorios'),
    ]

    CUARENTENA_CHOICES = [
        ('Ninguno', 'Ninguno'),
        ('Aislamiento de gotas', 'Aislamiento de gotas'),
        ('Aislamiento por aire', 'Aislamiento por aire'),
        ('Aislamiento protector', 'Aislamiento protector'),
        ('Código Púrpura', 'Código Púrpura'),
        ('Viruela del mono', 'Viruela del mono'),
    ]

    tipo_doc = models.CharField(max_length=2, choices=TIPO_DOCUMENTO_CHOICES)
    num_identificacion = models.CharField(max_length=20, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nac = models.DateField()
    observaciones = models.TextField(blank=True, null=True)
    cama = models.CharField(max_length=10, choices=CAMA_CHOICES, blank=True, null=True)
    cuarentena = models.CharField(max_length=30, choices=CUARENTENA_CHOICES, blank=True, null=True)
    activa = models.BooleanField(default=True)
    fecha_actual = models.DateField(auto_now_add=False)

    def __str__(self):
        return f"{self.nombres} {self.apellidos} - {self.num_identificacion}"

    @property
    def edad(self):
        hoy = date.today()
        años = hoy.year - self.fecha_nac.year
        meses = hoy.month - self.fecha_nac.month
        dias = hoy.day - self.fecha_nac.day

        if dias < 0:
            meses -= 1
            dias += 30

        if meses < 0:
            años -= 1
            meses += 12

        return f"{años} años, {meses} meses y {dias} días"

class Dieta(models.Model):
    paciente = models.ForeignKey(DatosPersonales, on_delete=models.CASCADE)
    acompanante = models.CharField(max_length=100, blank=True, null=True)
    npo = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.paciente.cama:
            raise ValueError("El paciente no tiene cama asignada, no se puede crear la dieta.")
        super(Dieta, self).save(*args, **kwargs)

    def __str__(self):
        return f"Dieta de {self.paciente.nombres} {self.paciente.apellidos}"

class DetalleDieta(models.Model):
    TIPO_DIETA_CHOICES = [
        ('Dieta', 'Dieta'),
        ('Biberones', 'Biberones')
    ]

    DIETA_CHOICES = [
        ('Ninguno', 'Ninguno'),
        ('Madre Lactante', 'Madre Lactante'),
        ('Familiar', 'Familiar'),
        ('General', 'General'),
        ('Hipocalórica', 'Hipocalórica'),
        ('Blanda Mecánica', 'Blanda Mecánica'),
        ('Liquida Amplia', 'Liquida Amplia'),
        ('Cetogenica', 'Cetogenica'),
        ('Alta en Fibra', 'Alta en Fibra'),
        ('Blanda Astringente', 'Blanda Astringente'),
        ('Hipercalórica', 'Hipercalórica'),
        ('Diabético', 'Diabético'),
        ('Hiperproteica', 'Hiperproteica'),
        ('Hiposódica', 'Hiposódica'),
        ('Complementaria', 'Complementaria'),
        ('Liquida Estricta', 'Liquida Estricta'),
        ('Tratamiento Dialítico', 'Tratamiento Dialítico'),
        ('Blanda Neutropénica', 'Blanda Neutropénica'),
        ('Blanda Hipograsa', 'Blanda Hipograsa'),
    ]

    BIBERON_CHOICES = [
        ('Ninguno', 'Ninguno'),
        ('Leche Entera', 'Leche Entera'),
        ('Agua Estéril', 'Agua Estéril'),
        ('Formula 75', 'Formula 75'),
        ('Formula Maternizada', 'Formula Maternizada'),
        ('Enteral Artesanal isocalórica', 'Enteral Artesanal isocalórica (1 KCAL/ML)'),
        ('Enteral Artesanal Hipercalórica-Hiperproteica', 'Enteral Artesanal Hipercalórica-Hiperproteica (1,5 KCAL/ML)'),
        ('Jugo', 'Jugo'),
        ('Papilla', 'Papilla'),
        ('Cereal en Agua', 'Cereal en Agua'),
        ('Cereal en Leche', 'Cereal en Leche'),
        ('Formula 100', 'Formula 100'),
        ('Suplementos Alimenticios', 'Suplementos Alimenticios'),
        ('Enteral Artesanal Hipercalórica-Normoproteica', 'Enteral Artesanal Hipercalórica-Normoproteica (1,2 KCAL/ML)'),
        ('Yogurt', 'Yogurt'),
        ('Infusión de Ciruela', 'Infusión de Ciruela'),
        ('Litros de Agua', 'Litros de Agua'),
    ]

    MEDIDAS_CHOICES = [
        ('Unidad', 'Unidad'),
        ('Onzas', 'Onzas')
    ]

    PERIODOS_CHOICES = [
    ('D', 'D'),
    ('CM', 'CM'),
    ('A', 'A'),
    ('CV', 'CV'),
    ('M', 'M'),
    ('CN', 'CN')
    ]

    dieta = models.ForeignKey(Dieta, on_delete=models.CASCADE, related_name="detalles")
    tipo_dieta = models.CharField(max_length=20, choices=TIPO_DIETA_CHOICES)
    descripcion_biberon = models.CharField(max_length=100, choices=BIBERON_CHOICES, null=True, blank=True)
    descripcion_dieta = models.CharField(max_length=100, choices=DIETA_CHOICES, null=True, blank=True)
    medidas = models.CharField(max_length=20, choices=MEDIDAS_CHOICES, null=True, blank=True)
    medidas_cantidad = models.PositiveIntegerField(null=True, blank=True)
    periodos = models.CharField(max_length=100, null=True, blank=True)
    frecuencia = models.CharField(max_length=100, null=True, blank=True)
    fecha_det_dieta = models.DateField(verbose_name='Fecha del Detalle')
    indicaciones = models.CharField(max_length=100, blank=False, null=True)
    restricciones = models.CharField(max_length=100, blank=False, null=True)

    def save(self, *args, **kwargs):
        if self.tipo_dieta == 'Dieta' and self.descripcion_dieta not in [choice[0] for choice in self.DIETA_CHOICES]:
            raise ValueError("Descripción de dieta inválida para el tipo 'Dieta'")
        if self.tipo_dieta == 'Biberones' and self.descripcion_dieta not in [choice[0] for choice in self.BIBERON_CHOICES]:
            raise ValueError("Descripción de dieta inválida para el tipo 'Biberones'")
        super(DetalleDieta, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_dieta_display()} - {self.descripcion_dieta}"