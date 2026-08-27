import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../shared/models/integration_model.dart';
import '../providers/integrations_provider.dart';

/// Consulta escrita pelo administrador.
///
/// A seção 10 da P4 pede que não exista campo de SQL livre. Ele existe por
/// decisão explícita de produto — alguns ERPs exigem JOIN ou filtro que o
/// mapeamento estruturado não expressa.
///
/// A tela leva isso a sério em vez de esconder: diz o que é permitido, o
/// que é bloqueado, e que toda execução fica registrada. Um administrador
/// que não sabe que está sendo auditado não teve a chance de decidir.
class QueryConsole extends ConsumerStatefulWidget {
  const QueryConsole({super.key});

  @override
  ConsumerState<QueryConsole> createState() => _QueryConsoleState();
}

class _QueryConsoleState extends ConsumerState<QueryConsole> {
  final _sql = TextEditingController();
  bool _executando = false;
  bool _aberto = false;
  ResultadoDaConsulta? _resultado;

  @override
  void dispose() {
    _sql.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () => setState(() => _aberto = !_aberto),
            child: Row(
              children: [
                const Icon(Icons.terminal, size: 20, color: AppColors.primary),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Consulta avançada',
                        style: context.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: context.textPrimaryColor,
                        ),
                      ),
                      Text(
                        'Escreva um SELECT quando precisar de um filtro ou '
                        'junção que os campos acima não cobrem.',
                        style: context.textTheme.bodySmall
                            ?.copyWith(color: context.textSecondaryColor),
                      ),
                    ],
                  ),
                ),
                Icon(
                  _aberto ? Icons.expand_less : Icons.expand_more,
                  color: context.textSecondaryColor,
                ),
              ],
            ),
          ),

          if (_aberto) ...[
            const SizedBox(height: AppSpacing.xl),
            const _Regras(),
            const SizedBox(height: AppSpacing.lg),

            TextField(
              controller: _sql,
              maxLines: 8,
              minLines: 4,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 13,
                height: 1.5,
              ),
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText:
                    'SELECT "MATRICULA", "NOMEFUNC"\nFROM "FUNCIONARIOS"\nWHERE "SITUACAO" = \'A\'',
                hintStyle: TextStyle(fontFamily: 'monospace', fontSize: 13),
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            Row(
              children: [
                AppButton(
                  text: 'Executar leitura',
                  icon: Icons.play_arrow,
                  isLoading: _executando,
                  onPressed: _executando ? null : _executar,
                ),
                const SizedBox(width: AppSpacing.md),
                Text(
                  'Devolve no máximo 50 linhas.',
                  style: context.textTheme.bodySmall
                      ?.copyWith(color: context.textMutedColor),
                ),
              ],
            ),

            if (_resultado != null) ...[
              const SizedBox(height: AppSpacing.xl),
              _Resultado(resultado: _resultado!),
            ],
          ],
        ],
      ),
    );
  }

  Future<void> _executar() async {
    final sql = _sql.text.trim();
    if (sql.isEmpty) return;

    setState(() {
      _executando = true;
      _resultado = null;
    });

    final resultado =
        await ref.read(integrationsRepositoryProvider).executarConsulta(sql);

    if (!mounted) return;
    setState(() {
      _resultado = resultado;
      _executando = false;
    });
  }
}

/// O que vale e o que não vale, dito antes de a pessoa escrever.
///
/// Descobrir a regra pela mensagem de erro é pior: parece defeito do
/// sistema, e não limite deliberado.
class _Regras extends StatelessWidget {
  const _Regras();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.warning.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.info_outline, size: 16, color: AppColors.warning),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'Somente leitura, e uma instrução por vez',
                style: context.textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: context.textPrimaryColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE e '
            'qualquer outro comando que altere o banco são recusados antes '
            'de chegar ao servidor. Duas instruções separadas por ponto e '
            'vírgula também.\n\n'
            'Toda execução fica registrada na auditoria, com a consulta '
            'inteira e o autor.',
            style: context.textTheme.bodySmall?.copyWith(
              color: context.textSecondaryColor,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _Resultado extends StatelessWidget {
  final ResultadoDaConsulta resultado;

  const _Resultado({required this.resultado});

  @override
  Widget build(BuildContext context) {
    if (!resultado.ok) {
      final cor = resultado.bloqueada ? AppColors.error : AppColors.warning;
      return Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: cor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: cor.withValues(alpha: 0.3)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              resultado.bloqueada ? Icons.block : Icons.error_outline,
              size: 18,
              color: cor,
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // A distinção importa: bloqueada é REGRA, e insistir na
                  // sintaxe não vai resolver.
                  Text(
                    resultado.bloqueada
                        ? 'Consulta bloqueada pela regra de somente leitura'
                        : 'O banco recusou a consulta',
                    style: context.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: context.textPrimaryColor,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    resultado.erro!,
                    style: context.textTheme.bodySmall
                        ?.copyWith(color: context.textSecondaryColor),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    if (resultado.linhas.isEmpty) {
      return Text(
        'A consulta rodou e não devolveu nenhuma linha.',
        style: context.textTheme.bodySmall
            ?.copyWith(color: context.textSecondaryColor),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(
              Icons.check_circle_outline,
              size: 16,
              color: AppColors.success,
            ),
            const SizedBox(width: AppSpacing.sm),
            Text(
              '${resultado.linhas.length} linha(s). Nada foi alterado no seu banco.',
              style: context.textTheme.bodySmall
                  ?.copyWith(color: context.textSecondaryColor),
            ),
            const Spacer(),
            Semantics(
              button: true,
              label: 'Copiar resultado',
              child: IconButton(
                icon: const Icon(Icons.copy, size: 16),
                tooltip: 'Copiar como texto',
                onPressed: () => _copiar(context),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        // Rola nos dois eixos: um SELECT de ERP costuma trazer muitas
        // colunas, e espremê-las tornaria o resultado ilegível justamente
        // onde ele precisa ser conferido.
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 320),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SingleChildScrollView(
              child: DataTable(
                columnSpacing: AppSpacing.xl,
                headingRowHeight: 36,
                dataRowMinHeight: 32,
                dataRowMaxHeight: 32,
                columns: [
                  for (final c in resultado.colunas)
                    DataColumn(
                      label: Text(
                        c,
                        style: context.textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ),
                ],
                rows: [
                  for (final linha in resultado.linhas)
                    DataRow(
                      cells: [
                        for (final c in resultado.colunas)
                          DataCell(
                            Text(
                              linha[c] ?? '',
                              style: context.textTheme.bodySmall
                                  ?.copyWith(fontFamily: 'monospace'),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                      ],
                    ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  void _copiar(BuildContext context) {
    final cabecalho = resultado.colunas.join('\t');
    final corpo = resultado.linhas
        .map((l) => resultado.colunas.map((c) => l[c] ?? '').join('\t'))
        .join('\n');
    Clipboard.setData(ClipboardData(text: '$cabecalho\n$corpo'));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Resultado copiado.'),
        backgroundColor: AppColors.success,
      ),
    );
  }
}
