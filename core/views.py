from calendar import monthrange
from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import (
    EntradaPresencialForm,
    HomeOfficeForm,
    LoginForm,
    RejeicaoForm,
    RelatorioForm,
    SaidaPresencialForm,
)
from .models import Estagiario, Registro, get_estagiario, is_supervisor


class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home(request):
    if is_supervisor(request.user) and not get_estagiario(request.user):
        return redirect('dashboard_supervisor')
    if get_estagiario(request.user):
        estagiario = get_estagiario(request.user)
        turno_aberto = estagiario.registros.filter(
            tipo=Registro.Tipo.PRESENCIAL,
            saida__isnull=True,
        ).first()
        return render(request, 'core/home.html', {
            'estagiario': estagiario,
            'turno_aberto': turno_aberto,
            'horas_realizadas': estagiario.horas_realizadas(),
            'horas_previstas': estagiario.carga_total,
        })
    messages.error(request, 'Seu usuário não está vinculado a um perfil de estagiário ou supervisor.')
    return redirect('login')


@login_required
def dashboard_estagiario(request):
    estagiario = get_estagiario(request.user)
    if not estagiario:
        return redirect('dashboard_supervisor')

    registros = estagiario.registros.all()[:10]
    turno_aberto = estagiario.registros.filter(
        tipo=Registro.Tipo.PRESENCIAL,
        saida__isnull=True,
    ).first()
    pendentes_count = estagiario.registros.filter(
        tipo=Registro.Tipo.HOME_OFFICE,
        status=Registro.Status.PENDENTE,
    ).count()
    context = {
        'estagiario': estagiario,
        'horas_previstas': estagiario.carga_total,
        'horas_realizadas': estagiario.horas_realizadas(),
        'horas_presenciais': estagiario.horas_presenciais(),
        'horas_home_office': estagiario.horas_home_office(),
        'horas_restantes': estagiario.horas_restantes(),
        'registros': registros,
        'turno_aberto': turno_aberto,
        'pendentes_count': pendentes_count,
    }
    return render(request, 'core/dashboard_estagiario.html', context)


@login_required
def presencial_entrada(request):
    estagiario = get_estagiario(request.user)
    if not estagiario:
        return redirect('dashboard_supervisor')

    if request.method == 'POST':
        form = EntradaPresencialForm(request.POST)
        if form.is_valid():
            registro = form.save(commit=False)
            registro.estagiario = estagiario
            registro.tipo = Registro.Tipo.PRESENCIAL
            registro.save()
            messages.success(request, f'Entrada registrada às {registro.entrada.strftime("%H:%M")}.')
            return redirect('presencial_saida', pk=registro.pk)
    else:
        form = EntradaPresencialForm(initial={'data': timezone.localdate()})

    return render(request, 'core/presencial_entrada.html', {'form': form})


@login_required
def presencial_saida(request, pk):
    estagiario = get_estagiario(request.user)
    if not estagiario:
        return redirect('dashboard_supervisor')

    registro = get_object_or_404(
        Registro,
        pk=pk,
        estagiario=estagiario,
        tipo=Registro.Tipo.PRESENCIAL,
    )

    if registro.saida:
        messages.info(request, 'Saída já registrada para este turno.')
        return redirect('dashboard_estagiario')

    if request.method == 'POST':
        form = SaidaPresencialForm(request.POST)
        if form.is_valid():
            registro.saida = form.cleaned_data['saida']
            registro.save()
            messages.success(
                request,
                f'Saída registrada. Total: {registro.horas} hora(s).',
            )
            return redirect('dashboard_estagiario')
    else:
        form = SaidaPresencialForm()

    return render(request, 'core/presencial_saida.html', {'form': form, 'registro': registro})


@login_required
def home_office_registro(request):
    estagiario = get_estagiario(request.user)
    if not estagiario:
        return redirect('dashboard_supervisor')

    if request.method == 'POST':
        form = HomeOfficeForm(request.POST, request.FILES)
        if form.is_valid():
            registro = form.save(commit=False)
            registro.estagiario = estagiario
            registro.tipo = Registro.Tipo.HOME_OFFICE
            registro.status = Registro.Status.PENDENTE
            registro.save()
            messages.success(request, 'Registro enviado. Aguardando aprovação do supervisor.')
            return redirect('dashboard_estagiario')
    else:
        form = HomeOfficeForm(initial={'data': timezone.localdate()})

    return render(request, 'core/home_office_registro.html', {'form': form})


@login_required
def dashboard_supervisor(request):
    if not is_supervisor(request.user):
        return redirect('dashboard_estagiario')

    filtro = request.GET.get('filtro', 'todos')
    estagiarios = Estagiario.objects.filter(supervisor=request.user)

    if not request.user.is_staff:
        pass
    elif request.GET.get('supervisor') == 'todos':
        estagiarios = Estagiario.objects.all()

    lista = []
    for est in estagiarios:
        registros = Registro.filtrar_por_tipo_status(est.registros.all(), filtro)
        horas = sum(r.horas_efetivas for r in registros) if filtro != 'todos' else est.horas_realizadas()
        lista.append({'estagiario': est, 'horas': horas})

    pendentes = Registro.objects.filter(
        estagiario__supervisor=request.user,
        tipo=Registro.Tipo.HOME_OFFICE,
        status=Registro.Status.PENDENTE,
    ).select_related('estagiario')

    if request.user.is_staff:
        pendentes = Registro.objects.filter(
            tipo=Registro.Tipo.HOME_OFFICE,
            status=Registro.Status.PENDENTE,
        ).select_related('estagiario')

    context = {
        'lista': lista,
        'filtro': filtro,
        'pendentes': pendentes,
        'filtros': [
            ('todos', 'Todos'),
            ('presencial', 'Presencial'),
            ('home_office', 'Home Office'),
            ('pendentes', 'Pendentes'),
            ('aprovados', 'Aprovados'),
        ],
    }
    return render(request, 'core/dashboard_supervisor.html', context)


@login_required
def aprovar_registro(request, pk):
    if not is_supervisor(request.user):
        return redirect('dashboard_estagiario')

    registro = get_object_or_404(
        Registro,
        pk=pk,
        tipo=Registro.Tipo.HOME_OFFICE,
        status=Registro.Status.PENDENTE,
    )

    if not request.user.is_staff and registro.estagiario.supervisor != request.user:
        messages.error(request, 'Você não tem permissão para aprovar este registro.')
        return redirect('dashboard_supervisor')

    registro.status = Registro.Status.APROVADO
    registro.save()
    messages.success(request, f'Registro de {registro.estagiario.nome} aprovado.')
    return redirect('dashboard_supervisor')


@login_required
def rejeitar_registro(request, pk):
    if not is_supervisor(request.user):
        return redirect('dashboard_estagiario')

    registro = get_object_or_404(
        Registro,
        pk=pk,
        tipo=Registro.Tipo.HOME_OFFICE,
        status=Registro.Status.PENDENTE,
    )

    if not request.user.is_staff and registro.estagiario.supervisor != request.user:
        messages.error(request, 'Você não tem permissão para rejeitar este registro.')
        return redirect('dashboard_supervisor')

    if request.method == 'POST':
        form = RejeicaoForm(request.POST)
        if form.is_valid():
            registro.status = Registro.Status.REJEITADO
            registro.observacao = form.cleaned_data['observacao']
            registro.save()
            messages.warning(request, f'Registro de {registro.estagiario.nome} rejeitado.')
            return redirect('dashboard_supervisor')
    else:
        form = RejeicaoForm()

    return render(request, 'core/rejeitar_registro.html', {'form': form, 'registro': registro})


@login_required
def historico(request):
    estagiario = get_estagiario(request.user)
    if not estagiario:
        if is_supervisor(request.user):
            estagiario_id = request.GET.get('estagiario')
            if estagiario_id:
                estagiario = get_object_or_404(Estagiario, pk=estagiario_id)
            else:
                return redirect('dashboard_supervisor')
        else:
            return redirect('login')

    filtro = request.GET.get('filtro', 'todos')
    registros = Registro.filtrar_por_tipo_status(estagiario.registros.all(), filtro)

    context = {
        'estagiario': estagiario,
        'registros': registros,
        'filtro': filtro,
        'filtros': [
            ('todos', 'Todos'),
            ('presencial', 'Presencial'),
            ('home_office', 'Home Office'),
            ('pendentes', 'Pendentes'),
            ('aprovados', 'Aprovados'),
        ],
    }
    return render(request, 'core/historico.html', context)


@login_required
def relatorios(request):
    estagiario = get_estagiario(request.user)
    supervisor_mode = is_supervisor(request.user) and not estagiario

    hoje = timezone.localdate()
    initial = {'mes': hoje.month, 'ano': hoje.year}

    if request.method == 'POST':
        form = RelatorioForm(request.POST)
        if form.is_valid():
            mes = form.cleaned_data['mes']
            ano = form.cleaned_data['ano']
            export = request.POST.get('export')

            if supervisor_mode:
                est_id = request.POST.get('estagiario_id')
                if est_id:
                    target = get_object_or_404(Estagiario, pk=est_id)
                else:
                    messages.error(request, 'Selecione um estagiário.')
                    return render(request, 'core/relatorios.html', {
                        'form': form,
                        'supervisor_mode': True,
                        'estagiarios': Estagiario.objects.all(),
                    })
            else:
                target = estagiario

            inicio = date(ano, mes, 1)
            fim = date(ano, mes, monthrange(ano, mes)[1])
            dados = Registro.horas_por_periodo(target, inicio, fim)
            registros = target.registros.filter(data__gte=inicio, data__lte=fim)

            if export == 'pdf':
                return _exportar_pdf(target, mes, ano, dados, registros)
            if export == 'excel':
                return _exportar_excel(target, mes, ano, dados, registros)

            context = {
                'form': form,
                'estagiario': target,
                'mes': mes,
                'ano': ano,
                'dados': dados,
                'registros': registros,
                'supervisor_mode': supervisor_mode,
                'estagiarios': Estagiario.objects.all() if supervisor_mode else None,
            }
            return render(request, 'core/relatorios.html', context)
    else:
        form = RelatorioForm(initial=initial)

    context = {
        'form': form,
        'supervisor_mode': supervisor_mode,
        'estagiarios': Estagiario.objects.all() if supervisor_mode else None,
    }
    return render(request, 'core/relatorios.html', context)


def _exportar_pdf(estagiario, mes, ano, dados, registros):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f'Relatório de Horas - {estagiario.nome}', styles['Title']))
    elements.append(Paragraph(f'Período: {mes:02d}/{ano}', styles['Normal']))
    elements.append(Spacer(1, 0.5 * cm))

    resumo = [
        ['Presencial', 'Home Office', 'Total'],
        [f'{dados["presencial"]} h', f'{dados["home_office"]} h', f'{dados["total"]} h'],
    ]
    table = Table(resumo, colWidths=[5 * cm, 5 * cm, 5 * cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 1 * cm))

    if registros.exists():
        elements.append(Paragraph('Detalhamento', styles['Heading2']))
        detalhe = [['Data', 'Tipo', 'Horas', 'Status']]
        for r in registros:
            detalhe.append([
                r.data.strftime('%d/%m/%Y'),
                r.get_tipo_display(),
                str(r.horas or '-'),
                r.get_status_display(),
            ])
        t2 = Table(detalhe, colWidths=[3 * cm, 4 * cm, 3 * cm, 4 * cm])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#64748b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(t2)

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_{estagiario.id}_{mes}_{ano}.pdf"'
    return response


def _exportar_excel(estagiario, mes, ano, dados, registros):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Relatório'

    ws.append(['Estagiário', estagiario.nome])
    ws.append(['Período', f'{mes:02d}/{ano}'])
    ws.append([])
    ws.append(['Presencial (h)', 'Home Office (h)', 'Total (h)'])
    ws.append([float(dados['presencial']), float(dados['home_office']), float(dados['total'])])
    ws.append([])
    ws.append(['Data', 'Tipo', 'Entrada', 'Saída', 'Horas', 'Status', 'Descrição'])

    for r in registros:
        ws.append([
            r.data.strftime('%d/%m/%Y'),
            r.get_tipo_display(),
            r.entrada.strftime('%H:%M') if r.entrada else '',
            r.saida.strftime('%H:%M') if r.saida else '',
            float(r.horas) if r.horas else '',
            r.get_status_display(),
            r.descricao[:200] if r.descricao else '',
        ])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="relatorio_{estagiario.id}_{mes}_{ano}.xlsx"'
    return response
