import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:onboarding_app/app/theme.dart';
import 'package:onboarding_app/features/landing/presentation/landing_screen.dart';

/// A landing é a única tela que alguém de fora do sistema vê. Dois riscos
/// concretos: o botão de acesso não levar ao login (a pessoa não tem outro
/// caminho) e a página quebrar em telas estreitas.

GoRouter _router() {
  return GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => const LandingScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (_, __) => const Scaffold(
          body: Center(child: Text('TELA DE LOGIN')),
        ),
      ),
    ],
  );
}

Future<void> _montar(WidgetTester tester, {Size tamanho = const Size(1440, 1200)}) async {
  tester.view.physicalSize = tamanho;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    MaterialApp.router(
      theme: AppTheme.lightTheme,
      routerConfig: _router(),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  group('Landing', () {
    testWidgets('apresenta o sistema com a marca e a proposta', (tester) async {
      await _montar(tester);

      expect(find.text('Onboarding Corp'), findsWidgets);
      expect(find.text('Do primeiro dia ao primeiro resultado.'), findsOneWidget);
    });

    testWidgets('o botão de acesso fica encostado na borda direita',
        (tester) async {
      // Mede a POSIÇÃO, não a existência. Foi assim que passou despercebido
      // que o botão parava no meio da barra: ele estava lá, clicável e
      // levando ao login — só que no lugar errado.
      const largura = 1900.0;
      await _montar(tester, tamanho: const Size(largura, 1000));

      final botao = find.ancestor(
        of: find.text('Entrar'),
        matching: find.byType(GestureDetector),
      );
      final caixa = tester.getRect(botao.first);

      // O recuo lateral da página é 48 em telas largas; a folga aceita
      // cobre a sombra e o arredondamento do pill.
      expect(
        largura - caixa.right,
        lessThan(60),
        reason: 'o botão está a ${largura - caixa.right}px da borda direita',
      );

      // E a marca, encostada na esquerda. `.first` porque "Onboarding Corp"
      // aparece também no rodapé.
      final marca = tester.getRect(find.text('Onboarding Corp').first);
      expect(marca.left, lessThan(120));
    });

    testWidgets('o botão do canto superior direito leva ao login',
        (tester) async {
      await _montar(tester);

      // O primeiro "Entrar" é o do cabeçalho — o do canto superior direito.
      await tester.tap(find.text('Entrar').first);
      await tester.pumpAndSettle();

      expect(find.text('TELA DE LOGIN'), findsOneWidget);
    });

    testWidgets('o botão do hero também leva ao login', (tester) async {
      await _montar(tester);

      await tester.tap(find.text('Acessar o sistema'));
      await tester.pumpAndSettle();

      expect(find.text('TELA DE LOGIN'), findsOneWidget);
    });

    testWidgets('mostra os módulos do sistema', (tester) async {
      await _montar(tester);

      expect(find.text('Tarefas de integração'), findsOneWidget);
      expect(find.text('Treinamentos com avaliação'), findsOneWidget);
      expect(find.text('Automações'), findsOneWidget);
    });

    testWidgets('explica o que cada papel enxerga', (tester) async {
      await _montar(tester);

      expect(find.text('Colaborador'), findsOneWidget);
      expect(find.text('Gestor'), findsOneWidget);
      expect(find.text('RH e Administração'), findsOneWidget);
    });

    testWidgets('não estoura o layout em tela de celular', (tester) async {
      // 390x844 é um iPhone comum. Overflow aqui viraria a faixa amarela
      // atravessando a página — na primeira tela que alguém de fora vê.
      await _montar(tester, tamanho: const Size(390, 844));

      expect(tester.takeException(), isNull);
      expect(find.text('Entrar'), findsWidgets);
    });

    testWidgets('não estoura o layout em tablet', (tester) async {
      await _montar(tester, tamanho: const Size(834, 1112));

      expect(tester.takeException(), isNull);
    });

    testWidgets('o conteúdo do hero aparece por completo depois da entrada',
        (tester) async {
      await _montar(tester);

      // `pumpAndSettle` já esperou toda a animação escalonada. Se algum
      // bloco ficasse preso em opacidade 0, ele sumiria da página.
      expect(find.text('Do primeiro dia ao primeiro resultado.'), findsOneWidget);
      expect(find.text('80% concluído'), findsOneWidget);
      expect(find.text('3 tarefas pendentes'), findsOneWidget);
      expect(find.text('1 documento aguardando aceite'), findsOneWidget);
    });

    testWidgets('com movimento reduzido a página aparece pronta, sem animar',
        (tester) async {
      // Quem pediu movimento reduzido ao sistema não pode depender de uma
      // animação para ver o conteúdo — nem esperar por ela.
      tester.view.physicalSize = const Size(1440, 1200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: MaterialApp.router(
            theme: AppTheme.lightTheme,
            routerConfig: _router(),
          ),
        ),
      );
      // Um único frame, sem settle: o conteúdo já tem que estar visível.
      await tester.pump();

      final opacidades = tester
          .widgetList<Opacity>(find.byType(Opacity))
          .where((o) => o.opacity < 1);
      expect(opacidades, isEmpty,
          reason: 'nada pode estar meio transparente com movimento reduzido');
      expect(find.text('Do primeiro dia ao primeiro resultado.'), findsOneWidget);
    });

    testWidgets('as seções de baixo aparecem ao rolar', (tester) async {
      await _montar(tester);

      await tester.dragUntilVisible(
        find.text('Sua empresa já usa o Onboarding Corp?'),
        find.byType(SingleChildScrollView),
        const Offset(0, -400),
      );
      await tester.pumpAndSettle();

      expect(find.text('Sua empresa já usa o Onboarding Corp?'), findsOneWidget);
      expect(find.text('Como funciona'), findsOneWidget);
    });

    testWidgets('funciona no tema escuro', (tester) async {
      tester.view.physicalSize = const Size(1440, 1200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        MaterialApp.router(
          theme: AppTheme.darkTheme,
          routerConfig: _router(),
        ),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.text('Do primeiro dia ao primeiro resultado.'), findsOneWidget);
    });
  });
}
