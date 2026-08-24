import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../providers/requests_provider.dart';
import 'widgets/request_card.dart';

class RequestsScreen extends ConsumerStatefulWidget {
  const RequestsScreen({super.key});

  @override
  ConsumerState<RequestsScreen> createState() => _RequestsScreenState();
}

class _RequestsScreenState extends ConsumerState<RequestsScreen> {
  String _selectedStatus = ''; // Vazio para "Todas"

  @override
  Widget build(BuildContext context) {
    final filters = <String, dynamic>{};
    if (_selectedStatus.isNotEmpty) {
      filters['status'] = _selectedStatus;
    }

    final requestsAsync = ref.watch(requestsListProvider(filters));

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(requestsListProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Solicitações de RH',
                subtitle: 'Acompanhe seus chamados, dúvidas e requisições abertas junto ao RH.',
                trailing: AppButton(
                  text: 'Nova Solicitação',
                  icon: Icons.add,
                  size: AppButtonSize.sm,
                  onPressed: () => context.push('/requests/new'),
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              _buildFilters(),
              const SizedBox(height: AppSpacing.lg),

              requestsAsync.when(
                loading: () => GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 380,
                    mainAxisExtent: 180,
                    crossAxisSpacing: AppSpacing.lg,
                    mainAxisSpacing: AppSpacing.lg,
                  ),
                  itemCount: 4,
                  itemBuilder: (_, __) => const AppSkeleton.card(height: 180),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar as solicitações.',
                  onRetry: () => ref.refresh(requestsListProvider(filters)),
                ),
                data: (response) {
                  final requests = response.results;
                  if (requests.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.forum_outlined,
                      title: 'Nenhuma solicitação',
                      description: 'Você ainda não possui chamados abertos nesta categoria.',
                    );
                  }

                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 380,
                      mainAxisExtent: 180,
                      crossAxisSpacing: AppSpacing.lg,
                      mainAxisSpacing: AppSpacing.lg,
                    ),
                    itemCount: requests.length,
                    itemBuilder: (context, index) {
                      final request = requests[index];
                      return RequestCard(
                        request: request,
                        onTap: () => context.push('/requests/${request.id}'),
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

  Widget _buildFilters() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _FilterChip(
            label: 'Todas',
            isSelected: _selectedStatus.isEmpty,
            onTap: () => setState(() => _selectedStatus = ''),
          ),
          const SizedBox(width: AppSpacing.sm),
          _FilterChip(
            label: 'Abertas',
            isSelected: _selectedStatus == 'received',
            onTap: () => setState(() => _selectedStatus = 'received'),
          ),
          const SizedBox(width: AppSpacing.sm),
          _FilterChip(
            label: 'Em Andamento',
            isSelected: _selectedStatus == 'in_progress',
            onTap: () => setState(() => _selectedStatus = 'in_progress'),
          ),
          const SizedBox(width: AppSpacing.sm),
          _FilterChip(
            label: 'Resolvidas',
            isSelected: _selectedStatus == 'resolved',
            onTap: () => setState(() => _selectedStatus = 'resolved'),
          ),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.primary : context.surfaceColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? AppColors.primary : context.borderColor,
          ),
        ),
        child: Text(
          label,
          style: context.textTheme.labelMedium?.copyWith(
            color: isSelected ? Colors.white : AppColors.textSecondary,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          ),
        ),
      ),
    );
  }
}
