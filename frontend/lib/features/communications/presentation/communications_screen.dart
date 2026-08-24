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
import '../providers/communications_provider.dart';
import '../../../shared/models/announcement_model.dart';

class CommunicationsScreen extends ConsumerStatefulWidget {
  const CommunicationsScreen({super.key});

  @override
  ConsumerState<CommunicationsScreen> createState() => _CommunicationsScreenState();
}

class _CommunicationsScreenState extends ConsumerState<CommunicationsScreen> {
  @override
  Widget build(BuildContext context) {
    final communicationsAsync = ref.watch(communicationsListProvider(1));
    final user = ref.watch(authNotifierProvider).user;
    final isRhAdmin = user?.managesCompany ?? false;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(communicationsListProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Comunicados Oficiais',
                subtitle: 'Fique por dentro das novidades, avisos importantes e eventos da empresa.',
                trailing: isRhAdmin
                    ? AppButton(
                        text: 'Novo Comunicado',
                        icon: Icons.add_alert,
                        size: AppButtonSize.sm,
                        onPressed: () => context.push('/communications/new'),
                      )
                    : null,
              ),
              const SizedBox(height: AppSpacing.xl),
              
              communicationsAsync.when(
                loading: () => ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: 3,
                  separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.lg),
                  itemBuilder: (_, __) => const AppSkeleton.card(height: 120),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar os comunicados.',
                  onRetry: () => ref.refresh(communicationsListProvider(1)),
                ),
                data: (response) {
                  final announcements = response.results;
                  if (announcements.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.campaign_outlined,
                      title: 'Nenhum comunicado',
                      description: 'Sua timeline está vazia no momento.',
                    );
                  }

                  return ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: announcements.length,
                    separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.lg),
                    itemBuilder: (context, index) {
                      final announcement = announcements[index];
                      return _AnnouncementCard(announcement: announcement);
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

class _AnnouncementCard extends ConsumerWidget {
  final Announcement announcement;

  const _AnnouncementCard({required this.announcement});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xl),
      decoration: BoxDecoration(
        color: context.surfaceColor,
        borderRadius: BorderRadius.circular(AppSpacing.md),
        border: Border.all(
          color: announcement.isUrgent ? AppColors.error : context.borderColor,
          width: announcement.isUrgent ? 2 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.02),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (announcement.isUrgent) ...[
                const Icon(Icons.warning_amber_rounded, color: AppColors.error, size: 24),
                const SizedBox(width: AppSpacing.sm),
              ],
              Expanded(
                child: Text(
                  announcement.title,
                  style: context.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: announcement.isUrgent ? AppColors.error : null,
                  ),
                ),
              ),
              if (!announcement.isRead)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(AppSpacing.xs),
                  ),
                  child: Text(
                    'Novo',
                    style: context.textTheme.labelSmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              const Icon(Icons.access_time, size: 16, color: AppColors.textSecondary),
              const SizedBox(width: AppSpacing.xs),
              Text(
                'Publicado em: ${announcement.createdAt.split('T').first}',
                style: context.textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
              const Spacer(),
              if (ref.watch(authNotifierProvider).user?.managesCompany == true) ...[
                const Icon(Icons.remove_red_eye_outlined, size: 16, color: AppColors.textSecondary),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  '${announcement.readCount} leituras',
                  style: context.textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
                ),
              ],
            ],
          ),
          const Divider(height: 32),
          Text(
            announcement.content,
            style: context.textTheme.bodyMedium?.copyWith(height: 1.5),
          ),
          const SizedBox(height: AppSpacing.xl),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Por: ${announcement.authorDetails?['full_name'] ?? 'Diretoria'}',
                style: context.textTheme.bodySmall?.copyWith(
                  fontStyle: FontStyle.italic,
                  color: AppColors.textSecondary,
                ),
              ),
              if (!announcement.isRead)
                AppButton(
                  text: 'Marcar como Lida',
                  icon: Icons.check,
                  size: AppButtonSize.sm,
                  variant: AppButtonVariant.outline,
                  onPressed: () async {
                    try {
                      await ref.read(communicationsRepositoryProvider).markAsRead(announcement.id);
                      ref.invalidate(communicationsListProvider);
                    } catch (e) {
                      // O widget pode ter saido da arvore durante a
                      // requisicao; usar o context sem checar quebra.
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            e.toString().replaceAll('Exception: ', ''),
                          ),
                          backgroundColor: AppColors.error,
                          behavior: SnackBarBehavior.floating,
                        ),
                      );
                    }
                  },
                )
              else
                Row(
                  children: [
                    const Icon(Icons.check_circle, size: 16, color: AppColors.success),
                    const SizedBox(width: AppSpacing.xs),
                    Text(
                      'Lida',
                      style: context.textTheme.bodySmall?.copyWith(
                        color: AppColors.success,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ],
      ),
    );
  }
}
