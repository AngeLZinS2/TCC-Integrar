import 'dart:math' as math;

import 'package:flutter/material.dart';
import '../../../../app/theme.dart';

/// Pequena animação sobreposta à própria tela de login: o quadrado da marca
/// (mesmo visual do logo do foguete exibido no login) "liga" os propulsores
/// e decola, antes de liberar a navegação para o app via [onComplete].
class LaunchBadgeOverlay extends StatefulWidget {
  final VoidCallback onComplete;

  const LaunchBadgeOverlay({super.key, required this.onComplete});

  @override
  State<LaunchBadgeOverlay> createState() => _LaunchBadgeOverlayState();
}

class _LaunchBadgeOverlayState extends State<LaunchBadgeOverlay>
    with SingleTickerProviderStateMixin {
  static const _duration = Duration(milliseconds: 2800);

  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: _duration)
      ..addStatusListener((status) {
        if (status == AnimationStatus.completed && mounted) {
          widget.onComplete();
        }
      })
      ..forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  static double _phase(double t, double start, double end) {
    if (t <= start) return 0.0;
    if (t >= end) return 1.0;
    return (t - start) / (end - start);
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final t = _controller.value;

        // Timeline (2.8s total): appear → hold/charge → ignite → launch → fade.
        final appearP = Curves.easeOutCubic.transform(_phase(t, 0.0, 0.12));
        final idleP = _phase(t, 0.12, 0.34);
        final igniteP = _phase(t, 0.34, 0.56);
        final flyP = Curves.easeInCubic.transform(_phase(t, 0.58, 0.96));
        final fadeOutP = _phase(t, 0.88, 1.0);
        final flashP = t < 0.45 ? _phase(t, 0.34, 0.45) : (1 - _phase(t, 0.45, 0.56));

        final bob = math.sin(idleP * math.pi * 2) * 5 * (1 - igniteP);
        final shake = math.sin(igniteP * math.pi * 6) * (1 - igniteP) * 0.07;
        final scale = _lerp(0.5, 1.0, appearP) * _lerp(1.0, 1.6, flyP);
        final translateY = bob - _lerp(0.0, 260.0, flyP);
        final badgeOpacity = (appearP * (1 - fadeOutP)).clamp(0.0, 1.0);

        final flameOpacity = igniteP.clamp(0.0, 1.0) * (1 - fadeOutP);
        final flameFlicker = 0.75 + math.sin(t * 2 * math.pi * 10) * 0.15;
        final flameScaleY = _lerp(1.0, 2.1, flyP);

        return Positioned.fill(
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Dim scrim over the login screen — also blocks taps on the form.
              Opacity(
                opacity: appearP * 0.55 * (1 - fadeOutP * 0.5),
                child: const ColoredBox(color: Colors.black),
              ),

              Transform.translate(
                offset: Offset(0, translateY),
                child: Transform.rotate(
                  angle: shake,
                  child: Transform.scale(
                    scale: scale,
                    child: Opacity(
                      opacity: badgeOpacity,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          _BadgeSquare(glowStrength: (0.25 + igniteP * 0.75 + flyP * 0.3).clamp(0.0, 1.0)),
                          Transform.scale(
                            scaleY: flameScaleY,
                            alignment: Alignment.topCenter,
                            child: Opacity(
                              opacity: (flameOpacity * flameFlicker).clamp(0.0, 1.0),
                              child: const _MiniFlame(),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // Ignition flash pulse.
              IgnorePointer(
                child: Opacity(
                  opacity: flashP.clamp(0.0, 1.0) * 0.35,
                  child: const ColoredBox(color: Colors.white),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

double _lerp(double a, double b, double t) => a + (b - a) * t;

class _BadgeSquare extends StatelessWidget {
  final double glowStrength;

  const _BadgeSquare({required this.glowStrength});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 64,
      height: 64,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.primary, Color(0xFF3B82F6)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary400.withValues(alpha: 0.6 * glowStrength),
            blurRadius: 36 * glowStrength,
            spreadRadius: 4 * glowStrength,
          ),
        ],
      ),
      child: const Icon(Icons.rocket_launch_rounded, color: Colors.white, size: 34),
    );
  }
}

class _MiniFlame extends StatelessWidget {
  const _MiniFlame();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 22,
      height: 32,
      decoration: BoxDecoration(
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(12)),
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.amber.shade200,
            Colors.orange.shade500,
            Colors.deepOrange.shade700.withValues(alpha: 0.0),
          ],
        ),
      ),
    );
  }
}
