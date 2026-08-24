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
