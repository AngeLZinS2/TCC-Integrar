import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_avatar.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../models/audit_log_model.dart';
import '../providers/audit_provider.dart';

/// Histórico de atividades administrativas da empresa.
///
/// Somente leitura — não há ação de editar ou excluir aqui, nem no backend.
/// Um log alterável pela interface não serviria como auditoria.
class AuditScreen extends ConsumerStatefulWidget {
  const AuditScreen({super.key});

  @override
  ConsumerState<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends ConsumerState<AuditScreen> {
  String? _action;
  DateTimeRange? _period;

  Future<void> _pickPeriod() async {
    final agora = DateTime.now();
    final escolhido = await showDateRangePicker(
      context: context,
      firstDate: DateTime(agora.year - 2),
      lastDate: agora,
      initialDateRange: _period,
    );
    if (escolhido != null) {
      setState(() => _period = escolhido);
      ref.read(auditProvider.notifier).load(
            dateFrom: escolhido.start,
            dateTo: escolhido.end,
          );
    }
  }

  void _clearFilters() {
    setState(() {
      _action = null;
      _period = null;
    });
    ref.read(auditProvider.notifier).load(clearFilters: true);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(auditProvider);
    final actionsAsync = ref.watch(auditActionsProvider);
    final temFiltro = _action != null || _period != null;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () => ref.read(auditProvider.notifier).load(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Histórico de Atividades',
                subtitle: 'Registro de quem fez o quê na sua empresa.',
                trailing: temFiltro
                    ? AppButton(
                        text: 'Limpar filtros',
                        icon: Icons.filter_alt_off_outlined,
                        variant: AppButtonVariant.ghost,
                        size: AppButtonSize.sm,
                        onPressed: _clearFilters,
                      )
                    : null,
              ),
              const SizedBox(height: AppSpacing.md),

              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth > 640;

                  final filtroAcao = Container(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                    decoration: BoxDecoration(
                      color: context.surfaceColor,
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      border: Border.all(color: context.borderColor),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String?>(
                        value: _action,
                        isExpanded: !isWide,
                        hint: const Text('Todas as ações'),
                        onChanged: (v) {
                          setState(() => _action = v);
                          ref.read(auditProvider.notifier).load(action: v ?? '');
                        },
                        items: [
                          const DropdownMenuItem<String?>(
                            value: null,
                            child: Text('Todas as ações'),
                          ),
                          ...?actionsAsync.valueOrNull?.map(
                            (a) => DropdownMenuItem<String?>(
                              value: a.value,
                              child: Text(a.label),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );

                  final filtroPeriodo = OutlinedButton.icon(
                    onPressed: _pickPeriod,
                    icon: const Icon(Icons.date_range_outlined, size: 17),
                    label: Text(
                      _period == null
                          ? 'Período'
                          : '${_short(_period!.start)} – ${_short(_period!.end)}',
                    ),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: context.textPrimaryColor,
                      side: BorderSide(color: context.borderColor),
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.md,
                        vertical: 16,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.md),
                      ),
                    ),
                  );

                  if (isWide) {
                    return Row(children: [
                      filtroAcao,
                      const SizedBox(width: AppSpacing.md),
                      filtroPeriodo,
                    ]);
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      filtroAcao,
                      const SizedBox(height: AppSpacing.sm),
                      filtroPeriodo,
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.xl),

              state.when(
                loading: () => Column(
                  children: List.generate(
                    5,
                    (_) => const Padding(
                      padding: EdgeInsets.only(bottom: AppSpacing.sm),
                      child: AppSkeleton.card(height: 68),
                    ),
                  ),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar o histórico.',
                  onRetry: () => ref.read(auditProvider.notifier).load(),
                ),
                data: (paged) {
                  if (paged.items.isEmpty) {
                    return AppEmptyState(
                      icon: Icons.history_rounded,
                      title: temFiltro
                          ? 'Nenhuma atividade neste filtro'
                          : 'Nenhuma atividade registrada',
                      description: temFiltro
                          ? 'Ajuste o período ou o tipo de ação.'
                          : 'As ações administrativas da sua empresa aparecerão aqui.',
                      actionText: temFiltro ? 'Limpar filtros' : null,
                      onAction: temFiltro ? _clearFilters : null,
                    );
                  }
                  return Column(
                    children: [
                      ...paged.items.map(
                        (log) => Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                          child: _AuditRow(log: log),
                        ),
                      ),
                      if (paged.hasMore)
                        Padding(
                          padding: const EdgeInsets.only(top: AppSpacing.sm),
                          child: AppButton(
                            text: 'Carregar mais',
                            icon: Icons.expand_more_rounded,
                            variant: AppButtonVariant.outline,
                            isLoading: paged.isLoadingMore,
                            onPressed: () => ref.read(auditProvider.notifier).loadMore(),
                          ),
                        ),
                      Padding(
                        padding: const EdgeInsets.only(top: AppSpacing.md),
                        child: Text(
                          'Mostrando ${paged.items.length} de ${paged.count}',
                          style: TextStyle(fontSize: 12, color: context.textMutedColor),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  static String _short(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}';
}

class _AuditRow extends StatelessWidget {
  final AuditLogModel log;

  const _AuditRow({required this.log});

  /// Cor por natureza da ação: destrutivo em vermelho, criação em verde,
  /// mudança de permissão em roxo — o que precisa de atenção salta à vista.
  AppBadgeVariant get _variant => switch (log.action) {
        'create' => AppBadgeVariant.success,
        'deactivate' || 'delete' => AppBadgeVariant.error,
        'role_change' => AppBadgeVariant.purple,
        'activate' => AppBadgeVariant.success,
        'login' || 'logout' => AppBadgeVariant.neutral,
        _ => AppBadgeVariant.primary,
      };

  @override
  Widget build(BuildContext context) {
    final campos = log.metadata['changed_fields'];
    return Semantics(
      label: '${log.summary}, ${_relative(log.createdAt)}',
      child: AppCard(
        enableHover: false,
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AppAvatar(name: log.actorName.isEmpty ? '?' : log.actorName, size: 34),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    log.summary,
                    style: TextStyle(
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                      height: 1.35,
                      color: context.textPrimaryColor,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Wrap(
                    spacing: AppSpacing.xs,
                    runSpacing: 4,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      AppBadge(label: log.actionDisplay, variant: _variant),
                      if (campos is List && campos.isNotEmpty)
                        Text(
                          'Campos: ${campos.join(", ")}',
                          style: TextStyle(fontSize: 11.5, color: context.textMutedColor),
                        ),
                      if (log.action == 'role_change' && log.metadata['to'] != null)
                        Text(
                          '${log.metadata["from"]} → ${log.metadata["to"]}',
                          style: TextStyle(fontSize: 11.5, color: context.textMutedColor),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Text(
              _relative(log.createdAt),
              style: TextStyle(fontSize: 11.5, color: context.textMutedColor),
            ),
          ],
        ),
      ),
    );
  }

  static String _relative(DateTime? when) {
    if (when == null) return '';
    final local = when.toLocal();
    final agora = DateTime.now();
    final hoje = DateTime(agora.year, agora.month, agora.day);
    final dia = DateTime(local.year, local.month, local.day);
    final hora =
        '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';

    final diff = hoje.difference(dia).inDays;
    if (diff == 0) return 'Hoje às $hora';
    if (diff == 1) return 'Ontem às $hora';
    return '${local.day.toString().padLeft(2, '0')}/'
        '${local.month.toString().padLeft(2, '0')} às $hora';
  }
}
