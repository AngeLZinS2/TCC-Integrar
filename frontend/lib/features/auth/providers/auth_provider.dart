import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/user_model.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/auth_repository.dart';

enum AuthStatus { initial, loading, authenticated, unauthenticated, error }

/// Mensagens mostradas na tela de login quando o servidor encerra a sessão.
/// Descrevem o que aconteceu e o que fazer, sem detalhe técnico.
const String kCompanySuspendedMessage =
    'Esta empresa está temporariamente suspensa. '
    'Entre em contato com o administrador da sua empresa.';
const String kSessionExpiredMessage = 'Sua sessão expirou. Entre novamente.';

class AuthState {
  final AuthStatus status;
  final UserModel? user;
  final String? errorMessage;

  /// Aviso a ser exibido na tela de login depois de uma sessão encerrada
  /// pelo servidor. Diferente de [errorMessage], que é falha de login.
  final String? sessionNotice;

  const AuthState({
    required this.status,
    this.user,
    this.errorMessage,
    this.sessionNotice,
  });

  factory AuthState.initial() => const AuthState(status: AuthStatus.initial);
  factory AuthState.loading() => const AuthState(status: AuthStatus.loading);
  factory AuthState.authenticated(UserModel user) =>
      AuthState(status: AuthStatus.authenticated, user: user);
  factory AuthState.unauthenticated({String? sessionNotice}) =>
      AuthState(status: AuthStatus.unauthenticated, sessionNotice: sessionNotice);
  factory AuthState.error(String message) =>
      AuthState(status: AuthStatus.error, errorMessage: message);

  bool get isAuthenticated => status == AuthStatus.authenticated;
  bool get isLoading => status == AuthStatus.loading;
}

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository _repository;
  UserModel? _pendingUser;

  AuthNotifier(this._repository, HttpClient httpClient)
      : super(AuthState.initial()) {
    // O interceptor avisa quando o servidor encerra a sessão (empresa
    // suspensa ou token irrecuperável) para que o app deslogue na hora.
    httpClient.onSessionTerminated = _handleSessionTerminated;
    checkAuthStatus();
  }

  void _handleSessionTerminated(SessionEndReason reason) {
    if (!mounted) return;
    state = AuthState.unauthenticated(
      sessionNotice: reason == SessionEndReason.companySuspended
          ? kCompanySuspendedMessage
          : kSessionExpiredMessage,
    );
  }

  /// Limpa o aviso depois de exibido, para não reaparecer numa nova visita.
  void clearSessionNotice() {
    if (state.sessionNotice == null) return;
    state = AuthState.unauthenticated();
  }

  Future<void> checkAuthStatus() async {
    try {
      final user = await _repository.getStoredUser();
      if (user != null) {
        state = AuthState.authenticated(user);
        // Atualiza dados mais recentes em background
        _repository.fetchCurrentUser().then((freshUser) {
          if (freshUser != null) {
            state = AuthState.authenticated(freshUser);
          }
        });
      } else {
        state = AuthState.unauthenticated();
      }
    } catch (_) {
      state = AuthState.unauthenticated();
    }
  }

  /// Autentica o usuário mas NÃO marca o estado como autenticado ainda —
  /// isso é feito por [confirmAuthenticated], chamado pela tela de login
  /// após a animação do foguete, para que o redirect do router só aconteça
  /// depois que a animação (que roda sobre a própria tela de login) terminar.
  Future<bool> login(String email, String password) async {
    state = AuthState.loading();
    try {
      final user = await _repository.login(email: email, password: password);
      _pendingUser = user;
      return true;
    } catch (e) {
      final msg = e.toString().replaceAll('Exception: ', '');
      state = AuthState.error(msg);
      return false;
    }
  }

  /// Confirma a autenticação pendente, liberando o redirect do router.
  void confirmAuthenticated() {
    final user = _pendingUser;
    if (user != null) {
      _pendingUser = null;
      state = AuthState.authenticated(user);
    }
  }

  /// Salva os campos editáveis do próprio perfil e reflete no estado.
  Future<void> updateProfile({
    String? fullName,
    String? phone,
    String? avatarUrl,
  }) async {
    final updated = await _repository.updateProfile(
      fullName: fullName,
      phone: phone,
      avatarUrl: avatarUrl,
    );
    if (mounted) state = AuthState.authenticated(updated);
  }

  Future<void> logout() async {
    await _repository.logout();
    state = AuthState.unauthenticated();
  }
}

final authNotifierProvider =
    StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final repository = ref.watch(authRepositoryProvider);
  final httpClient = ref.watch(httpClientProvider);
  return AuthNotifier(repository, httpClient);
});
