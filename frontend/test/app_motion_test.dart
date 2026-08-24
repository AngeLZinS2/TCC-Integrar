import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:onboarding_app/core/widgets/app_motion.dart';

/// O vocabulário de movimento do app.
///
/// Duas coisas precisam ficar travadas aqui, e as duas são de acessibilidade
/// antes de serem de estética:
///
///  1. O conteúdo TEM que terminar visível. Uma animação que trava no meio
///     esconde a tela inteira — pior do que não ter animação nenhuma.
///  2. Com movimento reduzido, nada anima e nada espera. Quem marcou essa
///     preferência no sistema não pode depender de uma transição para ver
///     o que pediu.

Widget _app(Widget filho, {bool movimentoReduzido = false}) {
  return MaterialApp(
    home: MediaQuery(
      data: MediaQueryData(disableAnimations: movimentoReduzido),
      child: Scaffold(body: filho),
    ),
  );
}

/// Opacidade efetiva de um texto — o que decide se ele está visível.
double _opacidadeDe(WidgetTester tester, String texto) {
  final opacidades = tester.widgetList<Opacity>(
    find.ancestor(of: find.text(texto), matching: find.byType(Opacity)),
  );
  return opacidades.fold<double>(1, (acc, o) => acc * o.opacity);
}

void main() {
  group('AppFadeIn', () {
    testWidgets('termina totalmente visível', (tester) async {
      await tester.pumpWidget(_app(const AppFadeIn(child: Text('conteúdo'))));
      await tester.pumpAndSettle();

      expect(find.text('conteúdo'), findsOneWidget);
      expect(_opacidadeDe(tester, 'conteúdo'), 1.0);
    });

    testWidgets('começa transparente e não fica pelo caminho', (tester) async {
      await tester.pumpWidget(_app(const AppFadeIn(child: Text('conteúdo'))));
      await tester.pump(); // primeiro frame, animação recém iniciada

      expect(_opacidadeDe(tester, 'conteúdo'), lessThan(1.0));

      await tester.pumpAndSettle();
      expect(_opacidadeDe(tester, 'conteúdo'), 1.0);
    });

    testWidgets('com movimento reduzido já nasce visível', (tester) async {
      await tester.pumpWidget(
        _app(const AppFadeIn(child: Text('conteúdo')), movimentoReduzido: true),
      );
      await tester.pump();

      expect(_opacidadeDe(tester, 'conteúdo'), 1.0);
    });

    testWidgets('o atraso não impede o conteúdo de aparecer', (tester) async {
      await tester.pumpWidget(
        _app(
          const AppFadeIn(
            delay: Duration(milliseconds: 300),
            child: Text('atrasado'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(_opacidadeDe(tester, 'atrasado'), 1.0);
    });

    testWidgets('com movimento reduzido o atraso é ignorado', (tester) async {
      // Sem isto, quem pediu movimento reduzido esperaria a mesma fila de
      // atrasos — recebendo a tela em branco por um tempo, sem nem a
      // animação para explicar a espera.
      await tester.pumpWidget(
        _app(
          const AppFadeIn(
            delay: Duration(seconds: 2),
            child: Text('imediato'),
          ),
          movimentoReduzido: true,
        ),
      );
      await tester.pump();

      expect(_opacidadeDe(tester, 'imediato'), 1.0);
    });

    testWidgets('o escalonamento trava no décimo item', (tester) async {
      // Numa lista de cem, o centésimo esperaria três segundos para
      // aparecer — e ninguém rola até lá antes disso.
      expect(AppFadeIn.escalonar(0), Duration.zero);
      expect(AppFadeIn.escalonar(5), const Duration(milliseconds: 225));
      expect(AppFadeIn.escalonar(10), const Duration(milliseconds: 450));
      expect(AppFadeIn.escalonar(99), const Duration(milliseconds: 450));
    });

    testWidgets('uma lista escalonada aparece inteira', (tester) async {
      await tester.pumpWidget(
        _app(
          Column(
            children: [
              for (var i = 0; i < 12; i++)
                AppFadeIn(
                  delay: AppFadeIn.escalonar(i),
                  child: Text('item $i'),
                ),
            ],
          ),
        ),
      );
      await tester.pumpAndSettle();

      for (var i = 0; i < 12; i++) {
        expect(_opacidadeDe(tester, 'item $i'), 1.0,
            reason: 'o item $i ficou invisível');
      }
    });
  });

  group('whenAnimado', () {
    testWidgets('mostra o carregando e depois os dados', (tester) async {
      final controle = ValueNotifier<AsyncValue<String>>(
        const AsyncValue.loading(),
      );

      await tester.pumpWidget(
        _app(
          ValueListenableBuilder<AsyncValue<String>>(
            valueListenable: controle,
            builder: (context, valor, _) => valor.whenAnimado(
              context,
              loading: () => const Text('carregando'),
              error: (_, __) => const Text('deu erro'),
              data: (d) => Text(d),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('carregando'), findsOneWidget);

      controle.value = const AsyncValue.data('pronto');
      await tester.pumpAndSettle();

      expect(find.text('pronto'), findsOneWidget);
      // O antigo precisa SAIR: se o AnimatedSwitcher não descartasse o
      // estado anterior, o skeleton ficaria empilhado sob o conteúdo.
      expect(find.text('carregando'), findsNothing);
    });

    testWidgets('mostra o erro quando falha', (tester) async {
      await tester.pumpWidget(
        _app(
          Builder(
            builder: (context) =>
                const AsyncValue<String>.error('falhou', StackTrace.empty)
                    .whenAnimado(
              context,
              loading: () => const Text('carregando'),
              error: (e, _) => Text('erro: $e'),
              data: (d) => Text(d),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('erro: falhou'), findsOneWidget);
    });

    testWidgets('com movimento reduzido a troca é instantânea',
        (tester) async {
      final controle = ValueNotifier<AsyncValue<String>>(
        const AsyncValue.loading(),
      );

      await tester.pumpWidget(
        _app(
          ValueListenableBuilder<AsyncValue<String>>(
            valueListenable: controle,
            builder: (context, valor, _) => valor.whenAnimado(
              context,
              loading: () => const Text('carregando'),
              error: (_, __) => const Text('deu erro'),
              data: (d) => Text(d),
            ),
          ),
          movimentoReduzido: true,
        ),
      );
      await tester.pump();

      controle.value = const AsyncValue.data('pronto');
      await tester.pump();

      expect(find.text('pronto'), findsOneWidget);
    });
  });

  group('AppHoverLift', () {
    testWidgets('renderiza o filho sem depender do ponteiro', (tester) async {
      // No toque não há hover. O conteúdo não pode depender dele.
      await tester.pumpWidget(
        _app(const AppHoverLift(child: Text('cartão'))),
      );
      await tester.pumpAndSettle();

      expect(find.text('cartão'), findsOneWidget);
    });
  });
}
