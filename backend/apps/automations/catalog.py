"""
Catálogo de eventos e ações das automações.

Duas listas fechadas, e é de propósito: uma automação é configurada pelo
RH e executa código do servidor. Se o evento e a ação viessem livres do
formulário, a configuração viraria uma porta para disparar qualquer coisa.
Aqui, o que não está no catálogo não existe.

Estender é acrescentar uma constante e registrar um executor em
`actions.py` — nenhuma view, serializer ou migração precisa mudar.
"""

# ── Eventos ─────────────────────────────────────────────────────────────────

EMPLOYEE_CREATED = "employee.created"
EMPLOYEE_ACTIVATED = "employee.activated"
EMPLOYEE_DEACTIVATED = "employee.deactivated"

TRAINING_ASSIGNED = "training.assigned"
TRAINING_COMPLETED = "training.completed"
TRAINING_OVERDUE = "training.overdue"

DOCUMENT_PUBLISHED = "document.published"
DOCUMENT_EXPIRING = "document.expiring"

REQUEST_CREATED = "request.created"
REQUEST_COMPLETED = "request.completed"

ANNOUNCEMENT_PUBLISHED = "announcement.published"

EVENTS = {
    EMPLOYEE_CREATED: "Colaborador cadastrado",
    EMPLOYEE_ACTIVATED: "Colaborador ativado",
    EMPLOYEE_DEACTIVATED: "Colaborador desativado",
    TRAINING_ASSIGNED: "Treinamento atribuído",
    TRAINING_COMPLETED: "Treinamento concluído",
    TRAINING_OVERDUE: "Treinamento atrasado",
    DOCUMENT_PUBLISHED: "Documento publicado",
    DOCUMENT_EXPIRING: "Documento próximo do vencimento",
    REQUEST_CREATED: "Solicitação aberta",
    REQUEST_COMPLETED: "Solicitação concluída",
    ANNOUNCEMENT_PUBLISHED: "Comunicado publicado",
}

EVENT_CHOICES = [(chave, rotulo) for chave, rotulo in EVENTS.items()]


# ── Ações ───────────────────────────────────────────────────────────────────

CREATE_ONBOARDING = "create_onboarding"
SEND_NOTIFICATION = "send_notification"
SEND_EMAIL = "send_email"
ASSIGN_TRAINING = "assign_training"

ACTIONS = {
    CREATE_ONBOARDING: "Gerar tarefas de onboarding",
    SEND_NOTIFICATION: "Enviar notificação no app",
    SEND_EMAIL: "Enviar e-mail",
    ASSIGN_TRAINING: "Atribuir treinamento",
}

ACTION_CHOICES = [(chave, rotulo) for chave, rotulo in ACTIONS.items()]


# ── Destinatários ───────────────────────────────────────────────────────────

TARGET_EMPLOYEE = "employee"
TARGET_MANAGER = "manager"
TARGET_HR = "hr"

TARGET_CHOICES = [
    (TARGET_EMPLOYEE, "O colaborador do evento"),
    (TARGET_MANAGER, "O gestor dele"),
    (TARGET_HR, "A equipe de RH"),
]


# ── Condições ───────────────────────────────────────────────────────────────

# Campos do contexto que uma condição pode inspecionar. Fechado pelo mesmo
# motivo do resto: uma condição livre seria acesso arbitrário ao objeto.
CONDITION_FIELDS = {
    "sector_id": "Setor do colaborador",
    "position_id": "Cargo do colaborador",
    "unit_id": "Unidade do colaborador",
    "role": "Papel do colaborador",
    "priority": "Prioridade",
    "category": "Categoria",
}

CONDITION_FIELD_CHOICES = [(k, v) for k, v in CONDITION_FIELDS.items()]

OP_EQUALS = "eq"
OP_NOT_EQUALS = "ne"
OP_IN = "in"

OPERATOR_CHOICES = [
    (OP_EQUALS, "É igual a"),
    (OP_NOT_EQUALS, "É diferente de"),
    (OP_IN, "Está entre"),
]
