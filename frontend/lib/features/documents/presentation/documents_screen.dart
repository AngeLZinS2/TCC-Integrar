import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../auth/providers/auth_provider.dart';
import '../providers/documents_provider.dart';
import '../../../core/widgets/app_motion.dart';
import '../../../shared/models/document_model.dart';

class DocumentsScreen extends ConsumerWidget {
  const DocumentsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final documentsAsync = ref.watch(documentsListProvider(1));
    final user = ref.watch(authNotifierProvider).user;
    final isRhAdmin = user?.managesCompany ?? false;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(documentsListProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Biblioteca Documental',
                subtitle: 'Consulte manuais, políticas, recibos e documentos corporativos importantes.',
                trailing: isRhAdmin
                    ? AppButton(
                        text: 'Novo Documento',
                        icon: Icons.upload_file,
                        size: AppButtonSize.sm,
                        onPressed: () => context.push('/documents/new'),
                      )
                    : null,
              ),
              const SizedBox(height: AppSpacing.xl),
              
              documentsAsync.whenAnimado(
                context,
                loading: () => ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: 4,
                  separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.md),
                  itemBuilder: (_, __) => const AppSkeleton.card(height: 80),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar os documentos.',
                  onRetry: () => ref.refresh(documentsListProvider(1)),
                ),
                data: (response) {
                  final documents = response.results;
                  if (documents.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.folder_open,
                      title: 'Nenhum documento encontrado',
                      description: 'A biblioteca da empresa está vazia.',
                    );
                  }

                  return ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: documents.length,
                    separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.md),
                    itemBuilder: (context, index) {
                      final doc = documents[index];
                      return AppFadeIn(
                        delay: AppFadeIn.escalonar(index),
                        child: _DocumentListItem(document: doc),
                      );
                    },
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DocumentListItem extends StatelessWidget {
  final DocumentModel document;

  const _DocumentListItem({required this.document});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.push('/documents/${document.id}'),
      borderRadius: BorderRadius.circular(AppSpacing.md),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
        decoration: BoxDecoration(
          color: context.surfaceColor,
          borderRadius: BorderRadius.circular(AppSpacing.md),
          border: Border.all(
            color: (document.isRequired && !document.hasAccepted)
                ? AppColors.warning
                : context.borderColor,
            width: (document.isRequired && !document.hasAccepted) ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AppSpacing.sm),
              ),
              child: const Icon(Icons.description_outlined, color: AppColors.primary),
            ),
            const SizedBox(width: AppSpacing.lg),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        document.title,
                        style: context.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      if (document.isRequired && !document.hasAccepted) ...[
                        const SizedBox(width: AppSpacing.sm),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppColors.warning.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            'Aceite Pendente',
                            style: context.textTheme.labelSmall?.copyWith(
                              color: Colors.orange[800],
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    document.description.isNotEmpty ? document.description : 'Sem descrição.',
                    style: context.textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  document.categoryName ?? 'Sem Categoria',
                  style: context.textTheme.labelMedium?.copyWith(color: AppColors.primary),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  document.activeVersion != null
                      ? 'Versão ${document.activeVersion!.versionNumber}'
                      : 'Sem arquivo',
                  style: context.textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
                ),
              ],
            ),
            const SizedBox(width: AppSpacing.md),
            const Icon(Icons.chevron_right, color: AppColors.textSecondary),
          ],
        ),
      ),
    );
  }
}
