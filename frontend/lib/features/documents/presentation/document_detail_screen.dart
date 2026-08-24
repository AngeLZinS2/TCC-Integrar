import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../shared/models/document_model.dart';
import '../providers/documents_provider.dart';

// Neste MVP, não estamos carregando "document_detailProvider" no backend,
// então para a tela de detalhe vamos usar os documentos já carregados da lista,
// ou idealmente você criaria um provider fetchDocumentById. 
// Para ser rápido, vamos carregar da lista usando o ID.

class DocumentDetailScreen extends ConsumerStatefulWidget {
  final int documentId;

  const DocumentDetailScreen({super.key, required this.documentId});

  @override
  ConsumerState<DocumentDetailScreen> createState() => _DocumentDetailScreenState();
}

class _DocumentDetailScreenState extends ConsumerState<DocumentDetailScreen> {
  bool _isDownloading = false;
  bool _isAccepting = false;

  Future<void> _handleDownload(DocumentModel doc) async {
    if (doc.activeVersion == null) return;
    setState(() => _isDownloading = true);
    
    try {
      final repo = ref.read(documentsRepositoryProvider);
      await repo.downloadDocument(doc.id, doc.activeVersion!.id, "document_${doc.id}.pdf");
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Download iniciado/concluído.'), backgroundColor: AppColors.success),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro no download: $e'), backgroundColor: AppColors.error),
      );
    } finally {
      if (mounted) setState(() => _isDownloading = false);
    }
  }

  Future<void> _handleAccept(DocumentModel doc) async {
    if (doc.activeVersion == null) return;
    setState(() => _isAccepting = true);
    
    try {
      final repo = ref.read(documentsRepositoryProvider);
      await repo.acceptDocument(doc.id, doc.activeVersion!.id);
      
      if (!mounted) return;
      // Invalidate list to refresh 'hasAccepted' status
      ref.invalidate(documentsListProvider);
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Documento aceito com sucesso!'), backgroundColor: AppColors.success),
      );
      context.pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao aceitar: $e'), backgroundColor: AppColors.error),
      );
    } finally {
      if (mounted) setState(() => _isAccepting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Buscar o documento da lista já carregada:
    final documentsAsync = ref.watch(documentsListProvider(1));
    
    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        title: const Text('Detalhes do Documento'),
        backgroundColor: context.surfaceColor,
        elevation: 0,
      ),
      body: documentsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Erro: $err')),
        data: (response) {
          final doc = response.results.firstWhere((d) => d.id == widget.documentId, orElse: () => throw Exception('Not found'));
          
          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 800),
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(AppSpacing.xxl),
                child: Container(
                  padding: const EdgeInsets.all(AppSpacing.xxl),
                  decoration: BoxDecoration(
                    color: context.surfaceColor,
                    borderRadius: BorderRadius.circular(AppSpacing.lg),
                    border: Border.all(color: context.borderColor),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(AppSpacing.lg),
                            decoration: BoxDecoration(
                              color: AppColors.primary.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(AppSpacing.md),
                            ),
                            child: const Icon(Icons.picture_as_pdf, color: AppColors.primary, size: 48),
                          ),
                          const SizedBox(width: AppSpacing.xl),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(doc.title, style: context.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                                const SizedBox(height: AppSpacing.xs),
                                Text(doc.categoryName ?? 'Geral', style: context.textTheme.labelLarge?.copyWith(color: AppColors.primary)),
                                const SizedBox(height: AppSpacing.lg),
                                Text(doc.description, style: context.textTheme.bodyMedium),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const Divider(height: 48),
                      
                      Text('Status da Versão', style: context.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                      const SizedBox(height: AppSpacing.sm),
                      if (doc.activeVersion != null) ...[
                        Text('Versão ${doc.activeVersion!.versionNumber}', style: context.textTheme.bodyMedium),
                        Text('Publicado em: ${doc.activeVersion!.publishedAt.split('T').first}', style: context.textTheme.bodySmall?.copyWith(color: AppColors.textSecondary)),
                        const SizedBox(height: AppSpacing.xl),
                        Row(
                          children: [
                            AppButton(
                              text: 'Fazer Download Seguro',
                              icon: Icons.download,
                              isLoading: _isDownloading,
                              variant: AppButtonVariant.outline,
                              onPressed: () => _handleDownload(doc),
                            ),
                          ],
                        ),
                      ] else ...[
                        const Text('Este documento não possui arquivos anexados na versão ativa.'),
                      ],
                      
                      if (doc.isRequired) ...[
                        const Divider(height: 48),
                        Text('Obrigatoriedade e Aceite', style: context.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                        const SizedBox(height: AppSpacing.sm),
                        
                        if (doc.hasAccepted)
                          Container(
                            padding: const EdgeInsets.all(AppSpacing.lg),
                            decoration: BoxDecoration(
                              color: AppColors.success.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(AppSpacing.sm),
                              border: Border.all(color: AppColors.success.withValues(alpha: 0.3)),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.check_circle, color: AppColors.success),
                                const SizedBox(width: AppSpacing.md),
                                Expanded(
                                  child: Text('Você já leu e concordou com esta versão do documento.', style: context.textTheme.bodyMedium?.copyWith(color: AppColors.success)),
                                ),
                              ],
                            ),
                          )
                        else
                          Container(
                            padding: const EdgeInsets.all(AppSpacing.lg),
                            decoration: BoxDecoration(
                              color: AppColors.warning.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(AppSpacing.sm),
                              border: Border.all(color: AppColors.warning.withValues(alpha: 0.3)),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                                    const SizedBox(width: AppSpacing.md),
                                    Expanded(
                                      child: Text('Este documento exige sua leitura obrigatória e aceite formal.', style: context.textTheme.bodyMedium?.copyWith(color: Colors.orange[800])),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: AppSpacing.lg),
                                AppButton(
                                  text: 'Li e estou de acordo',
                                  isLoading: _isAccepting,
                                  onPressed: () => _handleAccept(doc),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
