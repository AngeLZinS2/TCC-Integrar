import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../shared/models/quiz_model.dart';
import '../providers/quiz_provider.dart';
import '../../../core/widgets/app_motion.dart';

/// Certificados emitidos.
///
/// O código é o que torna o certificado verificável por quem está fora do
/// sistema, então copiá-lo precisa ser a ação mais fácil da tela.
class CertificatesScreen extends ConsumerWidget {
  const CertificatesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final certificadosAsync = ref.watch(certificatesProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(certificatesProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const AppSectionHeader(
                title: 'Certificados',
                subtitle:
                    'Comprovantes de conclusão emitidos na aprovação das avaliações.',
              ),
              const SizedBox(height: AppSpacing.xl),
              certificadosAsync.whenAnimado(
                context,
                loading: () => GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate:
                      const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 380,
                    mainAxisExtent: 180,
                    crossAxisSpacing: AppSpacing.lg,
                    mainAxisSpacing: AppSpacing.lg,
                  ),
                  itemCount: 3,
                  itemBuilder: (_, __) => const AppSkeleton.card(height: 180),
                ),
                error: (_, __) => AppErrorState(
                  message: 'Não foi possível carregar os certificados.',
                  onRetry: () => ref.invalidate(certificatesProvider),
                ),
                data: (resposta) {
                  final certificados = resposta.results;
                  if (certificados.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.workspace_premium_outlined,
                      title: 'Nenhum certificado ainda',
                      description:
                          'Conclua um treinamento com avaliação e seja aprovado para receber o seu.',
                    );
                  }
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate:
                        const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 380,
                      mainAxisExtent: 180,
                      crossAxisSpacing: AppSpacing.lg,
                      mainAxisSpacing: AppSpacing.lg,
                    ),
                    itemCount: certificados.length,
                    itemBuilder: (_, i) => AppFadeIn(
                      delay: AppFadeIn.escalonar(i),
                      child: _CertificateCard(certificate: certificados[i]),
                    ),
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

class _CertificateCard extends StatelessWidget {
  final CertificateModel certificate;

  const _CertificateCard({required this.certificate});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label:
          'Certificado de ${certificate.courseTitle}, nota ${certificate.score} por cento, código ${certificate.code}',
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.workspace_premium,
                  color: AppColors.warning,
                  size: 22,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    certificate.courseTitle,
                    style: context.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: context.textPrimaryColor,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              certificate.userName,
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textSecondaryColor,
              ),
            ),
            Text(
              'Nota ${certificate.score}% · ${_data(certificate.issuedAt)}',
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textMutedColor,
              ),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.md,
                vertical: AppSpacing.sm,
              ),
              decoration: BoxDecoration(
                color: context.subtleBg,
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      certificate.code,
                      style: context.textTheme.bodySmall?.copyWith(
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w600,
                        color: context.textPrimaryColor,
                      ),
                    ),
                  ),
                  Semantics(
                    button: true,
                    label: 'Copiar código do certificado',
                    child: IconButton(
                      icon: const Icon(Icons.copy, size: 16),
                      tooltip: 'Copiar código',
                      onPressed: () => _copiar(context),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _copiar(BuildContext context) {
    Clipboard.setData(ClipboardData(text: certificate.code));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Código copiado.'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  static String _data(String iso) {
    final data = DateTime.tryParse(iso);
    if (data == null) return iso;
    return '${data.day.toString().padLeft(2, '0')}/'
        '${data.month.toString().padLeft(2, '0')}/${data.year}';
  }
}
