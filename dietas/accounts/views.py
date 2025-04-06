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

    reporte_frecuencias = []
    periodos_ordenados = ['AMUERZO', 'COL.PM', 'MERIENDA', 'COL.NOC', 'DESAYUNO', 'COL.AM']

    if fecha_inicio_str and fecha_fin_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()

            detalle_dietas = DetalleDieta.objects.filter(
                dieta__paciente__fecha_actual__range=(fecha_inicio, fecha_fin)
            ).values('descripcion_dieta', 'frecuencia')

            frecuencia_periodo_map = {
                'F1': 'COL.AM', 'F2': 'COL.AM', 'F3': 'COL.AM', 'F4': 'COL.AM',
                'F5': 'DESAYUNO', 'F6': 'DESAYUNO', 'F7': 'DESAYUNO', 'F8': 'DESAYUNO',
                'F9': 'ALMUERZO', 'F10': 'ALMUERZO', 'F11': 'ALMUERZO', 'F12': 'ALMUERZO',
                'F13': 'COL.PM', 'F14': 'COL.PM', 'F15': 'COL.PM', 'F16': 'COL.PM',
                'F17': 'COL.NOC', 'F18': 'COL.NOC', 'F19': 'COL.NOC', 'F20': 'COL.NOC',
                'F21': 'MERIENDA', 'F22': 'MERIENDA', 'F23': 'MERIENDA', 'F24': 'MERIENDA',
            }

            reporte_frecuencias_dict = {}
            for detalle in detalle_dietas:
                descripcion_dieta = detalle['descripcion_dieta']
                frecuencias_str = detalle['frecuencia']
                frecuencias_lista = [f.strip().upper() for f in frecuencias_str.split(',')]

                for frecuencia in frecuencias_lista:
                    periodo = frecuencia_periodo_map.get(frecuencia)
                    if periodo:
                        reporte_frecuencias_dict.setdefault(descripcion_dieta, {}).setdefault(periodo, 0)
                        reporte_frecuencias_dict[descripcion_dieta][periodo] += 1

            reporte_frecuencias = []
            for descripcion_dieta, frecuencias in reporte_frecuencias_dict.items():
                reporte_frecuencias.append({'descripcion_dieta': descripcion_dieta, **frecuencias})

            for item in reporte_frecuencias:
                for periodo in periodos_ordenados:
                    item.setdefault(periodo, 0)

        except ValueError:
            messages.error(request, "El formato de las fechas es incorrecto (YYYY-MM-DD).")

    datos_personales = DatosPersonales.objects.all()
    dietas = Dieta.objects.all()

    if fecha_inicio_str and fecha_fin_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            datos_personales = datos_personales.filter(fecha_actual__range=(fecha_inicio, fecha_fin))
            dietas = dietas.filter(paciente__fecha_actual__range=(fecha_inicio, fecha_fin))
        except ValueError:
            pass # El mensaje de error ya se añadió arriba

    total_pacientes = datos_personales.count()
    total_dietas = dietas.count()

    camas_disponibles = DatosPersonales.CAMA_CHOICES
    conteo_camas = []
    for codigo, nombre in camas_disponibles:
        conteo = DatosPersonales.objects.filter(cama=codigo).count()
        conteo_camas.append({'codigo': codigo, 'nombre': nombre, 'conteo': conteo})

    context = {
        'fecha_inicio': fecha_inicio_str if fecha_inicio_str else '',
        'fecha_fin': fecha_fin_str if fecha_fin_str else '',
        'total_pacientes': total_pacientes,
        'total_dietas': total_dietas,
        'camas_disponibles': camas_disponibles,
        'conteo_camas': conteo_camas,
        'reporte_frecuencias': reporte_frecuencias,
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
        datos_personales = DatosPersonales.objects.filter(fecha_actual__range=(fecha_inicio, fecha_fin))
    except ValueError:
        messages.error(request, "El formato de las fechas es incorrecto (YYYY-MM-DD).")
        return redirect('dashboard')

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte_consolidado_{fecha_inicio_str}_a_{fecha_fin_str}.xlsx"'

    writer = pd.ExcelWriter(response, engine='xlsxwriter')

    try:
        # Crear un buffer para el archivo Excel
        buffer = io.BytesIO()
        writer = pd.ExcelWriter(buffer, engine='xlsxwriter')

        # Hoja 1: Datos personales con información de dieta
        data_hoja1 = []
        for paciente in datos_personales:
            dieta = Dieta.objects.filter(paciente=paciente).first()
            detalle = DetalleDieta.objects.filter(dieta=dieta).first() if dieta else None

            data_hoja1.append({
                'Cama': paciente.cama if paciente.cama else '',
                'Numero de Identificacion': paciente.num_identificacion,
                'Nombre': paciente.nombres,
                'Apellido': paciente.apellidos,
                'Fecha_Nac': paciente.fecha_nac.strftime('%Y-%m-%d') if paciente.fecha_nac else '',
                'Acompañante': dieta.acompanante if dieta else '',
                'Fecha_Actual': paciente.fecha_actual.strftime('%Y-%m-%d') if paciente.fecha_actual else '',
                'Periodos': detalle.periodos if detalle else '',
                'Medidas': detalle.medidas if detalle else '',
                'Cantidad': detalle.medidas_cantidad if detalle else '',
                'Frecuencia': detalle.frecuencia if detalle else '',
                'Indicaciones': dieta.indicaciones if dieta else '',
                'Restricciones': dieta.restricciones if dieta else '',
            })
        df_hoja1 = pd.DataFrame(data_hoja1)
        df_hoja1.to_excel(writer, sheet_name='Datos Pacientes', index=False)

        # Hoja 2: Listado de todas las dietas por medidas y cantidad
        dietas_detalle = DetalleDieta.objects.filter(dieta__paciente__fecha_actual__range=(fecha_inicio, fecha_fin)).values('medidas', 'medidas_cantidad').order_by('medidas')
        df_hoja2 = pd.DataFrame(list(dietas_detalle))
        df_hoja2.rename(columns={'medidas': 'Medida', 'medidas_cantidad': 'Cantidad'}, inplace=True)
        df_hoja2.to_excel(writer, sheet_name='Listado Dietas Medida Cantidad', index=False)

        # Hoja 3: Lista de dietas con el conteo por pacientes y tipo de dieta
        subquery_descripcion_dieta = DetalleDieta.objects.filter(dieta=OuterRef('id')).values('descripcion_dieta')[:1]

        conteo_dietas_con_descripcion = Dieta.objects.filter(paciente__fecha_actual__range=(fecha_inicio, fecha_fin)).annotate(
            total_dietas=Count('id'),
            descripcion_dieta=Subquery(subquery_descripcion_dieta)
        ).values(
            'descripcion_dieta',
            'total_dietas'  # Ya estamos anotando el total, no necesitamos 'id' en values
        ).order_by('paciente__num_identificacion')

        df_hoja3 = pd.DataFrame(list(conteo_dietas_con_descripcion))
        df_hoja3.rename(columns={
            'descripcion_dieta': 'Descripcion de dieta',
            'total_dietas': 'Conteo Dietas'  # Corregí el nombre de la columna
        }, inplace=True)
        df_hoja3.to_excel(writer, sheet_name='Conteo Dietas por Paciente', index=False)

        # Hoja 4: Lista de biberón con el conteo por pacientes
        conteo_biberon_paciente = DetalleDieta.objects.filter(dieta__paciente__fecha_actual__range=(fecha_inicio, fecha_fin)).values('dieta__paciente__num_identificacion', 'dieta__paciente__nombres', 'dieta__paciente__apellidos', 'descripcion_biberon').annotate(total_biberon=Count('id')).order_by('dieta__paciente__num_identificacion', 'descripcion_biberon')
        df_hoja4 = pd.DataFrame(list(conteo_biberon_paciente))
        df_hoja4.rename(columns={'descripcion_biberon': 'Biberon', 'total_biberon': 'Conteo Biberon'}, inplace=True)
        df_hoja4.to_excel(writer, sheet_name='Conteo Biberon por Paciente', index=False)

        # Hoja 5: Conteo de frecuencias por descripción de dieta y periodo
        detalle_dietas = DetalleDieta.objects.filter(dieta__paciente__fecha_actual__range=(fecha_inicio, fecha_fin)).values('tipo_dieta', 'frecuencia')

        frecuencia_periodo_map = {
            'F1': 'COL.AM', 'F2': 'COL.AM', 'F3': 'COL.AM', 'F4': 'COL.AM',
            'F5': 'DESAYUNO', 'F6': 'DESAYUNO', 'F7': 'DESAYUNO', 'F8': 'DESAYUNO',
            'F9': 'ALMUERZO', 'F10': 'ALMUERZO', 'F11': 'ALMUERZO', 'F12': 'ALMUERZO',
            'F13': 'COL.PM', 'F14': 'COL.PM', 'F15': 'COL.PM', 'F16': 'COL.PM',
            'F17': 'COL.NOC', 'F18': 'COL.NOC', 'F19': 'COL.NOC', 'F20': 'COL.NOC',
            'F21': 'MERIENDA', 'F22': 'MERIENDA', 'F23': 'MERIENDA', 'F24': 'MERIENDA',
        }

        reporte_frecuencias = {}
        for detalle in detalle_dietas:
            tipo_dieta = detalle['tipo_dieta']
            frecuencias_str = detalle['frecuencia']
            frecuencias_lista = [f.strip().upper() for f in frecuencias_str.split(',')]

            for frecuencia in frecuencias_lista:
                periodo = frecuencia_periodo_map.get(frecuencia)
                if periodo:
                    reporte_frecuencias.setdefault(tipo_dieta, {}).setdefault(periodo, 0)
                    reporte_frecuencias[tipo_dieta][periodo] += 1

        data_hoja5 = []
        periodos_ordenados = ['AMUERZO', 'COL.PM', 'MERIENDA', 'COL.NOC', 'DESAYUNO', 'COL.AM']
        for tipo, frecuencias_por_periodo in reporte_frecuencias.items():
            row = {'Descripcion Dieta': tipo}
            for periodo in periodos_ordenados:
                row[periodo] = frecuencias_por_periodo.get(periodo, 0)
            data_hoja5.append(row)

        df_hoja5 = pd.DataFrame(data_hoja5).fillna(0)
        df_hoja5.to_excel(writer, sheet_name='Conteo Frecuencias Dieta', index=False)

        writer.close()

        # Crear la respuesta HTTP
        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="reporte_dietas_{fecha_inicio}_a_{fecha_fin}.xlsx"'
        return response

    except Exception as e:
        # Loguear el error para depuración
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
    dieta = get_object_or_404(Dieta, pk=dieta_id)
    detalles = DetalleDieta.objects.filter(dieta=dieta)
    form_detalle = DetalleDietaForm()

    if request.method == 'POST':
        if 'agregar_detalle' in request.POST:
            form_detalle = DetalleDietaForm(request.POST)
            if form_detalle.is_valid():
                detalle = form_detalle.save(commit=False)
                detalle.dieta = dieta
                detalle.save()
                messages.success(request, "Detalle de dieta guardado correctamente.")
                return redirect('detalle_dieta', dieta_id=dieta_id)
            else:
                messages.error(request, "Error al guardar detalle de dieta.")

    return render(request, 'accounts/detalle_dieta.html', {
        'form_detalle': form_detalle,
        'dieta': dieta,
        'detalles': detalles
    })

@login_required
def editar_detalle_dieta(request, detalle_id):
    detalle = get_object_or_404(DetalleDieta, id=detalle_id)
    form_detalle = DetalleDietaForm(instance=detalle)

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