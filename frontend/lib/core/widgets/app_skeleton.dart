import 'package:flutter/material.dart';
import '../../app/theme.dart';

class AppSkeleton extends StatefulWidget {
  final double width;
  final double height;
  final double? borderRadius;
  final ShapeBorder? shape;

  const AppSkeleton({
    super.key,
    required this.width,
    required this.height,
    this.borderRadius,
    this.shape,
  });

  const AppSkeleton.circle({
    super.key,
    required double size,
  })  : width = size,
        height = size,
        borderRadius = null,
        shape = const CircleBorder();

  const AppSkeleton.card({
    super.key,
    this.height = 120.0,
  })  : width = double.infinity,
        borderRadius = AppRadius.lg,
        shape = null;

  @override
  State<AppSkeleton> createState() => _AppSkeletonState();
}

class _AppSkeletonState extends State<AppSkeleton> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);

    _animation = Tween<double>(begin: 0.4, end: 0.9).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    final baseColor = isDark ? const Color(0xFF1E293B) : AppColors.slate200;

    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: ShapeDecoration(
            color: baseColor.withValues(alpha: _animation.value),
            shape: widget.shape ??
                RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(widget.borderRadius ?? AppRadius.md),
                ),
          ),
        );
      },
    );
  }
}
