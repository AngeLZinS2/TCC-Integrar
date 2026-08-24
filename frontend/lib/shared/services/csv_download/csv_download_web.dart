import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

/// Dispara o download de um arquivo no navegador via Blob + elemento <a>.
///
/// Os bytes vêm de uma requisição autenticada feita pelo Dio — nunca de uma
/// URL aberta direto no navegador, que não carregaria o token JWT e faria o
/// backend recusar o acesso.
void saveFile(
  List<int> bytes,
  String filename, {
  String mimeType = 'application/octet-stream',
}) {
  final blob = web.Blob(
    [Uint8List.fromList(bytes).toJS].toJS,
    web.BlobPropertyBag(type: mimeType),
  );
  final url = web.URL.createObjectURL(blob);
  final anchor = web.document.createElement('a') as web.HTMLAnchorElement
    ..href = url
    ..download = filename;
  anchor.click();
  web.URL.revokeObjectURL(url);
}

void saveCsv(List<int> bytes, String filename) =>
    saveFile(bytes, filename, mimeType: 'text/csv');
