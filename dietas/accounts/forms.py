from django import forms
from .models import DatosPersonales, Dieta, DetalleDieta
from django.forms import formset_factory
from django.forms.models import formset_factory
from django.contrib.auth.forms import PasswordChangeForm

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, label="Nombre de usuario")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")

class CustomPasswordChangeForm(PasswordChangeForm):
    class Meta:
        fields = ['old_password', 'new_password1', 'new_password2']


class DatosPersonalesForm(forms.ModelForm):
    class Meta:
        model = DatosPersonales
        fields = ['tipo_doc', 'num_identificacion', 'nombres', 'apellidos', 'fecha_nac', 'observaciones', 'cama', 'cuarentena', 'activa']

    fecha_nac = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    def clean_num_identificacion(self):
        num_identificacion = self.cleaned_data.get("num_identificacion")

        # Validar formato
        if len(num_identificacion) != 10:
            raise forms.ValidationError("El número de identificación debe tener 10 dígitos.")

        if not num_identificacion.isdigit():
            raise forms.ValidationError("El número de identificación debe contener solo dígitos.")

        coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        suma = 0
        for i in range(9):
            producto = int(num_identificacion[i]) * coeficientes[i]
            if producto > 9:
                producto -= 9
            suma += producto

        digito_verificador = 10 - (suma % 10)
        if digito_verificador == 10:
            digito_verificador = 0

        if digito_verificador != int(num_identificacion[9]):
            raise forms.ValidationError("El número de identificación no es válido.")

        # Validar unicidad
        if DatosPersonales.objects.filter(num_identificacion=num_identificacion).exists():
            raise forms.ValidationError("El número de identificación ya está registrado. Por favor, ingrese un número único.")

        return num_identificacion
    

class DietaForm(forms.ModelForm):
    class Meta:
        model = Dieta
        fields = ['paciente', 'acompanante', 'npo', 'indicaciones', 'restricciones']

    def clean(self):
        cleaned_data = super().clean()
        paciente = cleaned_data.get('paciente')

        if paciente and not paciente.cama:
            raise forms.ValidationError("El paciente seleccionado no tiene una cama asignada. Por favor, asigne una cama al paciente antes de crear la dieta.")
        return cleaned_data

PERIODOS_CHOICES = [
    ('D', 'D'),
    ('CM', 'CM'),
    ('A', 'A'),
    ('CV', 'CV'),
    ('M', 'M'),
    ('TODOS', 'TODOS')
]

FRECUENCIA_CHOICES = [
        ('F1', 'F1'),
        ('F2', 'F2'),
        ('F3', 'F3'),
        ('F4', 'F4'),
        ('F5', 'F5'),
        ('F6', 'F6'),
        ('F7', 'F7'),
        ('F8', 'F8'),
        ('F9', 'F9'),
        ('F10', 'F10'),
        ('F11', 'F11'),
        ('F12', 'F12'),
        ('F13', 'F13'),
        ('F14', 'F14'),
        ('F15', 'F15'),
        ('F16', 'F16'),
        ('F17', 'F17'),
        ('F18', 'F18'),
        ('F19', 'F19'),
        ('F20', 'F20'),
        ('F21', 'F21'),
        ('F22', 'F22'),
        ('F23', 'F23'),
        ('F24', 'F24'),
]

class DetalleDietaForm(forms.ModelForm):

    periodos = forms.MultipleChoiceField(
        choices=PERIODOS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Períodos"  # Puedes personalizar la etiqueta
    )

    frecuencia = forms.MultipleChoiceField(
        choices=FRECUENCIA_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Frecuencia"  # Puedes personalizar la etiqueta
    )

    class Meta:
        model = DetalleDieta
        fields = ['tipo_dieta', 'descripcion_dieta', 'descripcion_biberon', 'medidas', 
                  'medidas_cantidad', 'periodos', 'frecuencia']
    
    def __init__(self, *args, **kwargs):
        super(DetalleDietaForm, self).__init__(*args, **kwargs)
        # Establece SIEMPRE los widgets Select con las opciones correspondientes
        self.fields['descripcion_dieta'].widget = forms.Select(choices=DetalleDieta.DIETA_CHOICES)
        self.fields['descripcion_biberon'].widget = forms.Select(choices=DetalleDieta.BIBERON_CHOICES)
        
    def clean(self):
        cleaned_data = super().clean()
        tipo_dieta = cleaned_data.get('tipo_dieta')
        descripcion_dieta = cleaned_data.get('descripcion_dieta')
        descripcion_biberon = cleaned_data.get('descripcion_biberon')

        if tipo_dieta == 'Dieta' and not descripcion_dieta:
            self.add_error('descripcion_dieta', 'Este campo es requerido para el tipo de dieta seleccionado.')
        elif tipo_dieta == 'Biberones' and not descripcion_biberon:
            self.add_error('descripcion_biberon', 'Este campo es requerido para el tipo de biberón seleccionado.')
        elif tipo_dieta == 'Ninguno':
            pass
        elif tipo_dieta == 'Dieta' and descripcion_biberon and descripcion_biberon != 'Ninguno':
            self.add_error('descripcion_biberon', 'Este campo debe estar en "Ninguno" para el tipo de dieta seleccionado.')
        elif tipo_dieta == 'Biberones' and descripcion_dieta and descripcion_dieta != 'Ninguno':
            self.add_error('descripcion_dieta', 'Este campo debe estar en "Ninguno" para el tipo de biberón seleccionado.')

        # No es necesario manipular 'periodos' aquí, Django lo hará automáticamente
        return cleaned_data
      
DietaDetalleFormSet = formset_factory(DetalleDietaForm, extra=1)