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
import '../providers/material_provider.dart';
import '../../../core/widgets/app_motion.dart';
import 'widgets/material_card.dart';

class MaterialsScreen extends ConsumerStatefulWidget {
  const MaterialsScreen({super.key});

  @override
  ConsumerState<MaterialsScreen> createState() => _MaterialsScreenState();
}

class _MaterialsScreenState extends ConsumerState<MaterialsScreen> {
  final String _searchQuery = '';

  @override
  Widget build(BuildContext context) {
    final materialsAsync = ref.watch(materialsListProvider);
    final user = ref.watch(authNotifierProvider).user;
    final canManageMaterials = user?.canManageMaterials ?? false;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(materialsListProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Page Header
              AppSectionHeader(
                title: 'Biblioteca de Materiais',
                subtitle: 'Acesse manuais, códigos de conduta, políticas internas e guias do seu setor.',
                trailing: canManageMaterials
                    ? AppButton(
                        text: 'Novo Material',
                        icon: Icons.upload_file_rounded,
                        size: AppButtonSize.sm,
                        onPressed: () => context.push('/materials/new'),
                      )
                    : null,
              ),
              const SizedBox(height: AppSpacing.lg),

              materialsAsync.whenAnimado(
                context,
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
                  message: 'Não foi possível carregar a biblioteca de materiais.',
                  onRetry: () => ref.refresh(materialsListProvider),
                ),
                data: (materials) {
                  final filtered = materials.where((m) {
                    if (_searchQuery.isNotEmpty &&
                        !m.title.toLowerCase().contains(_searchQuery.toLowerCase())) {
                      return false;
                    }
                    return true;
                  }).toList();

                  if (filtered.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.folder_open_rounded,
                      title: 'Nenhum material encontrado',
                      description: 'Não há documentos ou guias disponíveis na biblioteca no momento.',
                    );
                  }

                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 380,
                      mainAxisExtent: 190,
                      crossAxisSpacing: AppSpacing.lg,
                      mainAxisSpacing: AppSpacing.lg,
                    ),
                    itemCount: filtered.length,
                    itemBuilder: (context, index) {
                      final material = filtered[index];
                      return AppFadeIn(
                        delay: AppFadeIn.escalonar(index),
                        child: MaterialCard(
                          material: material,
                          onOpen: () {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text('Abrindo ${material.title}: ${material.fileUrl}'),
                                behavior: SnackBarBehavior.floating,
                              ),
                            );
                          },
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
