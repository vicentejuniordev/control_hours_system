from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


class Estagiario(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='estagiario',
        verbose_name='Usuário',
    )
    nome = models.CharField('Nome', max_length=200)
    curso = models.CharField('Curso', max_length=200)
    instituicao = models.CharField('Instituição', max_length=200)
    supervisor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='estagiarios_supervisionados',
        verbose_name='Supervisor',
    )
    carga_total = models.DecimalField(
        'Carga horária total',
        max_digits=6,
        decimal_places=1,
        help_text='Total de horas do estágio',
    )
    carga_semanal = models.DecimalField(
        'Carga horária semanal',
        max_digits=5,
        decimal_places=1,
    )
    inicio = models.DateField('Data de início')
    fim = models.DateField('Data prevista para término')

    class Meta:
        verbose_name = 'Estagiário'
        verbose_name_plural = 'Estagiários'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def horas_presenciais(self):
        total = self.registros.filter(
            tipo=Registro.Tipo.PRESENCIAL,
        ).aggregate(total=Sum('horas'))['total']
        return total or Decimal('0')

    def horas_home_office(self):
        total = self.registros.filter(
            tipo=Registro.Tipo.HOME_OFFICE,
            status=Registro.Status.APROVADO,
        ).aggregate(total=Sum('horas'))['total']
        return total or Decimal('0')

    def horas_realizadas(self):
        return self.horas_presenciais() + self.horas_home_office()

    def horas_restantes(self):
        return max(self.carga_total - self.horas_realizadas(), Decimal('0'))


class Registro(models.Model):
    class Tipo(models.TextChoices):
        PRESENCIAL = 'PRESENCIAL', 'Presencial'
        HOME_OFFICE = 'HOME_OFFICE', 'Home Office'

    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        APROVADO = 'APROVADO', 'Aprovado'
        REJEITADO = 'REJEITADO', 'Rejeitado'

    estagiario = models.ForeignKey(
        Estagiario,
        on_delete=models.CASCADE,
        related_name='registros',
        verbose_name='Estagiário',
    )
    tipo = models.CharField('Tipo', max_length=20, choices=Tipo.choices)
    data = models.DateField('Data')
    entrada = models.TimeField('Hora de entrada', null=True, blank=True)
    saida = models.TimeField('Hora de saída', null=True, blank=True)
    horas = models.DecimalField(
        'Horas',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    descricao = models.TextField('Descrição das atividades', blank=True)
    status = models.CharField(
        'Status',
        max_length=20,
        choices=Status.choices,
        default=Status.APROVADO,
    )
    observacao = models.TextField('Observação', blank=True)
    anexo = models.FileField('Anexo', upload_to='anexos/%Y/%m/', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Registro'
        verbose_name_plural = 'Registros'
        ordering = ['-data', '-criado_em']

    def __str__(self):
        return f'{self.estagiario.nome} - {self.get_tipo_display()} - {self.data}'

    def save(self, *args, **kwargs):
        if self.tipo == self.Tipo.PRESENCIAL and self.entrada and self.saida:
            self.horas = self._calcular_horas_presencial()
            self.status = self.Status.APROVADO
        elif self.tipo == self.Tipo.HOME_OFFICE and not self.pk:
            self.status = self.Status.PENDENTE
        super().save(*args, **kwargs)

    def _calcular_horas_presencial(self):
        entrada_dt = datetime.combine(self.data, self.entrada)
        saida_dt = datetime.combine(self.data, self.saida)
        if saida_dt <= entrada_dt:
            saida_dt += timedelta(days=1)
        diff = saida_dt - entrada_dt
        return Decimal(str(round(diff.total_seconds() / 3600, 2)))

    @property
    def horas_efetivas(self):
        if self.tipo == self.Tipo.PRESENCIAL:
            return self.horas or Decimal('0')
        if self.status == self.Status.APROVADO:
            return self.horas or Decimal('0')
        return Decimal('0')

    @classmethod
    def horas_por_periodo(cls, estagiario, inicio, fim):
        presencial = cls.objects.filter(
            estagiario=estagiario,
            tipo=cls.Tipo.PRESENCIAL,
            data__gte=inicio,
            data__lte=fim,
        ).aggregate(total=Sum('horas'))['total'] or Decimal('0')

        home_office = cls.objects.filter(
            estagiario=estagiario,
            tipo=cls.Tipo.HOME_OFFICE,
            status=cls.Status.APROVADO,
            data__gte=inicio,
            data__lte=fim,
        ).aggregate(total=Sum('horas'))['total'] or Decimal('0')

        return {
            'presencial': presencial,
            'home_office': home_office,
            'total': presencial + home_office,
        }

    @classmethod
    def filtrar_por_tipo_status(cls, queryset, filtro):
        if filtro == 'presencial':
            return queryset.filter(tipo=cls.Tipo.PRESENCIAL)
        if filtro == 'home_office':
            return queryset.filter(tipo=cls.Tipo.HOME_OFFICE)
        if filtro == 'pendentes':
            return queryset.filter(
                tipo=cls.Tipo.HOME_OFFICE,
                status=cls.Status.PENDENTE,
            )
        if filtro == 'aprovados':
            return queryset.filter(
                Q(tipo=cls.Tipo.PRESENCIAL)
                | Q(tipo=cls.Tipo.HOME_OFFICE, status=cls.Status.APROVADO)
            )
        return queryset


def is_supervisor(user):
    return user.is_authenticated and (
        user.is_staff
        or user.estagiarios_supervisionados.exists()
    )


def get_estagiario(user):
    try:
        return user.estagiario
    except Estagiario.DoesNotExist:
        return None
