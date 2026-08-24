import 'package:flutter/material.dart';
import '../../app/theme.dart';

/// Uma opção de [AppDropdown].
///
/// `const`-friendly para que listas de opções fixas possam ser declaradas
/// como `const` no widget que as usa.
class AppDropdownOption<T> {
  final T value;
  final String label;

  const AppDropdownOption({required this.value, required this.label});
}

/// Seletor com o mesmo enquadramento visual do [CustomTextField].
///
/// Antes cada tela montava seu próprio `DropdownButtonHideUnderline` dentro
/// de um `Container` — o mesmo bloco repetido, com o rótulo escrito à mão
/// em cada lugar. Reunido aqui para que rótulo, borda e espaçamento fiquem
/// idênticos aos dos campos de texto ao lado.
class AppDropdown<T> extends StatelessWidget {
  final String? label;
  final T? value;
  final List<AppDropdownOption<T>> options;
  final ValueChanged<T?> onChanged;
  final String? hint;
  final IconData? prefixIcon;
  final bool enabled;

  const AppDropdown({
    super.key,
    required this.value,
    required this.options,
    required this.onChanged,
    this.label,
    this.hint,
    this.prefixIcon,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    // Um `value` que não está entre as opções faz o DropdownButton lançar.
    // Acontece de verdade quando a lista de opções chega depois do valor
    // (setor carregado por API, por exemplo), então tratamos como vazio.
    final valorValido = options.any((o) => o.value == value) ? value : null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ...[
          Text(
            label!,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: context.textSecondaryColor,
              letterSpacing: -0.1,
            ),
          ),
          const SizedBox(height: 6),
        ],
        Semantics(
          label: label,
          button: true,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            decoration: BoxDecoration(
              color: enabled ? null : context.subtleBg,
              border: Border.all(color: context.borderColor),
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: Row(
              children: [
                if (prefixIcon != null) ...[
                  Icon(prefixIcon, size: 18, color: context.textMutedColor),
                  const SizedBox(width: AppSpacing.sm),
                ],
                Expanded(
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<T>(
                      value: valorValido,
                      isExpanded: true,
                      hint: hint == null ? null : Text(hint!),
                      onChanged: enabled ? onChanged : null,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: context.textPrimaryColor,
                      ),
                      items: options
                          .map(
                            (o) => DropdownMenuItem<T>(
                              value: o.value,
                              child: Text(
                                o.label,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
