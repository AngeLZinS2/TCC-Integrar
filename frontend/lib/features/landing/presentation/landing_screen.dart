import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import 'widgets/landing_animations.dart';

/// Página pública de apresentação do sistema.
///
/// É a primeira coisa que alguém de fora vê, então ela responde três
/// perguntas antes de qualquer botão: o que o sistema faz, para quem, e o
/// que a pessoa ganha usando. O acesso fica no canto superior direito —
/// onde quem já é usuário procura primeiro.
///
/// As animações servem à leitura: o conteúdo aparece na ordem em que deve
/// ser lido e responde ao ponteiro para indicar o que é clicável. Nada se
/// move sozinho depois de posicionado, e quem pediu movimento reduzido ao
/// sistema recebe a página estática (ver `landing_animations.dart`).
class LandingScreen extends StatefulWidget {
  const LandingScreen({super.key});

  static const fundoEscuro = Color(0xFF0F172A);
  static const fundoEscuroSuave = Color(0xFF1E293B);
  static const textoSobreEscuro = Color(0xFF94A3B8);

  @override
  State<LandingScreen> createState() => _LandingScreenState();
}

class _LandingScreenState extends State<LandingScreen> {
  /// Offset da rolagem, distribuído para os blocos que revelam ao aparecer.
  final _rolagem = ValueNotifier<double>(0);

  @override
  void dispose() {
    _rolagem.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: ScrollScope(
        offset: _rolagem,
        child: NotificationListener<ScrollNotification>(
          onNotification: (aviso) {
            if (aviso.metrics.axis == Axis.vertical) {
              _rolagem.value = aviso.metrics.pixels;
            }
            return false;
          },
          child: const SingleChildScrollView(
            child: Column(
              children: [
                _Cabecalho(),
                _Hero(),
                _Modulos(),
                _ComoFunciona(),
                _ParaCadaPapel(),
                _ChamadaFinal(),
                _Rodape(),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Recuo lateral da página.
///
/// O cabeçalho usa este recuo direto na borda da janela — sem o container
/// centralizado de 1180px que as seções usam. É o que leva a marca e o
/// botão de acesso para os cantos de verdade, onde o olho procura.
double _recuoLateral(BuildContext context) {
  final largura = MediaQuery.sizeOf(context).width;
  if (largura < 600) return AppSpacing.xl;
  if (largura < 1100) return AppSpacing.xxxl;
  return AppSpacing.huge;
}

// ── Cabeçalho com o botão de acesso ─────────────────────────────────────────

class _Cabecalho extends StatelessWidget {
  const _Cabecalho();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: LandingScreen.fundoEscuro,
      padding: EdgeInsets.symmetric(
        horizontal: _recuoLateral(context),
        vertical: AppSpacing.lg,
      ),
      // Sem `ConstrainedBox`: aqui a barra ocupa a largura inteira, para a
      // marca encostar na esquerda e o "Entrar" na direita.
      //
      // `spaceBetween` e nao `Spacer`: com um `Flexible` na marca, o
      // `Spacer` fica com METADE do espaco livre e o resto sobra no fim da
      // linha — o botao parava no meio da barra em telas largas.
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Flexible(child: EntradaEscalonada(child: _Marca())),
          EntradaEscalonada(
            delay: const Duration(milliseconds: 90),
            child: BotaoAcesso(
              rotulo: 'Entrar',
              icone: Icons.arrow_forward_rounded,
              onPressed: () => context.go('/login'),
            ),
          ),
        ],
      ),
    );
  }
}

class _Marca extends StatelessWidget {
  const _Marca();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: AppColors.primary,
            borderRadius: BorderRadius.circular(AppRadius.md),
            boxShadow: AppShadows.primaryGlow,
          ),
          child: const Icon(
            Icons.rocket_launch_rounded,
            color: Colors.white,
            size: 22,
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        // O nome cede espaço antes do botão de acesso: numa tela estreita,
        // é melhor o título truncar do que o "Entrar" ser espremido.
        const Flexible(
          child: Text(
            'Onboarding Corp',
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: Colors.white,
              letterSpacing: -0.4,
            ),
          ),
        ),
      ],
    );
  }
}

// ── Hero ────────────────────────────────────────────────────────────────────

class _Hero extends StatelessWidget {
  const _Hero();

  @override
  Widget build(BuildContext context) {
    final estreito = MediaQuery.sizeOf(context).width < 900;

    return Container(
      width: double.infinity,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            LandingScreen.fundoEscuro,
            LandingScreen.fundoEscuroSuave,
          ],
        ),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: _recuoLateral(context),
        vertical: estreito ? AppSpacing.huge : 72,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1180),
          child: estreito
              ? const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _HeroTexto(),
                    SizedBox(height: AppSpacing.huge),
                    _HeroPainel(),
                  ],
                )
              : const Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(flex: 6, child: _HeroTexto()),
                    SizedBox(width: AppSpacing.huge),
                    Expanded(flex: 5, child: _HeroPainel()),
                  ],
                ),
        ),
      ),
    );
  }
}

class _HeroTexto extends StatelessWidget {
  const _HeroTexto();

  @override
  Widget build(BuildContext context) {
    final estreito = MediaQuery.sizeOf(context).width < 900;

    // Escalonamento na ordem de leitura: selo, título, texto, botão.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        EntradaEscalonada(
          delay: const Duration(milliseconds: 120),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.sm,
            ),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(AppRadius.pill),
              border: Border.all(
                color: AppColors.primary.withValues(alpha: 0.3),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.auto_awesome,
                  size: 14,
                  color: AppColors.primary300,
                ),
                const SizedBox(width: AppSpacing.sm),
                // Rótulo mais curto no celular, e `Flexible` como rede: com
                // o texto ampliado por acessibilidade a versão longa estoura
                // a linha, e listras de overflow na primeira tela que alguém
                // de fora vê custam mais do que uma palavra a menos.
                Flexible(
                  child: Text(
                    estreito
                        ? 'Employee Experience'
                        : 'Integração e Employee Experience',
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppColors.primary300,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        EntradaEscalonada(
          delay: const Duration(milliseconds: 200),
          child: Text(
            'Do primeiro dia ao primeiro resultado.',
            style: TextStyle(
              fontSize: estreito ? 34 : 48,
              fontWeight: FontWeight.w800,
              color: Colors.white,
              height: 1.15,
              letterSpacing: -1.4,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
        const EntradaEscalonada(
          delay: Duration(milliseconds: 300),
          child: Text(
            'A plataforma que organiza a integração de novos colaboradores: '
            'tarefas com responsável e prazo, treinamentos com avaliação e '
            'certificado, documentos com aceite formal e comunicação '
            'direcionada — tudo num lugar só.',
            style: TextStyle(
              fontSize: 17,
              color: LandingScreen.textoSobreEscuro,
              height: 1.65,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.xxxl),
        EntradaEscalonada(
          delay: const Duration(milliseconds: 400),
          child: BotaoAcesso(
            // No celular o rótulo curto cabe inteiro; a frase completa fica
            // para telas em que ela não precisa ser cortada.
            rotulo: estreito ? 'Acessar' : 'Acessar o sistema',
            icone: Icons.arrow_forward_rounded,
            grande: true,
            onPressed: () => context.go('/login'),
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        const EntradaEscalonada(
          delay: Duration(milliseconds: 480),
          child: Text(
            'Acesso restrito a colaboradores cadastrados pela sua empresa.',
            style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
          ),
        ),
      ],
    );
  }
}

/// Uma prévia do painel real, montada com os mesmos números que a Home do
/// colaborador mostra. Vale mais do que uma imagem genérica de banco.
class _HeroPainel extends StatelessWidget {
  const _HeroPainel();

  @override
  Widget build(BuildContext context) {
    final reduzido = MediaQuery.of(context).disableAnimations;

    return EntradaEscalonada(
      delay: const Duration(milliseconds: 260),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(AppRadius.xl),
          border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Bom dia, Marina 👋',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: AppSpacing.xxl),
            const Text(
              'Sua integração',
              style: TextStyle(
                fontSize: 13,
                color: LandingScreen.textoSobreEscuro,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            // A barra preenche até 80% ao carregar: mostra que o progresso é
            // algo que ANDA, que é justamente o que o produto faz.
            TweenAnimationBuilder<double>(
              tween: Tween(begin: reduzido ? 0.8 : 0, end: 0.8),
              duration: Duration(milliseconds: reduzido ? 0 : 1100),
              curve: Curves.easeOutCubic,
              builder: (context, valor, _) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(AppRadius.pill),
                      child: LinearProgressIndicator(
                        value: valor,
                        minHeight: 10,
                        backgroundColor: Colors.white.withValues(alpha: 0.1),
                        valueColor: const AlwaysStoppedAnimation(
                          AppColors.success,
                        ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      '${(valor * 100).round()}% concluído',
                      style: const TextStyle(
                        fontSize: 12,
                        color: LandingScreen.textoSobreEscuro,
                      ),
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: AppSpacing.xxl),
            const _LinhaPendencia(
              icone: Icons.checklist_rounded,
              texto: '3 tarefas pendentes',
              delay: Duration(milliseconds: 620),
            ),
            const _LinhaPendencia(
              icone: Icons.school_rounded,
              texto: '2 treinamentos a concluir',
              delay: Duration(milliseconds: 720),
            ),
            const _LinhaPendencia(
              icone: Icons.description_outlined,
              texto: '1 documento aguardando aceite',
              delay: Duration(milliseconds: 820),
            ),
          ],
        ),
      ),
    );
  }
}

class _LinhaPendencia extends StatelessWidget {
  final IconData icone;
  final String texto;
  final Duration delay;

  const _LinhaPendencia({
    required this.icone,
    required this.texto,
    required this.delay,
  });

  @override
  Widget build(BuildContext context) {
    return EntradaEscalonada(
      delay: delay,
      child: Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.md),
        child: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: Icon(icone, size: 16, color: AppColors.primary300),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Text(
                texto,
                style: const TextStyle(fontSize: 14, color: Colors.white),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Módulos ─────────────────────────────────────────────────────────────────

class _Modulos extends StatelessWidget {
  const _Modulos();

  static const _itens = [
    (
      Icons.checklist_rounded,
      'Tarefas de integração',
      'Cada etapa com responsável e prazo. "Criar acessos" é do RH, "apresentar a equipe" é do gestor, "enviar documentos" é do colaborador — e o atraso de cada uma tem dono.',
    ),
    (
      Icons.school_rounded,
      'Treinamentos com avaliação',
      'Trilhas por setor e cargo, com quiz e nota mínima. Treinamento de compliance só fecha com aprovação — e gera certificado com código verificável.',
    ),
    (
      Icons.folder_shared_outlined,
      'Documentos com aceite',
      'Biblioteca versionada com registro de "li e estou de acordo". Publicar uma versão nova reabre a exigência para todo mundo.',
    ),
    (
      Icons.campaign_outlined,
      'Comunicados e eventos',
      'Segmentação por setor, cargo e unidade que afunila em vez de somar: "TI + Unidade Centro" alcança o TI da Centro, e mais ninguém.',
    ),
    (
      Icons.forum_outlined,
      'Solicitações de RH',
      'Chamados com número, prazo por prioridade, histórico e anexos. O colaborador acompanha; o RH não perde nada no e-mail.',
    ),
    (
      Icons.bolt_outlined,
      'Automações',
      'Regras que rodam sozinhas: admitiu um desenvolvedor júnior, o treinamento de segurança é atribuído e o gestor é avisado.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return _Secao(
      titulo: 'Tudo que a integração precisa',
      subtitulo:
          'Seis módulos que conversam entre si — o que acontece num aparece no outro.',
      child: LayoutBuilder(
        builder: (context, constraints) {
          return Wrap(
            spacing: AppSpacing.xxl,
            runSpacing: AppSpacing.xxl,
            children: [
              for (final (indice, item) in _itens.indexed)
                SizedBox(
                  width: constraints.maxWidth > 980
                      ? (constraints.maxWidth - AppSpacing.xxl * 2) / 3
                      : constraints.maxWidth > 620
                          ? (constraints.maxWidth - AppSpacing.xxl) / 2
                          : constraints.maxWidth,
                  child: RevealOnScroll(
                    // O atraso segue a leitura da grade, e reinicia a cada
                    // linha para a última não demorar demais.
                    delay: Duration(milliseconds: 70 * (indice % 3)),
                    child: _CartaoModulo(
                      icone: item.$1,
                      titulo: item.$2,
                      descricao: item.$3,
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _CartaoModulo extends StatelessWidget {
  final IconData icone;
  final String titulo;
  final String descricao;

  const _CartaoModulo({
    required this.icone,
    required this.titulo,
    required this.descricao,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$titulo. $descricao',
      child: ElevarNoHover(
        child: Container(
          padding: const EdgeInsets.all(AppSpacing.xxl),
          decoration: BoxDecoration(
            color: context.cardColor,
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border: Border.all(color: context.borderColor),
            boxShadow: AppShadows.sm,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Icon(icone, size: 22, color: AppColors.primary),
              ),
              const SizedBox(height: AppSpacing.xl),
              Text(
                titulo,
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: context.textPrimaryColor,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Text(
                descricao,
                style: TextStyle(
                  fontSize: 14,
                  color: context.textSecondaryColor,
                  height: 1.6,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Como funciona ───────────────────────────────────────────────────────────

class _ComoFunciona extends StatelessWidget {
  const _ComoFunciona();

  // Os passos são numerados porque a ordem importa de verdade: cada um só
  // acontece depois do anterior. Não é decoração.
  static const _passos = [
    (
      '01',
      'O RH cadastra o colaborador',
      'Setor, cargo, unidade e data de admissão. Uma tela só.',
    ),
    (
      '02',
      'O plano de integração nasce sozinho',
      'O roteiro do cargo vira tarefas com datas reais, e cada uma já sai com responsável definido.',
    ),
    (
      '03',
      'Cada um recebe o que lhe cabe',
      'Colaborador, gestor e RH são avisados no app e por e-mail — só do que é deles.',
    ),
    (
      '04',
      'O acompanhamento é em tempo real',
      'Painéis mostram o que está em dia, o que atrasou e de quem é a pendência.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: context.subtleBg,
      child: _Secao(
        titulo: 'Como funciona',
        subtitulo:
            'Da admissão ao acompanhamento, sem planilha paralela no meio.',
        child: LayoutBuilder(
          builder: (context, constraints) {
            final colunas = constraints.maxWidth > 980 ? 4 : 1;
            return Wrap(
              spacing: AppSpacing.xxl,
              runSpacing: AppSpacing.xxl,
              children: [
                for (final (indice, passo) in _passos.indexed)
                  SizedBox(
                    width: colunas == 4
                        ? (constraints.maxWidth - AppSpacing.xxl * 3) / 4
                        : constraints.maxWidth,
                    child: RevealOnScroll(
                      // Escalonamento maior de propósito: os passos aparecem
                      // na ordem, e a ordem é a informação.
                      delay: Duration(milliseconds: 110 * indice),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            passo.$1,
                            style: TextStyle(
                              fontSize: 32,
                              fontWeight: FontWeight.w800,
                              color: AppColors.primary.withValues(alpha: 0.35),
                              letterSpacing: -1,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.md),
                          Text(
                            passo.$2,
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                              color: context.textPrimaryColor,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          Text(
                            passo.$3,
                            style: TextStyle(
                              fontSize: 14,
                              color: context.textSecondaryColor,
                              height: 1.6,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

// ── Para cada papel ─────────────────────────────────────────────────────────

class _ParaCadaPapel extends StatelessWidget {
  const _ParaCadaPapel();

  static const _papeis = [
    (
      Icons.person_outline_rounded,
      'Colaborador',
      [
        'Vê o que precisa fazer, e só isso',
        'Treinamentos, documentos e certificados',
        'Abre solicitações e acompanha o andamento',
      ],
    ),
    (
      Icons.groups_2_outlined,
      'Gestor',
      [
        'Acompanha a integração da própria equipe',
        'Recebe as tarefas que são dele',
        'Cadastra treinamentos do seu setor',
      ],
    ),
    (
      Icons.badge_outlined,
      'RH e Administração',
      [
        'Painéis de toda a empresa',
        'Roteiros de integração reaproveitáveis',
        'Automações, unidades e auditoria',
      ],
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return _Secao(
      titulo: 'Cada pessoa vê o que é dela',
      subtitulo:
          'O acesso é definido por papel — e a regra vale no servidor, não só na tela.',
      child: LayoutBuilder(
        builder: (context, constraints) {
          final largo = constraints.maxWidth > 900;
          return Wrap(
            spacing: AppSpacing.xxl,
            runSpacing: AppSpacing.xxl,
            children: [
              for (final (indice, papel) in _papeis.indexed)
                SizedBox(
                  width: largo
                      ? (constraints.maxWidth - AppSpacing.xxl * 2) / 3
                      : constraints.maxWidth,
                  child: RevealOnScroll(
                    delay: Duration(milliseconds: 90 * indice),
                    child: ElevarNoHover(
                      elevacao: 4,
                      child: Container(
                        padding: const EdgeInsets.all(AppSpacing.xxl),
                        decoration: BoxDecoration(
                          color: context.cardColor,
                          borderRadius: BorderRadius.circular(AppRadius.lg),
                          border: Border.all(color: context.borderColor),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  papel.$1,
                                  size: 20,
                                  color: AppColors.primary,
                                ),
                                const SizedBox(width: AppSpacing.md),
                                // Expanded: "RH e Administração" em negrito
                                // estoura a largura do cartão sem ele.
                                Expanded(
                                  child: Text(
                                    papel.$2,
                                    style: TextStyle(
                                      fontSize: 17,
                                      fontWeight: FontWeight.w700,
                                      color: context.textPrimaryColor,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: AppSpacing.xl),
                            for (final item in papel.$3)
                              Padding(
                                padding: const EdgeInsets.only(
                                  bottom: AppSpacing.md,
                                ),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Icon(
                                      Icons.check_rounded,
                                      size: 16,
                                      color: AppColors.success,
                                    ),
                                    const SizedBox(width: AppSpacing.sm),
                                    Expanded(
                                      child: Text(
                                        item,
                                        style: TextStyle(
                                          fontSize: 14,
                                          color: context.textSecondaryColor,
                                          height: 1.5,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

// ── Chamada final ───────────────────────────────────────────────────────────

class _ChamadaFinal extends StatelessWidget {
  const _ChamadaFinal();

  @override
  Widget build(BuildContext context) {
    final estreito = MediaQuery.sizeOf(context).width < 720;

    return RevealOnScroll(
      child: Container(
        width: double.infinity,
        margin: EdgeInsets.symmetric(
          horizontal: _recuoLateral(context),
          vertical: AppSpacing.huge,
        ),
        padding: EdgeInsets.symmetric(
          horizontal: estreito ? AppSpacing.xxl : AppSpacing.huge,
          vertical: AppSpacing.huge,
        ),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              LandingScreen.fundoEscuro,
              LandingScreen.fundoEscuroSuave,
            ],
          ),
          borderRadius: BorderRadius.circular(AppRadius.xl),
        ),
        child: Column(
          children: [
            Text(
              'Sua empresa já usa o Onboarding Corp?',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: estreito ? 24 : 30,
                fontWeight: FontWeight.w800,
                color: Colors.white,
                letterSpacing: -0.8,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            const Text(
              'Entre com o e-mail cadastrado pelo seu RH e continue de onde parou.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 16,
                color: LandingScreen.textoSobreEscuro,
                height: 1.6,
              ),
            ),
            const SizedBox(height: AppSpacing.xxxl),
            BotaoAcesso(
              rotulo: 'Entrar',
              icone: Icons.arrow_forward_rounded,
              claro: true,
              grande: true,
              onPressed: () => context.go('/login'),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Rodapé ──────────────────────────────────────────────────────────────────

class _Rodape extends StatelessWidget {
  const _Rodape();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.symmetric(
        horizontal: _recuoLateral(context),
        vertical: AppSpacing.xxxl,
      ),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: context.borderColor)),
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1180),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    Icons.rocket_launch_rounded,
                    size: 18,
                    color: AppColors.primary,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Text(
                    'Onboarding Corp',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: context.textPrimaryColor,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              Text(
                'Plataforma de integração e capacitação de colaboradores.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 13,
                  color: context.textMutedColor,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Estrutura comum das seções ──────────────────────────────────────────────

class _Secao extends StatelessWidget {
  final String titulo;
  final String subtitulo;
  final Widget child;

  const _Secao({
    required this.titulo,
    required this.subtitulo,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final estreito = MediaQuery.sizeOf(context).width < 720;

    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: _recuoLateral(context),
        vertical: estreito ? AppSpacing.huge : 72,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1180),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              RevealOnScroll(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      titulo,
                      style: TextStyle(
                        fontSize: estreito ? 26 : 34,
                        fontWeight: FontWeight.w800,
                        color: context.textPrimaryColor,
                        letterSpacing: -1,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      subtitulo,
                      style: TextStyle(
                        fontSize: 16,
                        color: context.textSecondaryColor,
                        height: 1.6,
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: estreito ? AppSpacing.xxxl : AppSpacing.huge),
              child,
            ],
          ),
        ),
      ),
    );
  }
}
