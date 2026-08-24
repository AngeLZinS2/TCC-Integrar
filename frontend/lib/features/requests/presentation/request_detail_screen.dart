import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_dropdown.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../shared/models/hr_request_model.dart';
import '../../auth/providers/auth_provider.dart';
import '../providers/requests_provider.dart';

class RequestDetailScreen extends ConsumerStatefulWidget {
  final int requestId;

  const RequestDetailScreen({super.key, required this.requestId});

  @override
  ConsumerState<RequestDetailScreen> createState() => _RequestDetailScreenState();
}

class _RequestDetailScreenState extends ConsumerState<RequestDetailScreen> {
  final _commentController = TextEditingController();
  bool _isSubmittingComment = false;
  bool _isChangingStatus = false;

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _addComment() async {
    final text = _commentController.text.trim();
    if (text.isEmpty) return;

    setState(() => _isSubmittingComment = true);
    try {
      final repository = ref.read(requestsRepositoryProvider);
      await repository.addComment(widget.requestId, text);
      _commentController.clear();
      ref.invalidate(requestDetailProvider(widget.requestId));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao enviar comentário: $e'), backgroundColor: AppColors.error),
      );
    } finally {
      if (mounted) setState(() => _isSubmittingComment = false);
    }
  }

  Future<void> _changeStatus(String newStatus) async {
    setState(() => _isChangingStatus = true);
    try {
      final repository = ref.read(requestsRepositoryProvider);
      await repository.updateStatus(widget.requestId, newStatus);
      ref.invalidate(requestDetailProvider(widget.requestId));
      ref.invalidate(requestsListProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao alterar status: $e'), backgroundColor: AppColors.error),
      );
    } finally {
      if (mounted) setState(() => _isChangingStatus = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final requestAsync = ref.watch(requestDetailProvider(widget.requestId));
    final user = ref.watch(authNotifierProvider).user;
    final isRhAdmin = user?.managesCompany ?? false;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        title: const Text('Detalhes da Solicitação'),
        backgroundColor: context.surfaceColor,
        elevation: 0,
      ),
      body: requestAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: AppErrorState(
            message: 'Erro ao carregar os detalhes.',
            onRetry: () => ref.refresh(requestDetailProvider(widget.requestId)),
          ),
        ),
        data: (request) => Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1000),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Esquerda: Detalhes e Status
                Expanded(
                  flex: 1,
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(AppSpacing.xl),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildRequestInfo(context, request),
                        const SizedBox(height: AppSpacing.xl),
                        if (isRhAdmin) _buildStatusControl(context, request),
                        if (!isRhAdmin && request.status != 'closed' && request.status != 'cancelled')
                          _buildCancelControl(context, request),
                      ],
                    ),
                  ),
                ),
                // Direita: Chat / Comentários e Histórico
                Expanded(
                  flex: 2,
                  child: Container(
                    decoration: BoxDecoration(
                      border: Border(left: BorderSide(color: context.borderColor)),
                    ),
                    child: Column(
                      children: [
                        Expanded(
                          child: ListView(
                            padding: const EdgeInsets.all(AppSpacing.xl),
                            children: _buildTimeline(request),
                          ),
                        ),
                        if (request.status != 'closed' && request.status != 'cancelled')
                          _buildCommentInput(context),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRequestInfo(BuildContext context, HRRequest request) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: context.surfaceColor,
        borderRadius: BorderRadius.circular(AppSpacing.md),
        border: Border.all(color: context.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(request.number, style: context.textTheme.labelLarge?.copyWith(color: AppColors.textSecondary)),
          const SizedBox(height: AppSpacing.sm),
          Text(request.subject, style: context.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: AppSpacing.md),
          _InfoRow(label: 'Solicitante', value: request.requesterDetails['full_name'] ?? '-'),
          _InfoRow(label: 'Categoria', value: request.category.toUpperCase()),
          _InfoRow(label: 'Prioridade', value: request.priority.toUpperCase()),
          _InfoRow(label: 'Criado em', value: request.createdAt.split('T').first),
          const Divider(height: 32),
          Text('Descrição', style: context.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: AppSpacing.sm),
          Text(request.description ?? 'Sem descrição.', style: context.textTheme.bodyMedium),
        ],
      ),
    );
  }

  Widget _buildStatusControl(BuildContext context, HRRequest request) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: context.surfaceColor,
        borderRadius: BorderRadius.circular(AppSpacing.md),
        border: Border.all(color: context.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Gestão de Status', style: context.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: AppSpacing.md),
          if (_isChangingStatus)
            const Center(child: CircularProgressIndicator())
          else
            AppDropdown(
              label: 'Status Atual',
              value: request.status,
              options: const [
                AppDropdownOption(value: 'received', label: 'Recebida'),
                AppDropdownOption(value: 'in_progress', label: 'Em Andamento'),
                AppDropdownOption(value: 'resolved', label: 'Resolvida'),
                AppDropdownOption(value: 'closed', label: 'Fechada'),
                AppDropdownOption(value: 'cancelled', label: 'Cancelada'),
              ],
              onChanged: (val) {
                if (val != null && val != request.status) {
                  _changeStatus(val);
                }
              },
            ),
        ],
      ),
    );
  }

  Widget _buildCancelControl(BuildContext context, HRRequest request) {
    return AppButton(
      text: 'Cancelar Solicitação',
      variant: AppButtonVariant.outline,
      fullWidth: true,
      onPressed: () {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Cancelar Solicitação?'),
            content: const Text('Tem certeza que deseja cancelar esta solicitação? Ela não poderá ser reaberta.'),
            actions: [
              TextButton(onPressed: () => ctx.pop(), child: const Text('Não')),
              TextButton(
                onPressed: () {
                  ctx.pop();
                  _changeStatus('cancelled');
                },
                child: const Text('Sim, cancelar'),
              ),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _buildTimeline(HRRequest request) {
    final items = <dynamic>[...request.history, ...request.comments];
    items.sort((a, b) => a.createdAt.compareTo(b.createdAt));

    return items.map((item) {
      if (item is RequestHistory) {
        return _buildHistoryItem(context, item);
      } else if (item is RequestComment) {
        return _buildCommentItem(context, item);
      }
      return const SizedBox.shrink();
    }).toList();
  }

  Widget _buildHistoryItem(BuildContext context, RequestHistory history) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Row(
        children: [
          const Icon(Icons.info_outline, size: 16, color: AppColors.textSecondary),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              '${history.actorDetails?['full_name'] ?? 'Sistema'} ${history.details}',
              style: context.textTheme.bodySmall?.copyWith(color: AppColors.textSecondary, fontStyle: FontStyle.italic),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCommentItem(BuildContext context, RequestComment comment) {
    final isMe = comment.author == ref.read(authNotifierProvider).user?.id;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Row(
        mainAxisAlignment: isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isMe) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: AppColors.primary.withValues(alpha: 0.1),
              child: Text(
                comment.authorDetails['full_name']?[0] ?? 'U',
                style: const TextStyle(color: AppColors.primary, fontSize: 12),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: isMe ? AppColors.primary.withValues(alpha: 0.1) : context.surfaceColor,
                borderRadius: BorderRadius.circular(AppSpacing.md),
                border: Border.all(color: isMe ? Colors.transparent : context.borderColor),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    comment.authorDetails['full_name'] ?? 'Usuário',
                    style: context.textTheme.labelMedium?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(comment.text, style: context.textTheme.bodyMedium),
                ],
              ),
            ),
          ),
          if (isMe) ...[
            const SizedBox(width: AppSpacing.sm),
            CircleAvatar(
              radius: 16,
              backgroundColor: AppColors.primary,
              child: Text(
                comment.authorDetails['full_name']?[0] ?? 'U',
                style: const TextStyle(color: Colors.white, fontSize: 12),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCommentInput(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: context.surfaceColor,
        border: Border(top: BorderSide(color: context.borderColor)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _commentController,
              decoration: const InputDecoration(
                hintText: 'Escreva um comentário...',
                border: OutlineInputBorder(),
              ),
              maxLines: null,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          if (_isSubmittingComment)
            const CircularProgressIndicator()
          else
            IconButton(
              icon: const Icon(Icons.send, color: AppColors.primary),
              onPressed: _addComment,
            ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(label, style: context.textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary)),
          ),
          Expanded(
            child: Text(value, style: context.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }
}
