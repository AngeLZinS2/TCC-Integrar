import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_avatar.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../models/directory_entry_model.dart';
import '../providers/directory_provider.dart';

enum _ViewMode { directory, orgChart }

class DirectoryScreen extends ConsumerStatefulWidget {
  const DirectoryScreen({super.key});

  @override
  ConsumerState<DirectoryScreen> createState() => _DirectoryScreenState();
}

class _DirectoryScreenState extends ConsumerState<DirectoryScreen> {
  final _searchController = TextEditingController();
  String _search = '';
  String? _sectorFilter;
  String? _positionFilter;
  _ViewMode _mode = _ViewMode.directory;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<DirectoryEntryModel> _applyFilter(List<DirectoryEntryModel> entries) {
    var filtered = entries;

    if (_sectorFilter != null) {
      filtered = filtered.where((e) => e.sectorName == _sectorFilter).toList();
    }
    if (_positionFilter != null) {
      filtered = filtered.where((e) => e.positionName == _positionFilter).toList();
    }
    if (_search.isNotEmpty) {
      final query = _search.toLowerCase();
      filtered = filtered
          .where((e) =>
              e.fullName.toLowerCase().contains(query) ||
              e.email.toLowerCase().contains(query))
          .toList();
    }
    return filtered;
  }

  /// Opções de filtro derivadas da própria lista — só aparecem valores que
  /// existem de fato, sem oferecer um filtro que devolveria vazio.
  List<String> _distinct(List<DirectoryEntryModel> entries, String? Function(DirectoryEntryModel) pick) {
    final values = entries.map(pick).whereType<String>().toSet().toList()..sort();
    return values;
  }

  Widget _filterDropdown({
    required BuildContext context,
    required String hint,
    required String? value,
    required List<String> options,
    required ValueChanged<String?> onChanged,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        color: context.surfaceColor,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: context.borderColor),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String?>(
          value: options.contains(value) ? value : null,
          hint: Text(hint),
          onChanged: onChanged,
          items: [
            DropdownMenuItem<String?>(value: null, child: Text(hint)),
            ...options.map((o) => DropdownMenuItem<String?>(value: o, child: Text(o))),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final directoryAsync = ref.watch(directoryListProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(directoryListProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const AppSectionHeader(
                title: 'Equipe',
                subtitle: 'Diretório e organograma dos colegas da sua empresa.',
              ),
              const SizedBox(height: AppSpacing.md),
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth > 640;
                  final searchField = TextField(
                    controller: _searchController,
                    onChanged: (value) => setState(() => _search = value),
                    decoration: InputDecoration(
                      hintText: 'Buscar por nome ou e-mail...',
                      prefixIcon: const Icon(Icons.search_rounded, size: 20),
                      filled: true,
                      fillColor: context.surfaceColor,
                      contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(AppRadius.md),
                        borderSide: BorderSide(color: context.borderColor),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(AppRadius.md),
                        borderSide: BorderSide(color: context.borderColor),
                      ),
                    ),
                  );
                  final modeToggle = _ModeToggle(
                    mode: _mode,
                    onChanged: (mode) => setState(() => _mode = mode),
                  );

                  final todos = directoryAsync.valueOrNull ?? const <DirectoryEntryModel>[];
                  final filtroSetor = _filterDropdown(
                    context: context,
                    hint: 'Todos os setores',
                    value: _sectorFilter,
                    options: _distinct(todos, (e) => e.sectorName),
                    onChanged: (v) => setState(() {
                      _sectorFilter = v;
                      _positionFilter = null; // cargo depende do setor
                    }),
                  );
                  final filtroCargo = _filterDropdown(
                    context: context,
                    hint: 'Todos os cargos',
                    value: _positionFilter,
                    options: _distinct(
                      _sectorFilter == null
                          ? todos
                          : todos.where((e) => e.sectorName == _sectorFilter).toList(),
                      (e) => e.positionName,
                    ),
                    onChanged: (v) => setState(() => _positionFilter = v),
                  );

                  if (isWide) {
                    return Column(
                      children: [
                        Row(
                          children: [
                            Expanded(child: searchField),
                            const SizedBox(width: AppSpacing.md),
                            modeToggle,
                          ],
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        Row(
                          children: [
                            Expanded(child: filtroSetor),
                            const SizedBox(width: AppSpacing.md),
                            Expanded(child: filtroCargo),
                          ],
                        ),
                      ],
                    );
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      searchField,
                      const SizedBox(height: AppSpacing.sm),
                      filtroSetor,
                      const SizedBox(height: AppSpacing.sm),
                      filtroCargo,
                      const SizedBox(height: AppSpacing.sm),
                      modeToggle,
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.xl),
              directoryAsync.when(
                loading: () => Column(
                  children: List.generate(
                    4,
                    (_) => const Padding(
                      padding: EdgeInsets.only(bottom: AppSpacing.md),
                      child: AppSkeleton.card(height: 76),
                    ),
                  ),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar a equipe.',
                  onRetry: () => ref.invalidate(directoryListProvider),
                ),
                data: (entries) {
                  final filtered = _applyFilter(entries);
                  if (filtered.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.people_outline_rounded,
                      title: 'Nenhum colega encontrado',
                      description: 'Ajuste a busca para encontrar quem você procura.',
                    );
                  }
                  return _mode == _ViewMode.directory
                      ? _DirectoryList(entries: filtered)
                      : _OrgChart(entries: filtered);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ModeToggle extends StatelessWidget {
  final _ViewMode mode;
  final ValueChanged<_ViewMode> onChanged;

  const _ModeToggle({required this.mode, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: context.isDark ? const Color(0xFF1E293B) : AppColors.slate100,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: context.borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _ModeButton(
            label: 'Diretório',
            icon: Icons.list_alt_rounded,
            selected: mode == _ViewMode.directory,
            onTap: () => onChanged(_ViewMode.directory),
          ),
          _ModeButton(
            label: 'Organograma',
            icon: Icons.account_tree_outlined,
            selected: mode == _ViewMode.orgChart,
            onTap: () => onChanged(_ViewMode.orgChart),
          ),
        ],
      ),
    );
  }
}

class _ModeButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  const _ModeButton({required this.label, required this.icon, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
        decoration: BoxDecoration(
          color: selected ? context.surfaceColor : Colors.transparent,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          boxShadow: selected ? context.shadowSm : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 16,
              color: selected
                  ? (isDark ? AppColors.primary400 : AppColors.primary)
                  : context.textMutedColor,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              label,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: selected ? context.textPrimaryColor : context.textMutedColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DirectoryList extends StatelessWidget {
  final List<DirectoryEntryModel> entries;

  const _DirectoryList({required this.entries});

  @override
  Widget build(BuildContext context) {
    final sorted = [...entries]..sort((a, b) => a.fullName.compareTo(b.fullName));
    return Column(
      children: sorted
          .map((entry) => Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.md),
                child: _DirectoryCard(entry: entry),
              ))
          .toList(),
    );
  }
}

class _DirectoryCard extends StatelessWidget {
  final DirectoryEntryModel entry;

  const _DirectoryCard({required this.entry});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      enableHover: false,
      child: Row(
        children: [
          AppAvatar(name: entry.fullName, size: 42),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry.fullName,
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
                ),
                Text(
                  entry.email,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 12, color: context.textSecondaryColor),
                ),
              ],
            ),
          ),
          Wrap(
            spacing: AppSpacing.xs,
            children: [
              if (entry.isRHAdmin) const AppBadge(label: 'RH Admin', variant: AppBadgeVariant.purple),
              if (entry.sectorName != null)
                AppBadge(label: entry.sectorName!, variant: AppBadgeVariant.primary),
              if (entry.positionName != null)
                AppBadge(label: entry.positionName!, variant: AppBadgeVariant.neutral),
            ],
          ),
        ],
      ),
    );
  }
}

class _OrgChart extends StatelessWidget {
  final List<DirectoryEntryModel> entries;

  const _OrgChart({required this.entries});

  @override
  Widget build(BuildContext context) {
    final bySector = <String, Map<String, List<DirectoryEntryModel>>>{};
    for (final entry in entries) {
      final sectorKey = entry.sectorName ?? 'Sem setor';
      final positionKey = entry.positionName ?? 'Sem cargo definido';
      bySector.putIfAbsent(sectorKey, () => {});
      bySector[sectorKey]!.putIfAbsent(positionKey, () => []).add(entry);
    }
    final sectorNames = bySector.keys.toList()..sort();

    return Column(
      children: sectorNames.map((sectorName) {
        final positions = bySector[sectorName]!;
        final positionNames = positions.keys.toList()..sort();
        final total = positions.values.fold<int>(0, (sum, list) => sum + list.length);

        return Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.lg),
          child: AppCard(
            enableHover: false,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.apartment_rounded, size: 18, color: context.textMutedColor),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: Text(
                        sectorName,
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: context.textPrimaryColor),
                      ),
                    ),
                    AppBadge(label: '$total pessoa${total == 1 ? '' : 's'}', variant: AppBadgeVariant.neutral),
                  ],
                ),
                const SizedBox(height: AppSpacing.lg),
                for (final positionName in positionNames) ...[
                  Text(
                    positionName,
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: context.textMutedColor),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Wrap(
                    spacing: AppSpacing.sm,
                    runSpacing: AppSpacing.sm,
                    children: positions[positionName]!
                        .map((entry) => _PersonChip(entry: entry))
                        .toList(),
                  ),
                  if (positionName != positionNames.last) const SizedBox(height: AppSpacing.lg),
                ],
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _PersonChip extends StatelessWidget {
  final DirectoryEntryModel entry;

  const _PersonChip({required this.entry});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: 6),
      decoration: BoxDecoration(
        color: context.isDark ? const Color(0xFF1E293B) : AppColors.slate50,
        borderRadius: BorderRadius.circular(AppRadius.pill),
        border: Border.all(color: context.borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppAvatar(name: entry.fullName, size: 24),
          const SizedBox(width: AppSpacing.xs),
          Text(
            entry.fullName,
            style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: context.textPrimaryColor),
          ),
        ],
      ),
    );
  }
}
