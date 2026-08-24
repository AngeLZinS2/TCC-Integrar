import 'package:dio/dio.dart';
import '../constants/api_constants.dart';
import '../../shared/services/storage_service.dart';

/// Por que a sessão terminou — define a mensagem mostrada no login.
enum SessionEndReason {
  /// A empresa foi suspensa pelo administrador da plataforma.
  companySuspended,

  /// O token expirou e não foi possível renovar.
  expired,
}

/// Código devolvido pelo backend quando a empresa está suspensa.
/// Login, chamadas autenticadas e refresh usam todos este mesmo código.
const String _kCompanySuspendedCode = 'company_suspended';

class HttpClient {
  final Dio dio;
  final StorageService storageService;

  /// Chamado quando a sessão é encerrada pelo servidor, para que o app
  /// possa deslogar e explicar o motivo. Registrado pelo AuthNotifier.
  void Function(SessionEndReason reason)? onSessionTerminated;

  HttpClient({required this.storageService, Dio? customDio})
      : dio = customDio ??
            Dio(
              BaseOptions(
                baseUrl: ApiConstants.baseUrl,
                connectTimeout: const Duration(seconds: 15),
                receiveTimeout: const Duration(seconds: 15),
                headers: {
                  'Content-Type': 'application/json',
                  'Accept': 'application/json',
                },
              ),
            ) {
    _setupInterceptors();
  }

  /// True quando o 401 veio da regra de empresa suspensa.
  ///
  /// Depende do campo `code`, nunca do texto da mensagem — o texto é para
  /// pessoas e pode mudar; o código é o contrato entre app e backend.
  bool _isCompanySuspended(DioException error) {
    final data = error.response?.data;
    return data is Map && data['code'] == _kCompanySuspendedCode;
  }

  Future<void> _terminateSession(SessionEndReason reason) async {
    await storageService.clearAll();
    onSessionTerminated?.call(reason);
  }

  void _setupInterceptors() {
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Anexa token JWT se disponível
          final token = await storageService.getAccessToken();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException error, handler) async {
          final isAuthEndpoint = error.requestOptions.path.contains('/auth/token/');

          if (error.response?.statusCode == 401 && !isAuthEndpoint) {
            // Empresa suspensa não se resolve renovando token — o refresh
            // é recusado pelo mesmo motivo. Encerra a sessão direto.
            if (_isCompanySuspended(error)) {
              await _terminateSession(SessionEndReason.companySuspended);
              return handler.next(error);
            }

            final refreshed = await _tryRefreshToken();
            if (refreshed) {
              final token = await storageService.getAccessToken();
              error.requestOptions.headers['Authorization'] = 'Bearer $token';
              try {
                final cloneReq = await dio.fetch(error.requestOptions);
                return handler.resolve(cloneReq);
              } catch (e) {
                return handler.next(error);
              }
            }

            // Sem refresh possível: sessão encerrada de vez.
            await _terminateSession(SessionEndReason.expired);
          }
          return handler.next(error);
        },
      ),
    );
  }

  Future<bool> _tryRefreshToken() async {
    final refreshToken = await storageService.getRefreshToken();
    if (refreshToken == null) return false;

    try {
      final response = await Dio(
        BaseOptions(
          baseUrl: ApiConstants.baseUrl,
          headers: {'Content-Type': 'application/json'},
        ),
      ).post(
        ApiConstants.refreshToken,
        data: {'refresh': refreshToken},
      );

      if (response.statusCode == 200) {
        final newAccess = response.data['access'] as String;
        await storageService.saveAccessToken(newAccess);
        // Rotação está ligada no backend: o refresh antigo já foi para a
        // blacklist, então o novo precisa substituí-lo no armazenamento.
        final newRefresh = response.data['refresh'] as String?;
        if (newRefresh != null && newRefresh.isNotEmpty) {
          await storageService.saveRefreshToken(newRefresh);
        }
        return true;
      }
    } on DioException catch (e) {
      if (_isCompanySuspended(e)) {
        await _terminateSession(SessionEndReason.companySuspended);
        return false;
      }
    } catch (_) {}
    return false;
  }
}
