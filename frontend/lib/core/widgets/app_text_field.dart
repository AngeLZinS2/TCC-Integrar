// `AppTextField` é o nome usado pelas telas da P2 para o campo de texto
// padrão. A implementação é uma só — a de `custom_text_field.dart` — para
// não existirem dois campos com aparência e comportamento divergentes.
//
// `hintText` existe porque as telas da P2 usam esse nome; internamente é o
// mesmo `hint` do CustomTextField.

import 'package:flutter/material.dart';

import 'custom_text_field.dart';

class AppTextField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final String? hintText;
  final IconData? prefixIcon;
  final Widget? suffixIcon;
  final bool obscureText;
  final TextInputType keyboardType;
  final String? Function(String?)? validator;
  final void Function(String)? onFieldSubmitted;
  final bool autofocus;
  final int maxLines;

  const AppTextField({
    super.key,
    required this.controller,
    required this.label,
    this.hintText,
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
    return CustomTextField(
      controller: controller,
      label: label,
      hint: hintText,
      prefixIcon: prefixIcon,
      suffixIcon: suffixIcon,
      obscureText: obscureText,
      keyboardType: keyboardType,
      validator: validator,
      onFieldSubmitted: onFieldSubmitted,
      autofocus: autofocus,
      maxLines: maxLines,
    );
  }
}
