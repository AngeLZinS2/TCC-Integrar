class ApiConstants {
  // Ajuste a URL base conforme o ambiente:
  // - Android Emulator: 'http://10.0.2.2:8000/api/v1'
  // - iOS Simulator / Web / Desktop: 'http://127.0.0.1:8000/api/v1' ou 'http://localhost:8000/api/v1'
  // - Dispositivo físico: use o IP da sua máquina na rede local
  static const String baseUrl = 'http://localhost:8000/api/v1';

  // Auth
  static const String login = '/auth/token/';
  static const String refreshToken = '/auth/token/refresh/';
  static const String logout = '/auth/logout/';
  static const String passwordReset = '/auth/password-reset/';
  static const String passwordResetConfirm = '/auth/password-reset/confirm/';
  static const String me = '/auth/me/';
  static const String register = '/auth/register/';
  static String toggleColaboradorActive(int id) => '/auth/colaboradores/$id/toggle-active/';
  static String toggleSectorLeader(int id) => '/auth/colaboradores/$id/toggle-sector-leader/';
  static const String directory = '/auth/directory/';

  // Sectors & Positions
  static const String sectors = '/sectors/';
  static const String positions = '/sectors/positions/';
  static const String sectorManagerOptions = '/sectors/manager-options/';

  // Colaboradores (administração pelo RH / admin da empresa)
  static const String employees = '/employees/';
  static String employeeDetail(int id) => '/employees/$id/';
  static String employeeToggleActive(int id) => '/employees/$id/toggle-active/';
  static const String employeeManagerOptions = '/employees/manager-options/';
  static const String employeeRoles = '/employees/roles/';

  // Empresa do próprio tenant
  static const String myCompany = '/companies/me/';
  static const String myCompanySetup = '/companies/me/setup/';

  // Auditoria
  static const String audit = '/audit/';
  static const String auditFilters = '/audit/filters/';

  // Courses & Contents
  static const String courses = '/courses/';
  static const String contents = '/courses/contents/';

  // Checklist
  static const String checklist = '/checklist/';

  // Materials
  static const String materials = '/materials/';

  // Notifications
  static const String notifications = '/notifications/';

  // Requests (Solicitações RH)
  static const String requests = '/requests/';
  static String requestDetail(int id) => '/requests/$id/';
  static String requestStatus(int id) => '/requests/$id/status/';
  static String requestComments(int id) => '/requests/$id/comments/';

  // Communications (Comunicados)
  static const String communications = '/communications/';
  static String communicationDetail(int id) => '/communications/$id/';
  static String communicationRead(int id) => '/communications/$id/read/';

  // Events (Eventos e Aniversariantes)
  static const String events = '/events/';
  static String eventDetail(int id) => '/events/$id/';
  static const String birthdays = '/events/birthdays/';

  // Documents (Biblioteca)
  static const String documents = '/documents/';
  static String documentDownload(int docId, int verId) => '/documents/$docId/versions/$verId/download/';
  static String documentAccept(int docId, int verId) => '/documents/$docId/versions/$verId/accept/';

  // Painel RH (Dashboard)
  static const String dashboardOverview = '/dashboard/overview/';
  static const String dashboardCollaborators = '/dashboard/collaborators/';
  static String dashboardCollaboratorDetail(int id) => '/dashboard/collaborators/$id/';
  static const String dashboardCollaboratorsExport = '/dashboard/collaborators/export/';

  // Painel do Dono do Sistema (Empresas)
  static const String companies = '/companies/';
  static String companyDetail(int id) => '/companies/$id/';
  static String companyToggleActive(int id) => '/companies/$id/toggle-active/';
  static String companyDashboard(int id) => '/companies/$id/dashboard/';
  static const String companiesExport = '/companies/export/';

  // Painéis da P2
  static const String dashboardHr = '/dashboard/hr/';
  static const String dashboardMe = '/dashboard/me/';
  static const String dashboardTeam = '/dashboard/team/';

  // Onboarding (tarefas e templates)
  static const String onboardingTasks = '/onboarding/tasks/';
  static String onboardingTaskDetail(int id) => '/onboarding/tasks/$id/';
  static String onboardingTaskStatus(int id) => '/onboarding/tasks/$id/status/';
  static String onboardingTaskComments(int id) => '/onboarding/tasks/$id/comments/';
  static const String onboardingMy = '/onboarding/my/';
  static String onboardingEmployee(int id) => '/onboarding/employees/$id/';
  static const String onboardingTemplates = '/onboarding/templates/';
  static String onboardingTemplateDetail(int id) => '/onboarding/templates/$id/';
  static String onboardingTemplateApply(int id) => '/onboarding/templates/$id/apply/';

  // Unidades
  static const String units = '/units/';
  static String unitDetail(int id) => '/units/$id/';

  // Automações
  static const String automationRules = '/automations/rules/';
  static String automationRuleDetail(int id) => '/automations/rules/$id/';
  static String automationRuleRuns(int id) => '/automations/rules/$id/runs/';
  static const String automationCatalog = '/automations/catalog/';

  // Avaliação
  static String courseQuiz(int courseId) => '/courses/$courseId/quiz/';
  static String courseQuizQuestions(int courseId) => '/courses/$courseId/quiz/questions/';
  static String quizAttempts(int courseId) => '/courses/$courseId/quiz/attempts/';
  static String quizSubmit(int courseId, int attemptId) =>
      '/courses/$courseId/quiz/attempts/$attemptId/submit/';
  static const String myQuizAttempts = '/courses/my-attempts/';

  // Integração com o banco da empresa (P4)
  static const String integrationDatabases = '/integrations/databases/';
  static const String integrationConnection = '/integrations/connection/';
  static const String integrationConnectionTest = '/integrations/connection/test/';
  static const String integrationDiscovery = '/integrations/discovery/';
  static const String integrationPreview = '/integrations/preview/';
  static const String integrationFields = '/integrations/fields/';
  static const String integrationMappings = '/integrations/mappings/';
  static String integrationMapping(String entidade) =>
      '/integrations/mappings/$entidade/';
}
