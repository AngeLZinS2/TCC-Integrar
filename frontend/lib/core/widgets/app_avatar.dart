import 'package:flutter/material.dart';
import '../../app/theme.dart';

class AppAvatar extends StatelessWidget {
  final String name;
  final double size;
  final String? role;
  final bool showBorder;

  const AppAvatar({
    super.key,
    required this.name,
    this.size = 40.0,
    this.role,
    this.showBorder = true,
  });

  String get _initials {
    if (name.trim().isEmpty) return 'U';
    final parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    return name.substring(0, name.length >= 2 ? 2 : 1).toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const LinearGradient(
          colors: [Color(0xFF3B82F6), Color(0xFF1D4ED8)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: showBorder ? Border.all(color: Colors.white, width: 2) : null,
        boxShadow: showBorder ? AppShadows.sm : null,
      ),
      alignment: Alignment.center,
      child: Text(
        _initials,
        style: TextStyle(
          color: Colors.white,
          fontSize: size * 0.38,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
      ),
    );
  }
}
