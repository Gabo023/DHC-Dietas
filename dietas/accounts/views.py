import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from datetime import date
from .forms import LoginForm, DatosPersonalesForm, DietaForm, DetalleDietaForm, DietaDetalleFormSet
from .models import DatosPersonales, DetalleDieta, Dieta
from django.db.models import Q
import logging
from django.db.models import Count
import pandas as pd
from django.http import HttpResponse
from django.views import View
from django.utils import timezone
from datetime import datetime
from django.db.models import OuterRef, Subquery
import io
from django.db.models import F

logger = logging.getLogger(__name__)

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Credenciales incorrectas')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return render(request, 'Index.html')

@login_required
def cambiar_clave(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Importante para mantener la sesión activa
            messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
            return redirect('perfil_usuario')  # Redirige a la página de perfil (ajusta la URL)
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/cambiar_clave.html', {'form': form})

@login_required
def perfil_usuario(request):
    return render(request, 'accounts/perfil_usuario.html') # Crea esta plantilla

@login_required
def dashboard(request):
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

    detalles = DetalleDieta.objects.none()
    reporte_periodos = []
    periodos_ordenados = ['D', 'CM', 'A', 'CV', 'M']

    if fecha_inicio_str and fecha_fin_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()

            # Obtener detalles en rango
            detalles = DetalleDieta.objects.filter(fecha_det_dieta__range=(fecha_inicio, fecha_fin))

            # Obtener datos personales relacionados a esos detalles
            datos_personales = DatosPersonales.objects.filter(
                dieta__detalledieta__in=detalles
            ).values('descripcion_dieta', 'periodos')

            # Construcción del reporte por periodos
            reporte_periodos_dict = {}
            for detalle in datos_personales:
                descripcion_dieta = detalle['descripcion_dieta']
                periodos_str = detalle['periodos']
                if periodos_str:
                    periodos_lista = [p.strip().upper() for p in periodos_str.split(',')]
                    for periodo in periodos_lista:
                        if periodo in [choice[0] for choice in DetalleDieta.PERIODOS_CHOICES if choice[0] != 'TODOS']:
                            reporte_periodos_dict.setdefault(descripcion_dieta, {}).setdefault(periodo, 0)
                            reporte_periodos_dict[descripcion_dieta][periodo] += 1

            # Convertimos a lista para mostrar en el template
            for descripcion_dieta, periodos_conteo in reporte_periodos_dict.items():
                reporte_periodos.append({'descripcion_dieta': descripcion_dieta, **periodos_conteo})

            # Aseguramos que todos los periodos estén presentes aunque con valor 0
            for item in reporte_periodos:
                for periodo in periodos_ordenados:
                    item.setdefault(periodo, 0)

        except ValueError:
            messages.error(request, "El formato de las fechas es incorrecto (YYYY-MM-DD).")
    else:
        # Si no hay fechas, se toma el día actual por defecto
        hoy = timezone.localdate()
        detalles = DetalleDieta.objects.filter(fecha_det_dieta=hoy)

    # Conteo total de pacientes y dietas
    datos_personales_total = DatosPersonales.objects.all()
    dietas_total = Dieta.objects.all()

    total_pacientes = datos_personales_total.count()
    total_dietas = dietas_total.count()

    # Conteo de camas por tipo
    camas_disponibles = DatosPersonales.CAMA_CHOICES
    conteo_camas = []
    for codigo, nombre in camas_disponibles:
        conteo = datos_personales_total.filter(cama=codigo).count()
        conteo_camas.append({'codigo': codigo, 'nombre': nombre, 'conteo': conteo})

    context = {
        'fecha_inicio': fecha_inicio_str if fecha_inicio_str else '',
        'fecha_fin': fecha_fin_str if fecha_fin_str else '',
        'total_pacientes': total_pacientes,
        'total_dietas': total_dietas,
        'camas_disponibles': camas_disponibles,
        'conteo_camas': conteo_camas,
        'reporte_periodos': reporte_periodos,
        'periodos_ordenados': periodos_ordenados,
    }
    return render(request, 'dashboard.html', context)

@login_required
def generar_reporte_excel(request):
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

    if not fecha_inicio_str or not fecha_fin_str:
        messages.error(request, "Por favor, seleccione un rango de fechas para el reporte.")
        return redirect('dashboard')

    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "El formato de las fechas es incorrecto (YYYY-MM-DD).")
        return redirect('dashboard')

    # Crear un buffer para escribir el archivo en memoria
    buffer = io.BytesIO()
    writer = pd.ExcelWriter(buffer, engine='xlsxwriter')

    try:
        # Hoja 1: Datos personales con información de dieta y detalle
        detalles = DetalleDieta.objects.filter(fecha_det_dieta__range=(fecha_inicio, fecha_fin))

        data_hoja1 = []
        for detalle in detalles.select_related('dieta__paciente'):
            paciente = detalle.dieta.paciente
            dieta = detalle.dieta
            data_hoja1.append({
                'Cama': paciente.cama if paciente.cama else '',
                'Numero de Identificacion': paciente.num_identificacion,
                'Nombre': paciente.nombres,
                'Apellido': paciente.apellidos,
                'Fecha_Nac': paciente.fecha_nac.strftime('%Y-%m-%d') if paciente.fecha_nac else '',
                'Acompañante': dieta.acompanante if dieta else '',
                'Fecha_Creacion': paciente.fecha_actual.strftime('%Y-%m-%d') if paciente.fecha_actual else '',
                'Fecha del Detalle': detalle.fecha_det_dieta.strftime('%Y-%m-%d') if detalle.fecha_det_dieta else '',
                'Periodos': detalle.periodos,
                'Medidas': detalle.medidas,
                'Cantidad': detalle.medidas_cantidad,
                'Frecuencia': detalle.frecuencia,
            })

        df_hoja1 = pd.DataFrame(data_hoja1)
        df_hoja1.to_excel(writer, sheet_name='Datos Pacientes', index=False)

        # Hoja 2: Listado de todas las dietas por medidas y cantidad
        #dietas_detalle = detalles.values('medidas', 'medidas_cantidad').order_by('medidas')
        #df_hoja2 = pd.DataFrame(list(dietas_detalle))
        #df_hoja2.rename(columns={'medidas': 'Medida', 'medidas_cantidad': 'Cantidad'}, inplace=True)
        #df_hoja2.to_excel(writer, sheet_name='Listado Dietas Medida Cantidad', index=False)

        # Hoja 3: Conteo por tipo de dieta
        #dietas_ids = detalles.values_list('dieta_id', flat=True).distinct()
        #dietas = Dieta.objects.filter(id__in=dietas_ids).annotate(
        #    descripcion_dieta=Subquery(
        #        DetalleDieta.objects.filter(dieta=OuterRef('id')).values('descripcion_dieta')[:1]
        #    )
        #).values('descripcion_dieta').annotate(conteo=Count('id'))

        #df_hoja3 = pd.DataFrame(list(dietas))
        #df_hoja3.rename(columns={
        #    'descripcion_dieta': 'Descripcion de dieta',
        #    'conteo': 'Conteo Dietas'
        #}, inplace=True)
        #df_hoja3.to_excel(writer, sheet_name='Conteo Dietas por Tipo', index=False)

        # Hoja 4: Conteo de biberones por paciente
        #biberones = detalles.values(
        #    'dieta__paciente__num_identificacion',
        #    'dieta__paciente__nombres',
        #    'dieta__paciente__apellidos',
        #    'descripcion_biberon'
        #).annotate(total_biberon=Count('id')).order_by(
        #    'dieta__paciente__num_identificacion', 'descripcion_biberon'
        #)

        #df_hoja4 = pd.DataFrame(list(biberones))
        #df_hoja4.rename(columns={
        #    'descripcion_biberon': 'Biberon',
        #    'total_biberon': 'Conteo Biberon',
        #    'dieta__paciente__num_identificacion': 'Identificación',
        #    'dieta__paciente__nombres': 'Nombres',
        #    'dieta__paciente__apellidos': 'Apellidos',
        #}, inplace=True)
        #df_hoja4.to_excel(writer, sheet_name='Conteo Biberon por Paciente', index=False)

        # Finaliza el archivo y lo devuelve

        # Hoja 5: Matriz de descripcion_dieta vs periodos (dividiendo múltiples periodos)
        detalles_periodo = DetalleDieta.objects.filter(
            fecha_det_dieta__range=(fecha_inicio, fecha_fin)
        ).values('descripcion_dieta', 'periodos')

        # Crear DataFrame
        df_periodos = pd.DataFrame(list(detalles_periodo))

        # Eliminar filas sin datos válidos
        df_periodos = df_periodos.dropna(subset=['descripcion_dieta', 'periodos'])

        # Expandir filas con múltiples periodos (separados por coma o lista)
        rows_expandidas = []

        for _, row in df_periodos.iterrows():
            descripcion = row['descripcion_dieta']
            periodos_str = row['periodos']
            # Asegurar que esté en formato lista
            if isinstance(periodos_str, str):
                # Quitar corchetes si vienen como string tipo "['D', 'CM']"
                periodos_str = periodos_str.replace('[', '').replace(']', '').replace("'", "")
                periodos_list = [p.strip().upper() for p in periodos_str.split(',')]
            else:
                periodos_list = []

            for periodo in periodos_list:
                rows_expandidas.append({
                    'descripcion_dieta': descripcion,
                    'periodo': periodo
                })

        df_expandido = pd.DataFrame(rows_expandidas)

            # Crear matriz pivot (conteo de descripcion_dieta vs periodo)
        matriz = pd.pivot_table(
            df_expandido,
            index='descripcion_dieta',
            columns='periodo',
            aggfunc='size',
            fill_value=0
        )

        # Ordenar columnas
        orden_columnas = ['D', 'CM', 'A', 'CV', 'M', 'CN']
        for col in orden_columnas:
            if col not in matriz.columns:
                matriz[col] = 0
        matriz = matriz[orden_columnas]

        # Reset index y exportar
        matriz.reset_index(inplace=True)
        matriz.to_excel(writer, sheet_name='Matriz Dietas x Periodo', index=False)

        writer.close()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="reporte_dietas_{fecha_inicio}_a_{fecha_fin}.xlsx"'
        return response

    except Exception as e:
        print(f"Error al generar el reporte Excel: {e}")
        return HttpResponse(f"Ocurrió un error al generar el reporte: {e}", status=500)


@login_required
def crear_paciente(request):
    if request.method == "POST":
        form = DatosPersonalesForm(request.POST)
        if form.is_valid():
            paciente = form.save()
            messages.success(request, "Paciente creado correctamente.")
            return redirect(reverse('crear_dieta', kwargs={'paciente_id': paciente.id}))
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = DatosPersonalesForm()
    return render(request, 'accounts/form_paciente.html', {'form': form, 'accion': 'Crear'})

@login_required
def actualizar_paciente(request, pk):
    paciente = get_object_or_404(DatosPersonales, pk=pk)
    if request.method == "POST":
        form = DatosPersonalesForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            messages.success(request, "Paciente actualizado correctamente.")
            return redirect('lista_pacientes')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = DatosPersonalesForm(instance=paciente)
    return render(request, 'accounts/form_paciente.html', {'form': form, 'accion': 'Actualizar'})

@login_required
def eliminar_paciente(request, pk):
    paciente = get_object_or_404(DatosPersonales, pk=pk)
    if request.method == "POST":
        paciente.delete()
        messages.success(request, "Paciente eliminado correctamente.")
        return redirect('lista_pacientes')
    return render(request, 'accounts/confirmar_eliminar.html', {'paciente': paciente})

@login_required
def lista_pacientes(request):
    pacientes = DatosPersonales.objects.all()

    nombre_filter = request.GET.get('nombre', '')
    apellido_filter = request.GET.get('apellido', '')
    cama_filter = request.GET.get('cama', '')
    cuarentena_filter = request.GET.get('cuarentena', '')

    if nombre_filter:
        pacientes = pacientes.filter(nombres__icontains=nombre_filter)

    if apellido_filter:
        pacientes = pacientes.filter(apellidos__icontains=apellido_filter)

    if cama_filter:
        pacientes = pacientes.filter(cama__icontains=cama_filter)

    if cuarentena_filter:
        pacientes = pacientes.filter(cuarentena__icontains=cuarentena_filter)

    return render(request, 'accounts/lista_pacientes.html', {'pacientes': pacientes})

@login_required
def obtener_opciones_dieta(request):
    tipo_dieta = request.GET.get('tipo_dieta')
    if tipo_dieta == 'Dieta':
        opciones = DetalleDieta.DIETA_CHOICES
    elif tipo_dieta == 'Biberones':
        opciones = DetalleDieta.BIBERON_CHOICES
    else:
        opciones = []

    data = [{'value': opcion[0], 'label': opcion[1]} for opcion in opciones]
    return JsonResponse(data, safe=False)


logger = logging.getLogger(__name__)
def editar_dieta(request, pk):
    dieta = get_object_or_404(Dieta, pk=pk)
    detalles_dieta = DetalleDieta.objects.filter(dieta=dieta)
    if request.method == 'POST':
        form = DietaForm(request.POST, instance=dieta)
        if form.is_valid():
            form.save()
            messages.success(request, "Dieta actualizada correctamente.")
            return redirect('lista_dietas')  # Asegúrate de que 'lista_dietas' esté definido en tus URLs
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = DietaForm(instance=dieta)
    return render(request, 'accounts/editar_dieta.html', {'form': form, 'dieta': dieta, 'detalles_dieta': detalles_dieta})

@login_required
def eliminar_dieta(request, pk):
    dieta = get_object_or_404(Dieta, pk=pk)

    if request.method == 'POST':
        if 'confirmar_eliminar' in request.POST:
            dieta.delete()
            messages.success(request, f"Dieta eliminada correctamente.")
            return redirect('lista_dietas')  # Redirige a la lista de dietas
        elif 'cancelar_eliminar' in request.POST:
            return redirect('editar_dieta', pk=pk)  # Redirige de vuelta a la edición

    return render(request, 'accounts/eliminar_dieta.html', {'dieta': dieta})

@login_required   
def detalle_dieta(request, dieta_id):
    dieta = get_object_or_404(Dieta, id=dieta_id)
    detalles = DetalleDieta.objects.filter(dieta=dieta)

    if request.method == 'POST':
        form_detalle = DetalleDietaForm(request.POST)
        if form_detalle.is_valid():
            detalle = form_detalle.save(commit=False)
            detalle.dieta = dieta
            try:
                detalle.save()
                messages.success(request, "Detalle de dieta guardado correctamente.")
                return redirect('detalle_dieta', dieta_id=dieta_id)
            except ValueError as e:
                # Captura el error lanzado desde el save() del modelo
                form_detalle.add_error(None, str(e))
                messages.error(request, f"Error al guardar: {e}")
        else:
            messages.error(request, "Formulario inválido. Revisa los campos.")
    else:
        form_detalle = DetalleDietaForm()

    return render(request, 'accounts/detalle_dieta.html', {
        'form_detalle': form_detalle,
        'dieta': dieta,
        'detalles': detalles
    })


@login_required
def editar_detalle_dieta(request, detalle_id):
    detalle = get_object_or_404(DetalleDieta, id=detalle_id)
    form_detalle = DetalleDietaForm(instance=detalle)

    context = {
        'form_detalle': form_detalle,
        'detalle': detalle,
        'fecha_actual': date.today(), # Pasa la fecha actual al contexto
    }

    if request.method == 'POST':
        if 'editar_detalle' in request.POST:
            form_detalle = DetalleDietaForm(request.POST, instance=detalle)
            if form_detalle.is_valid():
                form_detalle.save()
                messages.success(request, "Detalle de dieta editado correctamente.")
                return redirect('editar_detalle_dieta', detalle_id=detalle_id)
            else:
                messages.error(request, "Error al editar detalle de dieta.")

    return render(request, 'accounts/editar_detalle_dieta.html', {
        'form_detalle': form_detalle,
        'detalle': detalle,
    })

@login_required
def eliminar_detalle_dieta(request, detalle_id):
    detalle = get_object_or_404(DetalleDieta, id=detalle_id)
    dieta_id = detalle.dieta.id

    if request.method == 'POST':
        print(f"Eliminando detalle con ID: {detalle_id}")  # Depuración
        detalle.delete()
        messages.success(request, "Detalle de dieta eliminado correctamente.")
        return redirect('editar_dieta', pk=dieta_id)

    print(f"Mostrando confirmación para detalle con ID: {detalle_id}")  # Depuración
    return render(request, 'accounts/confirmar_eliminar_detalle.html', {'detalle': detalle})

@login_required
def crear_dieta(request, paciente_id=None):
    paciente = None
    if paciente_id:
        paciente = get_object_or_404(DatosPersonales, id=paciente_id)

    if request.method == 'POST':
        form = DietaForm(request.POST)
        if form.is_valid():
            dieta = form.save(commit=False)
            if paciente:
                dieta.paciente = paciente
            dieta.save()
            messages.success(request, "Dieta creada correctamente.")
            return redirect('editar_dieta', pk=dieta.id)
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = DietaForm(initial={'paciente': paciente} if paciente else {})

    return render(request, 'accounts/crear_dieta.html', {'form': form, 'paciente': paciente})

@login_required
def lista_dietas(request, pk=None):
    if pk:
        dieta = get_object_or_404(Dieta, pk=pk)
        detalles_dieta = DetalleDieta.objects.filter(dieta=dieta)
        formset = DietaDetalleFormSet(request.POST or None, instance=dieta)
    else:
        formset = DietaDetalleFormSet(request.POST or None)
        detalles_dieta = None

    if request.method == 'POST':
        if formset.is_valid():
            formset.save()
            return redirect('lista_dietas', pk=pk)

    dietas = Dieta.objects.all()
    return render(request, 'accounts/lista_dietas.html', {
        'formset': formset,
        'detalles_dieta': detalles_dieta,
        'dietas': dietas,
    })

def calcular_edad(fecha_nac):
    hoy = date.today()
    años = hoy.year - fecha_nac.year
    meses = hoy.month - fecha_nac.month
    dias = hoy.day - fecha_nac.day

    if dias < 0:
        meses -= 1
        dias += 30
    if meses < 0:
        años -= 1
        meses += 12

    return f"{años} años, {meses} meses y {dias} días"

def buscar_pacientes(request):
    query = request.GET.get('busqueda', '')
    pacientes = DatosPersonales.objects.all()

    if query:
        pacientes = pacientes.filter(
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(cama__icontains=query)
        )

    pacientes_data = [
        {
            'nombre_completo': f"{p.nombres} {p.apellidos}",
            'edad': calcular_edad(p.fecha_nac),
            'cama': p.cama if p.cama else '-',
        }
        for p in pacientes
    ]

    return JsonResponse({'pacientes': pacientes_data})