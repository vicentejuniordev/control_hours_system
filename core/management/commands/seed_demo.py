from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import Estagiario, Registro


class Command(BaseCommand):
    help = 'Cria dados de exemplo para demonstração'

    def handle(self, *args, **options):
        if Estagiario.objects.exists():
            self.stdout.write(self.style.WARNING('Dados já existem. Pulando seed.'))
            return

        supervisor = User.objects.create_user(
            username='supervisor',
            password='supervisor123',
            first_name='Carlos',
            last_name='Silva',
            is_staff=True,
        )

        estagiarios_data = [
            ('maria', 'Maria Santos', 'Ciência da Computação'),
            ('joao', 'João Oliveira', 'Engenharia de Software'),
            ('pedro', 'Pedro Costa', 'Sistemas de Informação'),
        ]

        inicio = date.today() - timedelta(days=60)
        fim = date.today() + timedelta(days=120)

        for username, nome, curso in estagiarios_data:
            user = User.objects.create_user(
                username=username,
                password='estagiario123',
                first_name=nome.split()[0],
                last_name=nome.split()[-1],
            )
            est = Estagiario.objects.create(
                user=user,
                nome=nome,
                curso=curso,
                instituicao='Universidade Federal',
                supervisor=supervisor,
                carga_total=Decimal('400'),
                carga_semanal=Decimal('30'),
                inicio=inicio,
                fim=fim,
            )

            # Presencial records
            for i, (entrada, saida) in enumerate([
                (time(8, 0), time(12, 0)),
                (time(14, 0), time(18, 0)),
            ]):
                d = date.today() - timedelta(days=10 - i)
                Registro.objects.create(
                    estagiario=est,
                    tipo=Registro.Tipo.PRESENCIAL,
                    data=d,
                    entrada=entrada,
                    saida=saida,
                )

            # Home office - approved
            Registro.objects.create(
                estagiario=est,
                tipo=Registro.Tipo.HOME_OFFICE,
                data=date.today() - timedelta(days=5),
                horas=Decimal('6'),
                descricao='• Corrigi bugs da API\n• Desenvolvi endpoint de autenticação\n• Atualizei documentação',
                status=Registro.Status.APROVADO,
            )

            # Home office - pending (only for Maria)
            if username == 'maria':
                Registro.objects.create(
                    estagiario=est,
                    tipo=Registro.Tipo.HOME_OFFICE,
                    data=date.today() - timedelta(days=1),
                    horas=Decimal('6'),
                    descricao='• Corrigi autenticação\n• Criei documentação\n• Testei endpoints',
                    status=Registro.Status.PENDENTE,
                )

        self.stdout.write(self.style.SUCCESS('Dados de exemplo criados!'))
        self.stdout.write('')
        self.stdout.write('Supervisor: supervisor / supervisor123')
        self.stdout.write('Estagiários: maria, joao, pedro / estagiario123')
