import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../providers/notification_provider.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(notificationsProvider);
    final unreadCount = ref.watch(unreadNotificationsCountProvider);
    final isDark = context.isDark;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () => ref.read(notificationsProvider.notifier).loadNotifications(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Page Header with Mark All as Read button
              AppSectionHeader(
                title: 'Central de Notificações',
                subtitle: 'Acompanhe avisos de novos treinamentos, conclusões e recados do RH.',
                trailing: unreadCount > 0
                    ? AppButton(
                        text: 'Marcar todas como lidas',
                        variant: AppButtonVariant.ghost,
                        size: AppButtonSize.sm,
                        onPressed: () {
                          ref.read(notificationsProvider.notifier).markAllAsRead();
                        },
                      )
                    : null,
              ),
              const SizedBox(height: AppSpacing.lg),

              notificationsAsync.when(
                loading: () => ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: 3,
                  separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.sm),
                  itemBuilder: (_, __) => const AppSkeleton.card(height: 80),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar as notificações.',
                  onRetry: () => ref.read(notificationsProvider.notifier).loadNotifications(),
                ),
                data: (notifications) {
                  if (notifications.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.notifications_none_rounded,
                      title: 'Você está em dia!',
                      description: 'Não há nenhuma notificação pendente no momento.',
                    );
                  }

                  return ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: notifications.length,
                    separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.sm),
                    itemBuilder: (context, index) {
                      final item = notifications[index];
                      final isUnread = !item.isRead;

                      final cardBg = isUnread
                          ? (isDark ? const Color(0xFF1E293B) : Colors.white)
                          : (isDark ? const Color(0xFF0F172A) : AppColors.slate50);

                      final cardBorder = isUnread
                          ? (isDark ? const Color(0xFF1D4ED8).withValues(alpha: 0.5) : AppColors.primary200)
                          : context.borderColor;

                      return AppCard(
                        onTap: isUnread
                            ? () => ref.read(notificationsProvider.notifier).markAsRead(item.id)
                            : null,
                        padding: const EdgeInsets.all(AppSpacing.lg),
                        backgroundColor: cardBg,
                        borderColor: cardBorder,
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                color: isUnread
                                    ? (isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.4) : AppColors.primary50)
                                    : (isDark ? const Color(0xFF1E293B) : AppColors.slate200),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                isUnread ? Icons.notifications_active_rounded : Icons.notifications_outlined,
                                size: 20,
                                color: isUnread
                                    ? (isDark ? AppColors.primary300 : AppColors.primary)
                                    : (isDark ? AppColors.darkTextMuted : AppColors.slate500),
                              ),
                            ),
                            const SizedBox(width: AppSpacing.lg),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          item.title,
                                          style: TextStyle(
                                            fontSize: 14,
                                            fontWeight: isUnread ? FontWeight.w700 : FontWeight.w600,
                                            color: context.textPrimaryColor,
                                          ),
                                        ),
                                      ),
                                      if (isUnread) ...[
                                        Container(
                                          width: 8,
                                          height: 8,
                                          decoration: const BoxDecoration(
                                            color: AppColors.primary,
                                            shape: BoxShape.circle,
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                      ],
                                      Text(
                                        item.timeAgo,
                                        style: TextStyle(fontSize: 11, color: context.textMutedColor),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    item.message,
                                    style: TextStyle(
                                      fontSize: 13,
                                      color: isUnread ? context.textSecondaryColor : context.textMutedColor,
                                      height: 1.4,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
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
