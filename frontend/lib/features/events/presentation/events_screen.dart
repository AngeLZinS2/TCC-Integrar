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
import '../providers/events_provider.dart';
import '../../../core/widgets/app_motion.dart';
import '../../../shared/models/event_model.dart';

class EventsScreen extends ConsumerWidget {
  const EventsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authNotifierProvider).user;
    final isRhAdmin = user?.managesCompany ?? false;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(eventsListProvider);
          ref.invalidate(birthdaysListProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Eventos e Agenda',
                subtitle: 'Acompanhe os próximos eventos da empresa e aniversariantes do mês.',
                trailing: isRhAdmin
                    ? AppButton(
                        text: 'Novo Evento',
                        icon: Icons.add,
                        size: AppButtonSize.sm,
                        onPressed: () => context.push('/events/new'),
                      )
                    : null,
              ),
              const SizedBox(height: AppSpacing.xl),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Coluna Esquerda: Eventos
                  Expanded(
                    flex: 2,
                    child: _buildEventsList(context, ref),
                  ),
                  const SizedBox(width: AppSpacing.xxl),
                  // Coluna Direita: Aniversariantes
                  Expanded(
                    flex: 1,
                    child: _buildBirthdaysList(context, ref),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEventsList(BuildContext context, WidgetRef ref) {
    final eventsAsync = ref.watch(eventsListProvider(1));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Próximos Eventos',
          style: context.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: AppSpacing.lg),
        eventsAsync.whenAnimado(
                context,
          loading: () => ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: 3,
            separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.md),
            itemBuilder: (_, __) => const AppSkeleton.card(height: 100),
          ),
          error: (err, _) => AppErrorState(
            message: 'Erro ao carregar eventos.',
            onRetry: () => ref.refresh(eventsListProvider(1)),
          ),
          data: (response) {
            final events = response.results;
            if (events.isEmpty) {
              return const AppEmptyState(
                icon: Icons.event_available,
                title: 'Nenhum evento próximo',
                description: 'A agenda da empresa está livre no momento.',
              );
            }
            return ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: events.length,
              separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.md),
              itemBuilder: (context, index) {
                final event = events[index];
                return AppFadeIn(
                  delay: AppFadeIn.escalonar(index),
                  child: _EventCard(event: event),
                );
              },
            );
          },
        ),
      ],
    );
  }

  Widget _buildBirthdaysList(BuildContext context, WidgetRef ref) {
    final birthdaysAsync = ref.watch(birthdaysListProvider);

    return Container(
      padding: const EdgeInsets.all(AppSpacing.xl),
      decoration: BoxDecoration(
        color: context.surfaceColor,
        borderRadius: BorderRadius.circular(AppSpacing.lg),
        border: Border.all(color: context.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.cake_outlined, color: AppColors.primary),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'Aniversariantes (Próx. 30 dias)',
                style: context.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          birthdaysAsync.when(
            loading: () => const CircularProgressIndicator(),
            error: (err, _) => const Text('Erro ao carregar.'),
            data: (birthdays) {
              if (birthdays.isEmpty) {
                return Text(
                  'Nenhum aniversariante próximo.',
                  style: context.textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
                );
              }
              return ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: birthdays.length,
                separatorBuilder: (_, __) => const Divider(height: AppSpacing.xl),
                itemBuilder: (context, index) {
                  final b = birthdays[index];

                  return Row(
                    children: [
                      CircleAvatar(
                        radius: 20,
                        backgroundColor: AppColors.primary.withValues(alpha: 0.1),
                        child: Text(
                          b.fullName[0].toUpperCase(),
                          style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(b.fullName, style: context.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.bold)),
                            Text(b.sectorName ?? 'Colaborador', style: context.textTheme.bodySmall?.copyWith(color: AppColors.textSecondary)),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          b.birthday,
                          style: context.textTheme.labelMedium?.copyWith(color: AppColors.primary, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  );
                },
              );
            },
          ),
        ],
      ),
    );
  }
}

class _EventCard extends StatelessWidget {
  final EventModel event;

  const _EventCard({required this.event});

  @override
  Widget build(BuildContext context) {
    // A API devolve ISO (YYYY-MM-DD). O cartao mostra dia e mes
    // separados, no formato de folhinha.
    final parts = event.date.split('-');
    final dia = parts.length >= 3 ? parts[2] : '--';
    final mes = parts.length >= 3 ? _mesAbreviado(parts[1]) : '--';

    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: context.surfaceColor,
        borderRadius: BorderRadius.circular(AppSpacing.md),
        border: Border.all(color: context.borderColor),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(AppSpacing.sm),
            ),
            child: Column(
              children: [
                Text(
                  dia,
                  style: context.textTheme.titleLarge?.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  mes,
                  style: context.textTheme.labelMedium?.copyWith(
                    color: AppColors.primary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  event.title,
                  style: context.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  event.description,
                  style: context.textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
                ),
                const SizedBox(height: AppSpacing.sm),
                Row(
                  children: [
                    const Icon(Icons.person_outline, size: 14, color: AppColors.textSecondary),
                    const SizedBox(width: AppSpacing.xs),
                    Text(
                      'Por: ${event.authorDetails?['full_name'] ?? 'RH'}',
                      style: context.textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// "08" -> "AGO". Mes por extenso abreviado le melhor que um numero solto.
String _mesAbreviado(String mm) {
  const meses = [
    'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN',
    'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ',
  ];
  final n = int.tryParse(mm);
  if (n == null || n < 1 || n > 12) return mm;
  return meses[n - 1];
}
