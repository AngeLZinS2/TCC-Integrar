import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_progress.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../shared/models/quiz_model.dart';
import '../providers/quiz_provider.dart';

/// Responder a avaliação de um treinamento.
///
/// Três momentos numa tela só: a apresentação (com as regras), o
/// questionário e o resultado. Navegar entre rotas perderia as respostas
/// já marcadas se a pessoa voltasse sem querer.
class QuizScreen extends ConsumerStatefulWidget {
  final int courseId;
  final String courseTitle;

  const QuizScreen({
    super.key,
    required this.courseId,
    required this.courseTitle,
  });

  @override
  ConsumerState<QuizScreen> createState() => _QuizScreenState();
}

class _QuizScreenState extends ConsumerState<QuizScreen> {
  int? _attemptId;
  QuizModel? _emAndamento;
  final Map<int, List<int>> _respostas = {};
  QuizAttempt? _resultado;
  bool _carregando = false;
  String? _erro;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        title: Text(widget.courseTitle),
        backgroundColor: context.scaffoldBg,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: _corpo(),
          ),
        ),
      ),
    );
  }

  Widget _corpo() {
    if (_resultado != null) return _telaDeResultado(_resultado!);
    if (_emAndamento != null) return _telaDePerguntas(_emAndamento!);
    return _telaDeApresentacao();
  }

  // ── Apresentação ───────────────────────────────────────────────────────

  Widget _telaDeApresentacao() {
    final quizAsync = ref.watch(courseQuizProvider(widget.courseId));

    return quizAsync.when(
      loading: () => const AppSkeleton.card(height: 260),
      error: (_, __) => AppErrorState(
        message: 'Não foi possível carregar a avaliação.',
        onRetry: () => ref.invalidate(courseQuizProvider(widget.courseId)),
      ),
      data: (quiz) {
        if (quiz == null) {
          return const AppCard(
            child: Padding(
              padding: EdgeInsets.all(AppSpacing.lg),
              child: Text('Este treinamento não tem avaliação.'),
            ),
          );
        }

        return AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                quiz.title,
                style: context.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: context.textPrimaryColor,
                ),
              ),
              if (quiz.description.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.sm),
                Text(
                  quiz.description,
                  style: context.textTheme.bodyMedium?.copyWith(
                    color: context.textSecondaryColor,
                  ),
                ),
              ],
              const SizedBox(height: AppSpacing.xl),
              _regra(Icons.help_outline, '${quiz.questions.length} pergunta(s)'),
              _regra(
                Icons.check_circle_outline,
                'Nota mínima para aprovação: ${quiz.passingScore}%',
              ),
              _regra(
                Icons.replay,
                quiz.unlimited
                    ? 'Tentativas ilimitadas'
                    : 'Tentativas restantes: ${quiz.attemptsLeft ?? 0} de ${quiz.maxAttempts}',
              ),
              const SizedBox(height: AppSpacing.lg),

              if (quiz.alreadyPassed)
                _aviso(
                  Icons.verified_outlined,
                  'Você já foi aprovado nesta avaliação.',
                  AppColors.success,
                )
              else if (!quiz.unlimited && (quiz.attemptsLeft ?? 0) <= 0)
                _aviso(
                  Icons.block,
                  'Você esgotou as tentativas. Procure o RH.',
                  AppColors.error,
                )
              else ...[
                _aviso(
                  Icons.info_outline,
                  'A tentativa é contada assim que você começar — sair da tela não a devolve.',
                  AppColors.warning,
                ),
                const SizedBox(height: AppSpacing.lg),
                AppButton(
                  text: 'Iniciar avaliação',
                  icon: Icons.play_arrow,
                  isLoading: _carregando,
                  onPressed: _carregando ? null : _iniciar,
                ),
              ],

              if (_erro != null) ...[
                const SizedBox(height: AppSpacing.md),
                Text(
                  _erro!,
                  style: context.textTheme.bodySmall
                      ?.copyWith(color: AppColors.error),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  // ── Perguntas ──────────────────────────────────────────────────────────

  Widget _telaDePerguntas(QuizModel quiz) {
    final respondidas = _respostas.values.where((v) => v.isNotEmpty).length;
    final total = quiz.questions.length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppProgress(
          value: total == 0 ? 0 : respondidas / total,
          showLabel: true,
          labelText: '$respondidas de $total respondida(s)',
        ),
        const SizedBox(height: AppSpacing.xl),
        for (var i = 0; i < quiz.questions.length; i++) ...[
          _cartaoDePergunta(quiz.questions[i], i + 1),
          const SizedBox(height: AppSpacing.lg),
        ],
        if (_erro != null) ...[
          Text(
            _erro!,
            style: context.textTheme.bodySmall?.copyWith(color: AppColors.error),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        AppButton(
          text: 'Enviar respostas',
          icon: Icons.send,
          isLoading: _carregando,
          onPressed: _carregando ? null : () => _confirmarEnvio(quiz),
        ),
        const SizedBox(height: AppSpacing.xxl),
      ],
    );
  }

  Widget _cartaoDePergunta(QuizQuestion pergunta, int numero) {
    final marcadas = _respostas[pergunta.id] ?? const <int>[];

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$numero. ${pergunta.text}',
            style: context.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: context.textPrimaryColor,
            ),
          ),
          if (pergunta.allowsMultiple) ...[
            const SizedBox(height: 4),
            Text(
              'Marque todas que se aplicam.',
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textMutedColor,
              ),
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          for (final opcao in pergunta.options)
            pergunta.allowsMultiple
                ? CheckboxListTile(
                    value: marcadas.contains(opcao.id),
                    onChanged: (_) => _marcar(pergunta, opcao.id),
                    title: Text(opcao.text),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                  )
                : RadioListTile<int>(
                    value: opcao.id,
                    // ignore: deprecated_member_use
                    groupValue: marcadas.isEmpty ? null : marcadas.first,
                    // ignore: deprecated_member_use
                    onChanged: (_) => _marcar(pergunta, opcao.id),
                    title: Text(opcao.text),
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                  ),
        ],
      ),
    );
  }

  void _marcar(QuizQuestion pergunta, int opcaoId) {
    setState(() {
      final atuais = List<int>.from(_respostas[pergunta.id] ?? const []);
      if (pergunta.allowsMultiple) {
        atuais.contains(opcaoId)
            ? atuais.remove(opcaoId)
            : atuais.add(opcaoId);
        _respostas[pergunta.id] = atuais;
      } else {
        _respostas[pergunta.id] = [opcaoId];
      }
    });
  }

  // ── Resultado ──────────────────────────────────────────────────────────

  Widget _telaDeResultado(QuizAttempt resultado) {
    final aprovado = resultado.passed;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                aprovado ? Icons.verified : Icons.cancel_outlined,
                size: 32,
                color: aprovado ? AppColors.success : AppColors.error,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Text(
                  aprovado ? 'Aprovado!' : 'Não aprovado',
                  style: context.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: aprovado ? AppColors.success : AppColors.error,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(
            'Nota ${resultado.score}% · '
            '${resultado.correctCount} de ${resultado.questionCount} corretas · '
            'mínimo ${resultado.passingScore}%',
            style: context.textTheme.bodyMedium?.copyWith(
              color: context.textSecondaryColor,
            ),
          ),

          if (aprovado) ...[
            const SizedBox(height: AppSpacing.lg),
            _aviso(
              Icons.check_circle_outline,
              'Treinamento concluído.',
              AppColors.success,
            ),
          ],
          if (!aprovado) ...[
            const SizedBox(height: AppSpacing.lg),
            _aviso(
              Icons.replay,
              resultado.attemptsLeft == null
                  ? 'Você pode tentar novamente.'
                  : resultado.attemptsLeft! > 0
                      ? 'Você ainda tem ${resultado.attemptsLeft} tentativa(s).'
                      : 'Você esgotou as tentativas. Procure o RH.',
              AppColors.warning,
            ),
          ],

          const SizedBox(height: AppSpacing.xl),
          Text(
            'Desempenho por pergunta',
            style: context.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: context.textPrimaryColor,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          // Só acertou/errou: a resposta certa não aparece, senão esta tela
          // viraria o gabarito da próxima tentativa.
          for (final resposta in resultado.answers)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    resposta.isCorrect ? Icons.check : Icons.close,
                    size: 16,
                    color: resposta.isCorrect
                        ? AppColors.success
                        : AppColors.error,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      resposta.questionText,
                      style: context.textTheme.bodySmall?.copyWith(
                        color: context.textSecondaryColor,
                      ),
                    ),
                  ),
                ],
              ),
            ),

          const SizedBox(height: AppSpacing.xl),
          Row(
            children: [
              Expanded(
                child: AppButton(
                  text: 'Voltar ao treinamento',
                  variant: AppButtonVariant.secondary,
                  onPressed: () => Navigator.pop(context, aprovado),
                ),
              ),
              if (!aprovado && (resultado.attemptsLeft ?? 1) > 0) ...[
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: AppButton(
                    text: 'Tentar de novo',
                    onPressed: _reiniciar,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  // ── Ações ──────────────────────────────────────────────────────────────

  Future<void> _iniciar() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });
    try {
      final inicio = await ref
          .read(quizRepositoryProvider)
          .startAttempt(widget.courseId);
      setState(() {
        _attemptId = inicio.attemptId;
        _emAndamento = inicio.quiz;
        _respostas.clear();
      });
    } catch (erro) {
      setState(() => _erro = erro.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _carregando = false);
    }
  }

  /// Enviar é irreversível e gasta a tentativa — deixar em branco por
  /// engano custa caro, então a confirmação diz quantas faltam.
  Future<void> _confirmarEnvio(QuizModel quiz) async {
    final semResposta = quiz.questions
        .where((p) => (_respostas[p.id] ?? const []).isEmpty)
        .length;

    final confirmou = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Enviar respostas?'),
        content: Text(
          semResposta > 0
              ? '$semResposta pergunta(s) sem resposta serão contadas como erro. '
                  'Depois de enviar não dá para mudar.'
              : 'Depois de enviar não dá para mudar as respostas.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Revisar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Enviar'),
          ),
        ],
      ),
    );
    if (confirmou != true) return;
    await _enviar();
  }

  Future<void> _enviar() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });
    try {
      final resultado = await ref.read(quizRepositoryProvider).submit(
            widget.courseId,
            _attemptId!,
            _respostas,
          );
      setState(() {
        _resultado = resultado;
        _emAndamento = null;
      });
      ref.invalidate(courseQuizProvider(widget.courseId));
    } catch (erro) {
      setState(() => _erro = erro.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _carregando = false);
    }
  }

  void _reiniciar() {
    setState(() {
      _resultado = null;
      _emAndamento = null;
      _attemptId = null;
      _respostas.clear();
    });
    ref.invalidate(courseQuizProvider(widget.courseId));
  }

  // ── Auxiliares visuais ─────────────────────────────────────────────────

  Widget _regra(IconData icone, String texto) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        children: [
          Icon(icone, size: 16, color: context.textSecondaryColor),
          const SizedBox(width: AppSpacing.sm),
          Text(
            texto,
            style: context.textTheme.bodyMedium?.copyWith(
              color: context.textSecondaryColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _aviso(IconData icone, String texto, Color cor) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: cor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: cor.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Icon(icone, size: 18, color: cor),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              texto,
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textPrimaryColor,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
