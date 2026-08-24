import 'package:flutter/material.dart';
import '../../app/theme.dart';

class CustomTextField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final String? hint;
  final IconData? prefixIcon;
  final Widget? suffixIcon;
  final bool obscureText;
  final TextInputType keyboardType;
  final String? Function(String?)? validator;
  final void Function(String)? onFieldSubmitted;
  final bool autofocus;
  final int maxLines;

  const CustomTextField({
    super.key,
    required this.controller,
    required this.label,
    this.hint,
    this.prefixIcon,
    this.suffixIcon,
    this.obscureText = false,
    this.keyboardType = TextInputType.text,
    this.validator,
    this.onFieldSubmitted,
    this.autofocus = false,
    this.maxLines = 1,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: isDark ? AppColors.darkTextSecondary : AppColors.textSecondary,
            letterSpacing: -0.1,
          ),
        ),
        const SizedBox(height: 6),
        TextFormField(
          controller: controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          validator: validator,
          onFieldSubmitted: onFieldSubmitted,
          autofocus: autofocus,
          maxLines: maxLines,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary,
          ),
          decoration: InputDecoration(
            hintText: hint,
            prefixIcon: prefixIcon != null
                ? Icon(prefixIcon, size: 18, color: isDark ? AppColors.darkTextMuted : AppColors.slate400)
                : null,
            suffixIcon: suffixIcon,
          ),
        ),
      ],
    );
  }
}
