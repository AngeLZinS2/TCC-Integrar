import 'package:flutter/material.dart';

import '../../../../app/theme.dart';
import '../../../../core/widgets/app_motion.dart';

/// Peças de animação da landing.
///
/// Tudo aqui respeita `MediaQuery.disableAnimations`: quem pediu ao sistema
/// para reduzir movimento (enjoo, vertigem, sensibilidade vestibular) recebe
/// a página inteira, já posicionada, sem transição nenhuma. Animação que
/// ignora essa preferência não é charme — é barreira.

// `prefereMovimentoReduzido` e `duracaoDe` vêm de `app_motion.dart`: o
// vocabulário de movimento é um só no app inteiro.

/// Distribui o offset da rolagem para os widgets que revelam ao entrar em
/// tela.
///
/// Um `ValueNotifier` em vez de reconstruir a árvore a cada pixel: só quem
/// ainda não apareceu escuta, e cada um para de escutar assim que aparece.
class ScrollScope extends InheritedWidget {
  final ValueNotifier<double> offset;

  const ScrollScope({
    super.key,
    required this.offset,
    required super.child,
  });

  static ValueNotifier<double>? of(BuildContext context) {
    return context
        .dependOnInheritedWidgetOfExactType<ScrollScope>()
        ?.offset;
  }

  @override
  bool updateShouldNotify(ScrollScope oldWidget) => offset != oldWidget.offset;
}

/// Revela o conteúdo quando ele entra na área visível.
///
/// Sobe um pouco e aparece — o suficiente para o olho seguir a leitura,
/// sem virar espetáculo. Acontece UMA vez: reanimar a cada rolagem para
/// cima e para baixo cansa e atrapalha quem só quer reler um trecho.
class RevealOnScroll extends StatefulWidget {
  final Widget child;
  final Duration delay;
  final double deslocamento;

  const RevealOnScroll({
    super.key,
    required this.child,
    this.delay = Duration.zero,
    this.deslocamento = 28,
  });

  @override
  State<RevealOnScroll> createState() => _RevealOnScrollState();
}

class _RevealOnScrollState extends State<RevealOnScroll>
    with SingleTickerProviderStateMixin {
  late final int _totalMs = widget.delay.inMilliseconds + 520;

  late final AnimationController _controle = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: _totalMs),
  );

  /// O atraso é um trecho morto no início da própria animação, e não um
  /// `Future.delayed`: um timer descartado deixaria o bloco invisível para
  /// sempre.
  late final Animation<double> _progresso = CurvedAnimation(
    parent: _controle,
    curve: Interval(
      widget.delay.inMilliseconds / _totalMs,
      1,
      curve: Curves.easeOutCubic,
    ),
  );
  final _chave = GlobalKey();
  ValueNotifier<double>? _rolagem;
  bool _revelado = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _conferir());
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (prefereMovimentoReduzido(context)) {
      _revelado = true;
      _controle.value = 1;
      return;
    }
    final nova = ScrollScope.of(context);
    if (nova != _rolagem) {
      _rolagem?.removeListener(_conferir);
      _rolagem = nova;
      _rolagem?.addListener(_conferir);
    }
  }

  void _conferir() {
    if (_revelado || !mounted) return;

    final render = _chave.currentContext?.findRenderObject();
    if (render is! RenderBox || !render.hasSize) return;

    final topo = render.localToGlobal(Offset.zero).dy;
    final alturaDaTela = MediaQuery.sizeOf(context).height;

    // 88% da altura: dispara um pouco ANTES de o bloco estar totalmente
    // visível, senão a animação começa quando a pessoa já está lendo.
    if (topo < alturaDaTela * 0.88) {
      _revelado = true;
      _rolagem?.removeListener(_conferir);
      _controle.forward();
    }
  }

  @override
  void dispose() {
    _rolagem?.removeListener(_conferir);
    _controle.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      key: _chave,
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

/// O botão de acesso.
///
/// É o único caminho de entrada da página, então ele responde ao ponteiro
/// de forma inequívoca: acende, cresce um fio e o ícone avança.
class BotaoAcesso extends StatefulWidget {
  final String rotulo;
  final IconData icone;
  final VoidCallback onPressed;
  final bool claro;
  final bool grande;

  const BotaoAcesso({
    super.key,
    required this.rotulo,
    required this.icone,
    required this.onPressed,
    this.claro = false,
    this.grande = false,
  });

  @override
  State<BotaoAcesso> createState() => _BotaoAcessoState();
}

class _BotaoAcessoState extends State<BotaoAcesso> {
  bool _sobre = false;

  @override
  Widget build(BuildContext context) {
    final reduzido = prefereMovimentoReduzido(context);
    final duracao = Duration(milliseconds: reduzido ? 0 : 180);
    final ativo = _sobre && !reduzido;

    final corFundo = widget.claro ? Colors.white : AppColors.primary;
    final corTexto = widget.claro ? const Color(0xFF0F172A) : Colors.white;

    return Semantics(
      button: true,
      label: widget.rotulo,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _sobre = true),
        onExit: (_) => setState(() => _sobre = false),
        child: GestureDetector(
          onTap: widget.onPressed,
          child: AnimatedScale(
            scale: ativo ? 1.03 : 1.0,
            duration: duracao,
            curve: Curves.easeOut,
            child: AnimatedContainer(
              duration: duracao,
              padding: EdgeInsets.symmetric(
                horizontal: widget.grande ? AppSpacing.xxxl : AppSpacing.xxl,
                vertical: widget.grande ? AppSpacing.xl : AppSpacing.lg,
              ),
              decoration: BoxDecoration(
                color: corFundo,
                borderRadius: BorderRadius.circular(AppRadius.pill),
                boxShadow: [
                  BoxShadow(
                    color: (widget.claro ? Colors.black : AppColors.primary)
                        .withValues(alpha: ativo ? 0.45 : 0.28),
                    blurRadius: ativo ? 26 : 14,
                    offset: Offset(0, ativo ? 10 : 5),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // `Flexible` como rede: num celular estreito, ou com o
                  // texto ampliado por acessibilidade, o rótulo longo
                  // estoura a linha do botão. Encolher é melhor do que as
                  // listras de overflow sobre o único caminho de entrada.
                  Flexible(
                    child: Text(
                      widget.rotulo,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: widget.grande ? 16 : 15,
                        fontWeight: FontWeight.w700,
                        color: corTexto,
                        letterSpacing: -0.2,
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  // O ícone avança no hover: reforça "isto leva para outro
                  // lugar" sem precisar de mais texto.
                  AnimatedSlide(
                    offset: Offset(ativo ? 0.22 : 0, 0),
                    duration: duracao,
                    curve: Curves.easeOut,
                    child: Icon(widget.icone, size: 18, color: corTexto),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
