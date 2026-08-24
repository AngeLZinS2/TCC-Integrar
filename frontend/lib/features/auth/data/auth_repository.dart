import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/user_model.dart';
import '../../../shared/services/storage_service.dart';

class AuthRepository {
  final HttpClient httpClient;
  final StorageService storageService;

  AuthRepository({
    required this.httpClient,
    required this.storageService,
  });

  Future<UserModel> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.login,
        data: {
          'email': email.trim(),
          'password': password,
        },
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        final accessToken = data['access'] as String;
        final refreshToken = data['refresh'] as String;
        final userData = data['user'] as Map<String, dynamic>;

        final user = UserModel.fromJson(userData);

        await storageService.saveAccessToken(accessToken);
        await storageService.saveRefreshToken(refreshToken);
        await storageService.saveUser(user);

        return user;
      } else {
        throw Exception('Falha ao autenticar. Verifique suas credenciais.');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('E-mail ou senha incorretos.');
      } else if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.connectionError) {
        throw Exception('Não foi possível conectar ao servidor. Verifique sua conexão.');
      }
      final errorMsg = e.response?.data?['detail'] ?? 'Erro no login.';
      throw Exception(errorMsg);
    }
  }

  Future<UserModel?> getStoredUser() async {
    return await storageService.getUser();
  }

  /// Atualiza os campos que o próprio usuário pode editar.
  ///
  /// Setor, cargo, gestor, matrícula e papel não entram aqui: são read-only
  /// no backend, administrados pelo RH. Enviá-los seria ignorado em silêncio.
  Future<UserModel> updateProfile({
    String? fullName,
    String? phone,
    String? avatarUrl,
  }) async {
    try {
      final response = await httpClient.dio.patch(
        ApiConstants.me,
        data: {
          if (fullName != null) 'full_name': fullName,
          if (phone != null) 'phone': phone,
          if (avatarUrl != null) 'avatar_url': avatarUrl,
        },
      );
      final user = UserModel.fromJson(response.data as Map<String, dynamic>);
      await storageService.saveUser(user);
      return user;
    } on DioException catch (e) {
      final data = e.response?.data;
      if (data is Map && data.isNotEmpty) {
        final first = data.values.first;
        throw Exception(first is List ? first.first.toString() : first.toString());
      }
      throw Exception('Não foi possível salvar o perfil.');
    }
  }

  Future<UserModel?> fetchCurrentUser() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.me);
      if (response.statusCode == 200) {
        final user = UserModel.fromJson(response.data as Map<String, dynamic>);
        await storageService.saveUser(user);
        return user;
      }
    } catch (_) {}
    return null;
  }

  /// Encerra a sessão no servidor antes de limpar o armazenamento local.
  ///
  /// A revogação do refresh token é o que realmente encerra a sessão — sem
  /// ela, um token capturado continuaria válido por dias. Se a chamada
  /// falhar (offline, token já expirado), a sessão local é limpa mesmo
  /// assim: do ponto de vista de quem clicou em "sair", ficar preso na tela
  /// seria pior do que a revogação não ter acontecido.
  Future<void> logout() async {
    final refreshToken = await storageService.getRefreshToken();
    if (refreshToken != null && refreshToken.isNotEmpty) {
      try {
        await httpClient.dio.post(
          ApiConstants.logout,
          data: {'refresh': refreshToken},
        );
      } catch (_) {}
    }
    await storageService.clearAll();
  }

  /// Pede o e-mail de recuperação. A resposta é sempre a mesma, exista a
  /// conta ou não — o backend não revela se o e-mail está cadastrado.
  Future<String> requestPasswordReset(String email) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.passwordReset,
        data: {'email': email.trim()},
      );
      return response.data['detail'] as String? ??
          'Se existir uma conta associada a este e-mail, enviaremos instruções para recuperação.';
    } on DioException catch (e) {
      if (e.response?.statusCode == 429) {
        throw Exception('Muitas tentativas. Aguarde um minuto e tente novamente.');
      }
      final data = e.response?.data;
      if (data is Map && data.isNotEmpty) {
        final first = data.values.first;
        throw Exception(first is List ? first.first.toString() : first.toString());
      }
      throw Exception('Não foi possível solicitar a recuperação. Tente novamente.');
    }
  }

  Future<void> confirmPasswordReset({
    required String uid,
    required String token,
    required String newPassword,
  }) async {
    try {
      await httpClient.dio.post(
        ApiConstants.passwordResetConfirm,
        data: {
          'uid': uid,
          'token': token,
          'new_password': newPassword,
          'new_password_confirm': newPassword,
        },
      );
    } on DioException catch (e) {
      if (e.response?.statusCode == 429) {
        throw Exception('Muitas tentativas. Aguarde um minuto e tente novamente.');
      }
      final data = e.response?.data;
      if (data is Map && data.isNotEmpty) {
        final first = data.values.first;
        throw Exception(first is List ? first.first.toString() : first.toString());
      }
      throw Exception('Não foi possível redefinir a senha. Solicite um novo link.');
    }
  }
}
