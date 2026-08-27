import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../features/auth/presentation/forgot_password_screen.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/landing/presentation/landing_screen.dart';
import '../features/auth/presentation/reset_password_screen.dart';
import '../features/auth/providers/auth_provider.dart';
import '../features/audit/presentation/audit_screen.dart';
import '../features/checklist/presentation/checklist_screen.dart';
import '../features/company/presentation/company_settings_screen.dart';
import '../features/employees/presentation/edit_employee_screen.dart';
import '../features/courses/presentation/course_detail_screen.dart';
import '../features/courses/presentation/courses_screen.dart';
import '../features/courses/presentation/new_course_screen.dart';
import '../features/directory/presentation/directory_screen.dart';
import '../features/materials/presentation/materials_screen.dart';
import '../features/org/presentation/positions_screen.dart';
import '../features/org/presentation/sectors_screen.dart';
import '../features/materials/presentation/new_material_screen.dart';
import '../features/notifications/presentation/notifications_screen.dart';
import '../features/onboarding/presentation/onboarding_screen.dart';
import '../features/documents/presentation/document_detail_screen.dart';
import '../features/documents/presentation/documents_screen.dart';
import '../features/onboarding/presentation/tasks_screen.dart';
import '../features/units/presentation/units_screen.dart';
import '../features/automations/presentation/automations_screen.dart';
import '../features/integrations/presentation/integration_screen.dart';
import '../features/courses/presentation/quiz_screen.dart';
import '../features/events/presentation/events_screen.dart';
import '../features/events/presentation/new_event_screen.dart';
import '../features/owner/presentation/companies_list_screen.dart';
import '../features/owner/presentation/company_detail_screen.dart';
import '../features/owner/presentation/new_company_screen.dart';
import '../features/owner/presentation/owner_dashboard_screen.dart';
import '../features/communications/presentation/communications_screen.dart';
import '../features/communications/presentation/new_communication_screen.dart';
import '../features/profile/presentation/profile_screen.dart';
import '../features/requests/presentation/new_request_screen.dart';
import '../features/requests/presentation/request_detail_screen.dart';
import '../features/requests/presentation/requests_screen.dart';
import '../features/rh_dashboard/presentation/collaborator_detail_screen.dart';
import '../features/rh_dashboard/presentation/collaborators_list_screen.dart';
import '../features/rh_dashboard/presentation/new_collaborator_screen.dart';
import '../features/rh_dashboard/presentation/rh_dashboard_screen.dart';
import '../core/widgets/app_motion.dart';
import '../features/shell/presentation/app_shell.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/',
    refreshListenable: _RouterAuthNotifier(ref),
    redirect: (BuildContext context, GoRouterState state) {
      final authState = ref.read(authNotifierProvider);
      final isLoggingIn = state.matchedLocation == '/login';
      final isLanding = state.matchedLocation == '/';

      // Rotas abertas: a landing apresenta o sistema para quem ainda não
      // tem conta; quem esqueceu a senha não consegue autenticar para
      // chegar até as demais, e o link do e-mail é aberto sem sessão.
      final isPublicAuthRoute = isLoggingIn ||
          isLanding ||
          state.matchedLocation == '/forgot-password' ||
          state.matchedLocation == '/reset-password';

      if (authState.status == AuthStatus.initial || authState.status == AuthStatus.loading) {
        return null;
      }

      final isAuthenticated = authState.isAuthenticated;
      final isOwner = authState.user?.isOwner == true;

      if (!isAuthenticated && !isPublicAuthRoute) {
        return '/login';
      }

      // Quem já tem sessão não fica na vitrine nem na tela de login —
      // vai direto para o painel do seu papel.
      if (isAuthenticated && (isLoggingIn || isLanding)) {
        return isOwner ? '/owner/dashboard' : '/onboarding';
      }

      final user = authState.user;

      // Painel do RH: aberto a quem administra a empresa (RH ou admin).
      final isRhPath = state.matchedLocation.startsWith('/rh');
      if (isAuthenticated && isRhPath && user?.managesCompany != true) {
        return '/onboarding';
      }

      // Estrutura organizacional: exige permissão de escrita em setores.
      final isOrgPath = state.matchedLocation.startsWith('/org');
      if (isAuthenticated && isOrgPath && user?.canManageOrg != true) {
        return '/onboarding';
      }

      // Auditoria: exclusiva de quem administra a empresa.
      final isAuditPath = state.matchedLocation.startsWith('/audit');
      if (isAuthenticated && isAuditPath && user?.canViewAudit != true) {
        return '/onboarding';
      }

      final isCompanyPath = state.matchedLocation.startsWith('/company');

      final isOwnerPath = state.matchedLocation.startsWith('/owner');
      if (isAuthenticated && isOwnerPath && !isOwner) {
        return '/onboarding';
      }

      // Dono não tem trilha pessoal — mantém fora das rotas de colaborador.
      // `isLanding` nao entra aqui: o retorno antecipado acima ja tratou
      // quem esta autenticado na vitrine.
      final isCollaboratorPath = !isRhPath &&
          !isOrgPath &&
          !isAuditPath &&
          !isCompanyPath &&
          !isOwnerPath &&
          state.matchedLocation != '/profile';
      if (isAuthenticated && isOwner && isCollaboratorPath) {
        return '/owner/dashboard';
      }

      return null;
    },
    routes: [
      // ── Public Auth Routes ─────────────────────────────────────────
      // Vitrine pública. Fica na raiz porque é o endereço que alguém
      // digita sem saber nada do sistema.
      GoRoute(
        path: '/',
        name: 'landing',
        builder: (context, state) => const LandingScreen(),
      ),
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/forgot-password',
        name: 'forgot_password',
        builder: (context, state) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        // Aberta pelo link do e-mail: /reset-password?uid=...&token=...
        path: '/reset-password',
        name: 'reset_password',
        builder: (context, state) => ResetPasswordScreen(
          uid: state.uri.queryParameters['uid'] ?? '',
          token: state.uri.queryParameters['token'] ?? '',
        ),
      ),

      // ── New Course Route (Fullscreen, RH admin / sector leader) ─────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/courses/new',
        name: 'new_course',
        builder: (context, state) => const NewCourseScreen(),
      ),

      // ── New Material Route (Fullscreen, RH admin / sector leader) ───
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/materials/new',
        name: 'new_material',
        builder: (context, state) => const NewMaterialScreen(),
      ),

      // ── New Request Route (Fullscreen) ─────────────────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/requests/new',
        name: 'new_request',
        builder: (context, state) => const NewRequestScreen(),
      ),

      // ── New Communication Route (Fullscreen, RH) ───────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/communications/new',
        name: 'new_communication',
        builder: (context, state) => const NewCommunicationScreen(),
      ),

      // ── New Event Route (Fullscreen, RH) ───────────────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/events/new',
        name: 'new_event',
        builder: (context, state) => const NewEventScreen(),
      ),

      // ── Document Detail Route (Fullscreen) ─────────────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/documents/:id',
        name: 'document_detail',
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return DocumentDetailScreen(documentId: id);
        },
      ),

      // ── Request Detail Route (Fullscreen) ──────────────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/requests/:id',
        name: 'request_detail',
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return RequestDetailScreen(requestId: id);
        },
      ),

      // ── Quiz (Fullscreen) ──────────────────────────────────────────
      // Sem a barra lateral de propósito: responder a avaliação é uma
      // tarefa de foco, e um clique de navegação no meio dela custaria a
      // tentativa.
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/courses/:id/quiz',
        name: 'course_quiz',
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          final title = state.uri.queryParameters['title'] ?? 'Avaliação';
          return QuizScreen(courseId: id, courseTitle: title);
        },
      ),

      // ── Course Detail Route (Fullscreen) ───────────────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/courses/:id',
        name: 'course_detail',
        builder: (context, state) {
          final courseId = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return CourseDetailScreen(courseId: courseId);
        },
      ),

      // ── New Collaborator Route (Fullscreen, RH only) ─────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/rh/collaborators/new',
        name: 'new_collaborator',
        builder: (context, state) => const NewCollaboratorScreen(),
      ),

      // ── Edit Employee Route (Fullscreen, RH / admin) ────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/rh/collaborators/:id/edit',
        name: 'edit_employee',
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return EditEmployeeScreen(employeeId: id);
        },
      ),

      // ── Collaborator Detail Route (Fullscreen, RH only) ─────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/rh/collaborators/:id',
        name: 'collaborator_detail',
        builder: (context, state) {
          final collaboratorId = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return CollaboratorDetailScreen(collaboratorId: collaboratorId);
        },
      ),

      // ── New Company Route (Fullscreen, Owner only) ──────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/owner/companies/new',
        name: 'new_company',
        builder: (context, state) => const NewCompanyScreen(),
      ),

      // ── Company Detail Route (Fullscreen, Owner only) ────────────────
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/owner/companies/:id',
        name: 'company_detail',
        builder: (context, state) {
          final companyId = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return CompanyDetailScreen(companyId: companyId);
        },
      ),

      // ── App Shell Wrapped Routes ───────────────────────────────────
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) {
          return AppShell(
            location: state.matchedLocation,
            child: child,
          );
        },
        routes: [
          GoRoute(
            path: '/onboarding',
            name: 'onboarding',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const OnboardingScreen(),
            ),
          ),
          GoRoute(
            path: '/courses',
            name: 'courses',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const CoursesScreen(),
            ),
          ),
          GoRoute(
            path: '/checklist',
            name: 'checklist',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const ChecklistScreen(),
            ),
          ),
          GoRoute(
            path: '/requests',
            name: 'requests',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const RequestsScreen(),
            ),
          ),
          GoRoute(
            path: '/communications',
            name: 'communications',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const CommunicationsScreen(),
            ),
          ),
          GoRoute(
            path: '/events',
            name: 'events',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const EventsScreen(),
            ),
          ),
          GoRoute(
            path: '/documents',
            name: 'documents',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const DocumentsScreen(),
            ),
          ),
          GoRoute(
            path: '/onboarding/tasks',
            name: 'onboarding_tasks',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const OnboardingTasksScreen(),
            ),
          ),
          GoRoute(
            path: '/units',
            name: 'units',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const UnitsScreen(),
            ),
          ),
          GoRoute(
            path: '/automations',
            name: 'automations',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const AutomationsScreen(),
            ),
          ),
          GoRoute(
            path: '/integrations',
            name: 'integrations',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const IntegrationScreen(),
            ),
          ),
          GoRoute(
            path: '/audit',
            name: 'audit',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const AuditScreen(),
            ),
          ),
          GoRoute(
            path: '/company/settings',
            name: 'company_settings',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const CompanySettingsScreen(),
            ),
          ),
          GoRoute(
            path: '/org/sectors',
            name: 'sectors',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const SectorsScreen(),
            ),
          ),
          GoRoute(
            path: '/org/positions',
            name: 'positions',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const PositionsScreen(),
            ),
          ),
          GoRoute(
            path: '/materials',
            name: 'materials',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const MaterialsScreen(),
            ),
          ),
          GoRoute(
            path: '/notifications',
            name: 'notifications',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const NotificationsScreen(),
            ),
          ),
          GoRoute(
            path: '/profile',
            name: 'profile',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const ProfileScreen(),
            ),
          ),
          GoRoute(
            path: '/directory',
            name: 'directory',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const DirectoryScreen(),
            ),
          ),

          // ── RH Admin Routes ────────────────────────────────────────
          GoRoute(
            path: '/rh/dashboard',
            name: 'rh_dashboard',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const RhDashboardScreen(),
            ),
          ),
          GoRoute(
            path: '/rh/collaborators',
            name: 'rh_collaborators',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const CollaboratorsListScreen(),
            ),
          ),

          // ── Owner Routes ─────────────────────────────────────────────
          GoRoute(
            path: '/owner/dashboard',
            name: 'owner_dashboard',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const OwnerDashboardScreen(),
            ),
          ),
          GoRoute(
            path: '/owner/companies',
            name: 'owner_companies',
            pageBuilder: (context, state) => paginaComTransicao(
              chave: state.pageKey,
              filho: const CompaniesListScreen(),
            ),
          ),
        ],
      ),
    ],
  );
});

class _RouterAuthNotifier extends ChangeNotifier {
  final Ref _ref;

  _RouterAuthNotifier(this._ref) {
    _ref.listen(authNotifierProvider, (_, __) {
      notifyListeners();
    });
  }
}
