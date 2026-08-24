import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Vocabulário de movimento do app.
///
/// Três regras guiam tudo aqui:
///
///  1. **O movimento explica, não enfeita.** Conteúdo entra de baixo porque
///     acabou de chegar; telas cruzam em fade porque uma substitui a outra;
///     um cartão sobe sob o ponteiro porque responde ao clique.
///  2. **Curto.** Nada passa de 400ms. Animação que a pessoa percebe como
///     espera virou obstáculo.
///  3. **Opcional.** Tudo respeita `MediaQuery.disableAnimations`. Quem
///     pediu movimento reduzido ao sistema — por enjoo, vertigem ou
///     sensibilidade vestibular — recebe a interface pronta, sem transição.

bool prefereMovimentoReduzido(BuildContext context) =>
    MediaQuery.of(context).disableAnimations;

/// Duração padrão, já zerada quando o sistema pede movimento reduzido.
Duration duracaoDe(BuildContext context, int ms) =>
    Duration(milliseconds: prefereMovimentoReduzido(context) ? 0 : ms);

// ── Entrada ─────────────────────────────────────────────────────────────────

/// Aparece subindo, uma vez, ao ser montado.
///
/// O `delay` escalona uma lista: cada item entra logo depois do anterior, o
/// que faz o olho percorrer a lista na ordem em vez de encarar tudo de uma
/// vez.
class AppFadeIn extends StatefulWidget {
  final Widget child;
  final Duration delay;
  final double deslocamento;

  const AppFadeIn({
    super.key,
    required this.child,
    this.delay = Duration.zero,
    this.deslocamento = 16,
  });

  /// Atraso escalonado por posição na lista.
  ///
  /// Trava no décimo item: numa lista de cem, o centésimo esperaria três
  /// segundos para aparecer — e ninguém rola até lá antes disso.
  static Duration escalonar(int indice, {int passoMs = 45}) =>
      Duration(milliseconds: passoMs * (indice.clamp(0, 10)));

  @override
  State<AppFadeIn> createState() => _AppFadeInState();
}

class _AppFadeInState extends State<AppFadeIn>
    with SingleTickerProviderStateMixin {
  static const _duracaoDoFade = 380;

  late final int _totalMs =
      widget.delay.inMilliseconds + _duracaoDoFade;

  late final AnimationController _controle = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: _totalMs),
  );

  /// O atraso vira um trecho MORTO no início da própria animação, em vez de
  /// um `Future.delayed`.
  ///
  /// A diferença importa: com timer, o conteúdo fica em opacidade 0 até o
  /// callback disparar — e se ele for descartado, o conteúdo não aparece
  /// nunca. Aqui existe uma única animação, sempre correndo até o fim.
  late final Animation<double> _progresso = CurvedAnimation(
    parent: _controle,
    curve: Interval(
      widget.delay.inMilliseconds / _totalMs,
      1,
      curve: Curves.easeOutCubic,
    ),
  );

  bool _iniciado = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_iniciado) return;
    _iniciado = true;

    if (prefereMovimentoReduzido(context)) {
      _controle.value = 1;
    } else {
      _controle.forward();
    }
  }

  @override
  void dispose() {
    _controle.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _progresso,
      builder: (context, filho) {
        final t = _progresso.value;
        return Opacity(
          opacity: t,
          child: Transform.translate(
            offset: Offset(0, widget.deslocamento * (1 - t)),
            child: filho,
          ),
        );
      },
      child: widget.child,
    );
  }
}

// ── Resposta ao ponteiro ────────────────────────────────────────────────────

/// Sobe de leve e ganha sombra sob o ponteiro.
///
/// Serve para dizer "isto responde ao seu mouse". No toque não há ponteiro,
/// então nada muda — e é por isso que nada aqui pode ser a única pista de
/// que o elemento é clicável.
class AppHoverLift extends StatefulWidget {
  final Widget child;
  final double elevacao;
  final BorderRadius? raio;
  final Color? corDaSombra;

  const AppHoverLift({
    super.key,
    required this.child,
    this.elevacao = 4,
    this.raio,
    this.corDaSombra,
  });

  @override
  State<AppHoverLift> createState() => _AppHoverLiftState();
}

class _AppHoverLiftState extends State<AppHoverLift> {
  bool _sobre = false;

  @override
  Widget build(BuildContext context) {
    final duracao = duracaoDe(context, 180);
    final ativo = _sobre && !prefereMovimentoReduzido(context);
    final cor = widget.corDaSombra ?? Theme.of(context).colorScheme.primary;

    return MouseRegion(
      onEnter: (_) => setState(() => _sobre = true),
      onExit: (_) => setState(() => _sobre = false),
      child: AnimatedContainer(
        duration: duracao,
        curve: Curves.easeOut,
        transform: Matrix4.translationValues(0, ativo ? -widget.elevacao : 0, 0),
        decoration: BoxDecoration(
          borderRadius: widget.raio ?? BorderRadius.circular(16),
          boxShadow: ativo
              ? [
                  BoxShadow(
                    color: cor.withValues(alpha: 0.16),
                    blurRadius: 20,
                    offset: const Offset(0, 8),
                  ),
                ]
              : const [],
        ),
        child: widget.child,
      ),
    );
  }
}

// ── Troca de estado ─────────────────────────────────────────────────────────

/// Renderiza um `AsyncValue` trocando os estados em fade.
///
/// Sem isto, o skeleton some e o conteúdo aparece no mesmo frame — um
/// salto que faz a tela parecer que piscou. O fade dá continuidade: a
/// pessoa entende que aquilo que estava carregando virou o conteúdo.
///
/// É uma extensão com a MESMA assinatura de `.when` de propósito: adotar
/// numa tela existente é trocar `.when(` por `.whenAnimado(context,` — sem
/// mexer em nenhum dos três blocos, que costumam ser longos e aninhados.
extension AsyncValueAnimado<T> on AsyncValue<T> {
  Widget whenAnimado(
    BuildContext context, {
    required Widget Function(T dados) data,
    required Widget Function() loading,
    required Widget Function(Object erro, StackTrace? pilha) error,
  }) {
    // A `ValueKey` por estado é o que faz o `AnimatedSwitcher` reconhecer a
    // troca; sem ela ele acha que é o mesmo widget e não anima nada.
    final conteudo = when(
      loading: () => KeyedSubtree(
        key: const ValueKey('carregando'),
        child: loading(),
      ),
      error: (erro, pilha) => KeyedSubtree(
        key: const ValueKey('erro'),
        child: error(erro, pilha),
      ),
      data: (dados) => KeyedSubtree(
        key: const ValueKey('dados'),
        child: data(dados),
      ),
    );

    return AnimatedSwitcher(
      duration: duracaoDe(context, 240),
      switchInCurve: Curves.easeOut,
      switchOutCurve: Curves.easeIn,
      // O padrão empilha os dois no centro e faz a altura pular quando um é
      // maior. Alinhado no topo, a troca acontece sem mexer no resto.
      layoutBuilder: (atual, anteriores) => Stack(
        alignment: Alignment.topLeft,
        children: [...anteriores, if (atual != null) atual],
      ),
      child: conteudo,
    );
  }
}

// ── Transição entre telas ───────────────────────────────────────────────────

/// Transição padrão de navegação: fade com um empurrãozinho para cima.
///
/// Substitui o corte seco do `NoTransitionPage`. É curta de propósito — a
/// navegação lateral do app é usada o tempo todo, e meio segundo de
/// transição a cada clique vira espera.
CustomTransitionPage<T> paginaComTransicao<T>({
  required LocalKey chave,
  required Widget filho,
}) {
  return CustomTransitionPage<T>(
    key: chave,
    child: filho,
    transitionDuration: const Duration(milliseconds: 220),
    reverseTransitionDuration: const Duration(milliseconds: 160),
    transitionsBuilder: (context, animation, secondary, child) {
      if (prefereMovimentoReduzido(context)) return child;

      final curva = CurvedAnimation(
        parent: animation,
        curve: Curves.easeOutCubic,
      );
      return FadeTransition(
        opacity: curva,
        child: SlideTransition(
          position: Tween(
            begin: const Offset(0, 0.012),
            end: Offset.zero,
          ).animate(curva),
          child: child,
        ),
      );
    },
  );
}
