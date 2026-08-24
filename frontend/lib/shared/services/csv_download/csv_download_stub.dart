// Implementação usada em plataformas não-web (mobile/desktop), onde o
// download direto de arquivo não é aplicável do mesmo jeito que na web.

void saveFile(List<int> bytes, String filename, {String mimeType = 'application/octet-stream'}) {
  throw UnsupportedError('Download de arquivo disponível apenas na versão Web.');
}

void saveCsv(List<int> bytes, String filename) =>
    saveFile(bytes, filename, mimeType: 'text/csv');
