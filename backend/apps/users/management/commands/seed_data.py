from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.companies.models import Company
from apps.users.models import User
from apps.sectors.models import Sector, Position
from apps.courses.models import Course, Content, CourseProgress
from apps.checklist.models import ChecklistItem, ChecklistProgress
from apps.materials.models import Material
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = "Popula o banco com dados de demonstração para teste inicial"

    def handle(self, *args, **options):
        self.stdout.write("Criando dados de demonstração...")

        self._seed_owner()
        self._seed_empresa_demo()
        self._seed_empresa_beta()

        self.stdout.write(self.style.SUCCESS("[OK] Dados de demonstracao criados com sucesso!"))
        self.stdout.write("--------------------------------------------------")
        self.stdout.write("  Dono do sistema:     owner@empresa.com   / senha123")
        self.stdout.write("--------------------------------------------------")
        self.stdout.write("  Empresa Demo:")
        self.stdout.write("  Usuario RH:          rh@empresa.com      / senha123")
        self.stdout.write("  Colaborador (TI):    joao@empresa.com    / senha123 (parcial)")
        self.stdout.write("  Colaborador (TI):    ana@empresa.com     / senha123 (100%)")
        self.stdout.write("  Colaborador (RH):    carla@empresa.com   / senha123 (parcial)")
        self.stdout.write("  Colaborador (RH):    pedro@empresa.com   / senha123 (nunca acessou)")
        self.stdout.write("--------------------------------------------------")
        self.stdout.write("  Empresa Beta (prova de isolamento entre empresas):")
        self.stdout.write("  Usuario RH:          rh@beta.com         / senha123")
        self.stdout.write("  Colaborador:         bruno@beta.com      / senha123")
        self.stdout.write("--------------------------------------------------")

    def _create_user(self, email, defaults):
        user, created = User.objects.get_or_create(email=email, defaults=defaults)
        if created or not user.check_password("senha123"):
            user.set_password("senha123")
        # Mantém os dados sincronizados mesmo em reexecuções (ex.: hire_date
        # adicionado depois que os usuários de demonstração já existiam).
        for field, value in defaults.items():
            setattr(user, field, value)
        user.save()
        return user

    def _seed_owner(self):
        self._create_user(
            "owner@empresa.com",
            {
                "full_name": "Dono do Sistema",
                "role": "owner",
                "company": None,
                "is_staff": True,
                "is_superuser": True,
            },
        )

    def _seed_empresa_demo(self):
        empresa, _ = Company.objects.get_or_create(name="Empresa Demo")

        # 1. Setores
        sector_ti, _ = Sector.objects.get_or_create(
            name="Tecnologia da Informação",
            company=empresa,
            defaults={"description": "Desenvolvimento de software, infraestrutura e segurança."},
        )
        sector_rh, _ = Sector.objects.get_or_create(
            name="Recursos Humanos",
            company=empresa,
            defaults={"description": "Gestão de pessoas, cultura e recrutamento."},
        )

        # 2. Cargos
        pos_dev, _ = Position.objects.get_or_create(name="Desenvolvedor Júnior", sector=sector_ti)
        pos_rh, _ = Position.objects.get_or_create(name="Analista de RH", sector=sector_rh)

        # 3. Usuários
        rh_user = self._create_user(
            "rh@empresa.com",
            {
                "full_name": "Mariana Santos (RH)",
                "role": "rh_admin",
                "company": empresa,
                "sector": sector_rh,
                "position": pos_rh,
                "is_staff": True,
            },
        )
        today = timezone.localdate()
        colab_user = self._create_user(
            "joao@empresa.com",
            {
                "full_name": "João Silva", "role": "colaborador", "company": empresa,
                "sector": sector_ti, "position": pos_dev, "hire_date": today - timedelta(days=10),
            },
        )
        colab_ana = self._create_user(
            "ana@empresa.com",
            {
                "full_name": "Ana Beatriz Costa", "role": "colaborador", "company": empresa,
                "sector": sector_ti, "position": pos_dev, "hire_date": today - timedelta(days=20),
            },
        )
        colab_pedro = self._create_user(
            "pedro@empresa.com",
            {
                "full_name": "Pedro Henrique Lima", "role": "colaborador", "company": empresa,
                "sector": sector_rh, "position": pos_rh, "hire_date": today - timedelta(days=45),
            },
        )
        colab_carla = self._create_user(
            "carla@empresa.com",
            {
                "full_name": "Carla Mendes", "role": "colaborador", "company": empresa,
                "sector": sector_rh, "position": pos_rh, "hire_date": today - timedelta(days=5),
            },
        )

        # 4. Cursos
        course1, _ = Course.objects.get_or_create(
            title="Boas-vindas e Cultura da Empresa",
            company=empresa,
            defaults={
                "description": "Conheça nossa história, valores, missão e os principais ritos da equipe.",
                "sector": None,  # Geral
                "order": 1,
            },
        )
        Content.objects.get_or_create(
            course=course1, order=1,
            defaults={"type": "video", "file_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        Content.objects.get_or_create(
            course=course1, order=2,
            defaults={"type": "text", "file_url": "https://empresa.com/manual-cultura.html"},
        )

        course2, _ = Course.objects.get_or_create(
            title="Setup do Ambiente de Desenvolvimento",
            company=empresa,
            defaults={
                "description": "Configuração de Git, Docker, Python/Flutter e chaves de acesso.",
                "sector": sector_ti,
                "deadline": "week1",
                "order": 2,
            },
        )
        Content.objects.get_or_create(
            course=course2, order=1,
            defaults={"type": "pdf", "file_url": "https://empresa.com/guia-ambiente-ti.pdf"},
        )

        course3, _ = Course.objects.get_or_create(
            title="Arquitetura de Software e Padrões de Código",
            company=empresa,
            defaults={
                "description": "Clean Architecture, padrões de API REST e convenções do time de engenharia.",
                "sector": sector_ti,
                "position": pos_dev,
                "order": 3,
            },
        )
        # Só faz sentido estudar arquitetura depois do ambiente estar pronto.
        if course3.prerequisite_id != course2.id:
            course3.prerequisite = course2
            course3.save(update_fields=["prerequisite"])
        Content.objects.get_or_create(
            course=course3, order=1,
            defaults={"type": "video", "file_url": "https://empresa.com/treinamento-arquitetura.mp4"},
        )

        # Progresso inicial para João (parcial)
        CourseProgress.objects.get_or_create(user=colab_user, course=course1, defaults={"status": "completed"})
        CourseProgress.objects.get_or_create(user=colab_user, course=course2, defaults={"status": "in_progress"})

        # Ana (TI): trilha completa (caso 100% no Painel RH)
        CourseProgress.objects.get_or_create(user=colab_ana, course=course1, defaults={"status": "completed"})
        CourseProgress.objects.get_or_create(user=colab_ana, course=course2, defaults={"status": "completed"})
        CourseProgress.objects.get_or_create(user=colab_ana, course=course3, defaults={"status": "completed"})

        # Carla (RH): parcial (só curso geral concluído)
        CourseProgress.objects.get_or_create(user=colab_carla, course=course1, defaults={"status": "completed"})

        # Pedro (RH): nenhum progresso ainda — caso "não iniciado" / nunca acessou

        # 5. Checklist
        item1, _ = ChecklistItem.objects.get_or_create(
            title="Assinar termo de confidencialidade (NDA)",
            company=empresa,
            defaults={"deadline": "day1", "sector": None, "order": 1},
        )
        item2, _ = ChecklistItem.objects.get_or_create(
            title="Configurar autenticação de dois fatores (2FA)",
            company=empresa,
            defaults={"deadline": "day1", "sector": sector_ti, "order": 2},
        )
        item3, _ = ChecklistItem.objects.get_or_create(
            title="Reunião 1-on-1 de alinhamento com a liderança",
            company=empresa,
            defaults={"deadline": "week1", "sector": None, "order": 3},
        )

        ChecklistProgress.objects.get_or_create(user=colab_user, item=item1, defaults={"completed": True})

        # Ana (TI): checklist completo
        ChecklistProgress.objects.get_or_create(user=colab_ana, item=item1, defaults={"completed": True})
        ChecklistProgress.objects.get_or_create(user=colab_ana, item=item2, defaults={"completed": True})
        ChecklistProgress.objects.get_or_create(user=colab_ana, item=item3, defaults={"completed": True})

        # Carla (RH): só um item concluído
        ChecklistProgress.objects.get_or_create(user=colab_carla, item=item1, defaults={"completed": True})

        # 6. Materiais
        Material.objects.get_or_create(
            title="Código de Conduta e Ética",
            company=empresa,
            defaults={"file_url": "https://empresa.com/codigo-conduta.pdf", "sector": None},
        )
        Material.objects.get_or_create(
            title="Guia de Boas Práticas Git & GitHub",
            company=empresa,
            defaults={"file_url": "https://empresa.com/git-flow.pdf", "sector": sector_ti},
        )

        # 7. Notificações
        Notification.objects.get_or_create(
            user=colab_user,
            title="Bem-vindo ao time!",
            defaults={"message": "Sua jornada de integração já começou. Acesse seus cursos no painel.", "read": False},
        )

    def _seed_empresa_beta(self):
        """
        Segunda empresa, deliberadamente pequena — serve para provar na
        demonstração que o isolamento multi-tenant funciona de verdade:
        o RH da Beta só enxerga este único curso, nunca os 3 da Demo.
        """
        empresa, _ = Company.objects.get_or_create(name="Empresa Beta")

        sector, _ = Sector.objects.get_or_create(
            name="Operações", company=empresa, defaults={"description": "Setor único da Empresa Beta."}
        )
        position, _ = Position.objects.get_or_create(name="Analista de Operações", sector=sector)

        self._create_user(
            "rh@beta.com",
            {"full_name": "Rafaela Souza (RH)", "role": "rh_admin", "company": empresa, "sector": sector, "position": position, "is_staff": True},
        )
        colaborador = self._create_user(
            "bruno@beta.com",
            {
                "full_name": "Bruno Almeida", "role": "colaborador", "company": empresa,
                "sector": sector, "position": position, "hire_date": timezone.localdate() - timedelta(days=3),
            },
        )

        course, _ = Course.objects.get_or_create(
            title="Boas-vindas à Empresa Beta",
            company=empresa,
            defaults={"description": "Integração inicial da Empresa Beta.", "sector": None, "order": 1},
        )
        Content.objects.get_or_create(
            course=course, order=1,
            defaults={"type": "text", "file_url": "https://beta.com/boas-vindas.html"},
        )

        item, _ = ChecklistItem.objects.get_or_create(
            title="Assinar contrato",
            company=empresa,
            defaults={"deadline": "day1", "sector": None, "order": 1},
        )
        ChecklistProgress.objects.get_or_create(user=colaborador, item=item, defaults={"completed": True})
