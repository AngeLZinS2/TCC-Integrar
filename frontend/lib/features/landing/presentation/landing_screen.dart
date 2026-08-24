import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';

/// Página pública de apresentação do sistema.
///
/// É a primeira coisa que alguém de fora vê, então ela responde três
/// perguntas antes de qualquer botão: o que o sistema faz, para quem, e o
/// que a pessoa ganha usando. O acesso fica no canto superior direito —
/// onde quem já é usuário procura primeiro.
class LandingScreen extends StatelessWidget {
  const LandingScreen({super.key});

  static const _fundoEscuro = Color(0xFF0F172A);
  static const _fundoEscuroSuave = Color(0xFF1E293B);
  static const _textoSobreEscuro = Color(0xFF94A3B8);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: SingleChildScrollView(
        child: Column(
          children: [
            _Cabecalho(),
            const _Hero(),
            const _Modulos(),
            const _ComoFunciona(),
            const _ParaCadaPapel(),
            const _ChamadaFinal(),
            const _Rodape(),
          ],
        ),
      ),
    );
  }
}

// ── Cabeçalho com o botão de acesso ─────────────────────────────────────────

class _Cabecalho extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final estreito = MediaQuery.sizeOf(context).width < 720;

    return Container(
      color: LandingScreen._fundoEscuro,
      padding: EdgeInsets.symmetric(
        horizontal: estreito ? AppSpacing.xl : AppSpacing.huge,
        vertical: AppSpacing.xl,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1180),
          child: Row(
            children: [
              const Flexible(child: _Marca()),
              const Spacer(),
              Semantics(
                button: true,
                label: 'Entrar no sistema',
                child: ElevatedButton.icon(
                  onPressed: () => context.go('/login'),
                  icon: const Icon(Icons.login_rounded, size: 18),
                  label: const Text('Entrar'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    padding: EdgeInsets.symmetric(
                      horizontal: estreito ? AppSpacing.xl : AppSpacing.xxl,
                      vertical: AppSpacing.lg,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.md),
                    ),
                    textStyle: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
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
    final largura = MediaQuery.sizeOf(context).width;
    final estreito = largura < 900;

    return Container(
      width: double.infinity,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            LandingScreen._fundoEscuro,
            LandingScreen._fundoEscuroSuave,
          ],
        ),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: estreito ? AppSpacing.xl : AppSpacing.huge,
        vertical: estreito ? AppSpacing.huge : 72,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1180),
          child: estreito
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const _HeroTexto(),
                    const SizedBox(height: AppSpacing.huge),
                    _HeroPainel(),
                  ],
                )
              : Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    const Expanded(flex: 6, child: _HeroTexto()),
                    const SizedBox(width: AppSpacing.huge),
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

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
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
        const SizedBox(height: AppSpacing.xxl),
        Text(
          'Do primeiro dia ao primeiro resultado.',
          style: TextStyle(
            fontSize: estreito ? 34 : 48,
            fontWeight: FontWeight.w800,
            color: Colors.white,
            height: 1.15,
            letterSpacing: -1.4,
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
        const Text(
          'A plataforma que organiza a integração de novos colaboradores: '
          'tarefas com responsável e prazo, treinamentos com avaliação e '
          'certificado, documentos com aceite formal e comunicação '
          'direcionada — tudo num lugar só.',
          style: TextStyle(
            fontSize: 17,
            color: LandingScreen._textoSobreEscuro,
            height: 1.65,
          ),
        ),
        const SizedBox(height: AppSpacing.xxxl),
        Wrap(
          spacing: AppSpacing.lg,
          runSpacing: AppSpacing.md,
          children: [
            Semantics(
              button: true,
              label: 'Acessar o sistema',
              child: ElevatedButton.icon(
                onPressed: () => context.go('/login'),
                icon: const Icon(Icons.arrow_forward_rounded, size: 18),
                label: const Text('Acessar o sistema'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.xxxl,
                    vertical: AppSpacing.xl,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                  ),
                  textStyle: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xxl),
        const Text(
          'Acesso restrito a colaboradores cadastrados pela sua empresa.',
          style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
        ),
      ],
    );
  }
}

/// Uma prévia do painel real, montada com os mesmos números que a Home do
/// colaborador mostra. Vale mais do que uma imagem genérica de banco.
class _HeroPainel extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
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
              color: LandingScreen._textoSobreEscuro,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.pill),
            child: LinearProgressIndicator(
              value: 0.8,
              minHeight: 10,
              backgroundColor: Colors.white.withValues(alpha: 0.1),
              valueColor: const AlwaysStoppedAnimation(AppColors.success),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          const Text(
            '80% concluído',
            style: TextStyle(
              fontSize: 12,
              color: LandingScreen._textoSobreEscuro,
            ),
          ),
          const SizedBox(height: AppSpacing.xxl),
          const _LinhaPendencia(
            icone: Icons.checklist_rounded,
            texto: '3 tarefas pendentes',
          ),
          const _LinhaPendencia(
            icone: Icons.school_rounded,
            texto: '2 treinamentos a concluir',
          ),
          const _LinhaPendencia(
            icone: Icons.description_outlined,
            texto: '1 documento aguardando aceite',
          ),
        ],
      ),
    );
  }
}

class _LinhaPendencia extends StatelessWidget {
  final IconData icone;
  final String texto;

  const _LinhaPendencia({required this.icone, required this.texto});

  @override
  Widget build(BuildContext context) {
    return Padding(
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
              for (final (icone, titulo, descricao) in _itens)
                SizedBox(
                  width: constraints.maxWidth > 980
                      ? (constraints.maxWidth - AppSpacing.xxl * 2) / 3
                      : constraints.maxWidth > 620
                          ? (constraints.maxWidth - AppSpacing.xxl) / 2
                          : constraints.maxWidth,
                  child: _CartaoModulo(
                    icone: icone,
                    titulo: titulo,
                    descricao: descricao,
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
                for (final (numero, titulo, descricao) in _passos)
                  SizedBox(
                    width: colunas == 4
                        ? (constraints.maxWidth - AppSpacing.xxl * 3) / 4
                        : constraints.maxWidth,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          numero,
                          style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.w800,
                            color: AppColors.primary.withValues(alpha: 0.35),
                            letterSpacing: -1,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Text(
                          titulo,
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: context.textPrimaryColor,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.sm),
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
              for (final (icone, papel, itens) in _papeis)
                SizedBox(
                  width: largo
                      ? (constraints.maxWidth - AppSpacing.xxl * 2) / 3
                      : constraints.maxWidth,
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
                            Icon(icone, size: 20, color: AppColors.primary),
                            const SizedBox(width: AppSpacing.md),
                            // Expanded: "RH e Administração" em negrito
                            // estoura a largura do cartão sem ele.
                            Expanded(
                              child: Text(
                                papel,
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
                        for (final item in itens)
                          Padding(
                            padding:
                                const EdgeInsets.only(bottom: AppSpacing.md),
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

    return Container(
      width: double.infinity,
      margin: EdgeInsets.symmetric(
        horizontal: estreito ? AppSpacing.xl : AppSpacing.huge,
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
            LandingScreen._fundoEscuro,
            LandingScreen._fundoEscuroSuave,
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
              color: LandingScreen._textoSobreEscuro,
              height: 1.6,
            ),
          ),
          const SizedBox(height: AppSpacing.xxxl),
          Semantics(
            button: true,
            label: 'Entrar no sistema',
            child: ElevatedButton.icon(
              onPressed: () => context.go('/login'),
              icon: const Icon(Icons.login_rounded, size: 18),
              label: const Text('Entrar'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: LandingScreen._fundoEscuro,
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.huge,
                  vertical: AppSpacing.xl,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                textStyle: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Rodapé ──────────────────────────────────────────────────────────────────

class _Rodape extends StatelessWidget {
  const _Rodape();

  @override
  Widget build(BuildContext context) {
    final estreito = MediaQuery.sizeOf(context).width < 720;

    return Container(
      width: double.infinity,
      padding: EdgeInsets.symmetric(
        horizontal: estreito ? AppSpacing.xl : AppSpacing.huge,
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
        horizontal: estreito ? AppSpacing.xl : AppSpacing.huge,
        vertical: estreito ? AppSpacing.huge : 72,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1180),
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
              SizedBox(height: estreito ? AppSpacing.xxxl : AppSpacing.huge),
              child,
            ],
          ),
        ),
      ),
    );
  }
}
