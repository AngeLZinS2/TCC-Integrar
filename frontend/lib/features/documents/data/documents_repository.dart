import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/document_model.dart';
import '../../../shared/models/paginated_response.dart';
import '../../../shared/services/csv_download/csv_download.dart';

class DocumentsRepository {
  final HttpClient httpClient;

  DocumentsRepository({required this.httpClient});

  Future<PaginatedResponse<DocumentModel>> getDocuments({int page = 1}) async {
    final response = await httpClient.dio.get(
      ApiConstants.documents,
      queryParameters: {'page': page},
    );
    return PaginatedResponse.fromJson(
      response.data,
      (json) => DocumentModel.fromJson(json),
    );
  }

  Future<void> acceptDocument(int documentId, int versionId) async {
    await httpClient.dio.post(ApiConstants.documentAccept(documentId, versionId));
  }

  /// Baixa uma versão do documento.
  ///
  /// Os bytes vêm por requisição autenticada do Dio — o backend exige o
  /// token e valida a empresa antes de servir o arquivo. Abrir a URL direto
  /// no navegador não funcionaria: o header JWT não iria junto e o download
  /// seria recusado.
  Future<void> downloadDocument(int documentId, int versionId, String fileName) async {
    final url = ApiConstants.documentDownload(documentId, versionId);
    try {
      final response = await httpClient.dio.get<List<int>>(
        url,
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = response.data;
      if (bytes == null || bytes.isEmpty) {
        throw Exception('O arquivo veio vazio.');
      }
      saveFile(bytes, fileName, mimeType: _mimeFor(fileName));
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        throw Exception('Documento não encontrado ou fora do seu acesso.');
      }
      throw Exception('Não foi possível baixar o documento.');
    }
  }

  String _mimeFor(String fileName) {
    final ext = fileName.contains('.') ? fileName.split('.').last.toLowerCase() : '';
    return switch (ext) {
      'pdf' => 'application/pdf',
      'png' => 'image/png',
      'jpg' || 'jpeg' => 'image/jpeg',
      'doc' => 'application/msword',
      'docx' =>
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'xls' => 'application/vnd.ms-excel',
      'xlsx' =>
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      _ => 'application/octet-stream',
    };
  }
}
