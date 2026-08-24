import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  // ── Primary Palette (Blue / Indigo) ───────────────────────────────────────
  static const Color primary50 = Color(0xFFEFF6FF);
  static const Color primary100 = Color(0xFFDBEAFE);
  static const Color primary200 = Color(0xFFBFDBFE);
  static const Color primary300 = Color(0xFF93C5FD);
  static const Color primary400 = Color(0xFF60A5FA);
  static const Color primary = Color(0xFF2563EB); // Base Blue 600
  static const Color primary600 = Color(0xFF2563EB);
  static const Color primary700 = Color(0xFF1D4ED8);
  static const Color primary800 = Color(0xFF1E40AF);
  static const Color primary900 = Color(0xFF1E3A8A);

  // ── Neutrals (Slate) ──────────────────────────────────────────────────────
  static const Color slate50 = Color(0xFFF8FAFC);
  static const Color slate100 = Color(0xFFF1F5F9);
  static const Color slate200 = Color(0xFFE2E8F0);
  static const Color slate300 = Color(0xFFCBD5E1);
  static const Color slate400 = Color(0xFF94A3B8);
  static const Color slate500 = Color(0xFF64748B);
  static const Color slate600 = Color(0xFF475569);
  static const Color slate700 = Color(0xFF334155);
  static const Color slate800 = Color(0xFF1E293B);
  static const Color slate900 = Color(0xFF0F172A);
  static const Color slate950 = Color(0xFF020617);

  // ── Feedback Semantic Colors ──────────────────────────────────────────────
  static const Color success = Color(0xFF10B981);
  static const Color successLight = Color(0xFFECFDF5);
  static const Color successDark = Color(0xFF064E3B);
  static const Color successBorder = Color(0xFFA7F3D0);
  static const Color successDarkBorder = Color(0xFF065F46);
  static const Color successText = Color(0xFF047857);
  static const Color successDarkText = Color(0xFF6EE7B7);

  static const Color warning = Color(0xFFF59E0B);
  static const Color warningLight = Color(0xFFFFFBEB);
  static const Color warningDark = Color(0xFF78350F);
  static const Color warningBorder = Color(0xFFFDE68A);
  static const Color warningDarkBorder = Color(0xFF92400E);
  static const Color warningText = Color(0xFFB45309);
  static const Color warningDarkText = Color(0xFFFCD34D);

  static const Color error = Color(0xFFEF4444);
  static const Color errorLight = Color(0xFFFEF2F2);
  static const Color errorDark = Color(0xFF7F1D1D);
  static const Color errorBorder = Color(0xFFFECACA);
  static const Color errorDarkBorder = Color(0xFF991B1B);
  static const Color errorText = Color(0xFFB91C1C);
  static const Color errorDarkText = Color(0xFFFCA5A5);

  static const Color info = Color(0xFF0EA5E9);
  static const Color infoLight = Color(0xFFF0F9FF);
  static const Color infoDark = Color(0xFF0C4A6E);
  static const Color infoBorder = Color(0xFFBAE6FD);
  static const Color infoDarkBorder = Color(0xFF075985);
  static const Color infoText = Color(0xFF0369A1);
  static const Color infoDarkText = Color(0xFF7DD3FC);

  static const Color purple = Color(0xFF8B5CF6);
  static const Color purpleLight = Color(0xFFF5F3FF);
  static const Color purpleDark = Color(0xFF4C1D95);
  static const Color purpleBorder = Color(0xFFDDD6FE);
  static const Color purpleDarkBorder = Color(0xFF5B21B6);
  static const Color purpleText = Color(0xFF6D28D9);
  static const Color purpleDarkText = Color(0xFFC4B5FD);

  // ── Light Surfaces & Text ─────────────────────────────────────────────────
  static const Color background = Color(0xFFF8FAFC);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color card = Color(0xFFFFFFFF);
  static const Color border = Color(0xFFE2E8F0);
  static const Color borderSubtle = Color(0xFFF1F5F9);

  static const Color textPrimary = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF475569);
  static const Color textMuted = Color(0xFF94A3B8);
  static const Color textDisabled = Color(0xFFCBD5E1);

  // ── Dark Mode Surfaces ────────────────────────────────────────────────────
  static const Color darkBackground = Color(0xFF0B0F19);
  static const Color darkSurface = Color(0xFF111827);
  static const Color darkCard = Color(0xFF1E293B);
  static const Color darkCardHover = Color(0xFF24344D);
  static const Color darkBorder = Color(0xFF334155);
  static const Color darkBorderSubtle = Color(0xFF1E293B);

  static const Color darkTextPrimary = Color(0xFFF8FAFC);
  static const Color darkTextSecondary = Color(0xFF94A3B8);
  static const Color darkTextMuted = Color(0xFF64748B);
  static const Color darkTextDisabled = Color(0xFF475569);
}

class AppSpacing {
  static const double xxs = 2.0;
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double xl = 20.0;
  static const double xxl = 24.0;
  static const double xxxl = 32.0;
  static const double huge = 48.0;
}

class AppRadius {
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double xl = 20.0;
  static const double pill = 999.0;
}

class AppShadows {
  static List<BoxShadow> get sm => [
        BoxShadow(
          color: const Color(0xFF0F172A).withValues(alpha: 0.04),
          blurRadius: 6,
          offset: const Offset(0, 2),
        ),
      ];

  static List<BoxShadow> get md => [
        BoxShadow(
          color: const Color(0xFF0F172A).withValues(alpha: 0.06),
          blurRadius: 14,
          offset: const Offset(0, 4),
        ),
      ];

  static List<BoxShadow> get lg => [
        BoxShadow(
          color: const Color(0xFF0F172A).withValues(alpha: 0.08),
          blurRadius: 24,
          offset: const Offset(0, 8),
        ),
      ];

  static List<BoxShadow> get darkSm => [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.25),
          blurRadius: 6,
          offset: const Offset(0, 2),
        ),
      ];

  static List<BoxShadow> get darkMd => [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.35),
          blurRadius: 14,
          offset: const Offset(0, 4),
        ),
      ];

  static List<BoxShadow> get primaryGlow => [
        BoxShadow(
          color: AppColors.primary.withValues(alpha: 0.25),
          blurRadius: 20,
          offset: const Offset(0, 8),
        ),
      ];
}

/// Extensão de conveniência para acessar cores adaptativas conforme o tema ativo
extension AppThemeContextExtension on BuildContext {
  bool get isDark => Theme.of(this).brightness == Brightness.dark;

  /// Atalho para a escala tipográfica do tema ativo.
  TextTheme get textTheme => Theme.of(this).textTheme;

  Color get scaffoldBg => isDark ? AppColors.darkBackground : AppColors.background;
  Color get surfaceColor => isDark ? AppColors.darkSurface : AppColors.surface;
  Color get cardColor => isDark ? AppColors.darkCard : AppColors.card;
  Color get subtleBg => isDark ? const Color(0xFF1E293B) : AppColors.slate50;
  Color get borderColor => isDark ? AppColors.darkBorder : AppColors.border;
  Color get borderSubtleColor => isDark ? AppColors.darkBorderSubtle : AppColors.borderSubtle;

  Color get textPrimaryColor => isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
  Color get textSecondaryColor => isDark ? AppColors.darkTextSecondary : AppColors.textSecondary;
  Color get textMutedColor => isDark ? AppColors.darkTextMuted : AppColors.textMuted;
  Color get textDisabledColor => isDark ? AppColors.darkTextDisabled : AppColors.textDisabled;

  List<BoxShadow> get shadowSm => isDark ? AppShadows.darkSm : AppShadows.sm;
  List<BoxShadow> get shadowMd => isDark ? AppShadows.darkMd : AppShadows.md;
}

class AppTheme {
  // ── Light Theme ────────────────────────────────────────────────────────────
  static ThemeData get lightTheme {
    final baseTextTheme = GoogleFonts.interTextTheme();

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.background,
      primaryColor: AppColors.primary,
      colorScheme: const ColorScheme.light(
        primary: AppColors.primary,
        onPrimary: Colors.white,
        primaryContainer: AppColors.primary50,
        onPrimaryContainer: AppColors.primary900,
        secondary: AppColors.info,
        onSecondary: Colors.white,
        surface: AppColors.surface,
        onSurface: AppColors.textPrimary,
        error: AppColors.error,
        onError: Colors.white,
      ),
      textTheme: baseTextTheme.copyWith(
        displayLarge: baseTextTheme.displayLarge?.copyWith(
          fontSize: 32,
          fontWeight: FontWeight.w800,
          letterSpacing: -1.0,
          color: AppColors.textPrimary,
        ),
        displayMedium: baseTextTheme.displayMedium?.copyWith(
          fontSize: 26,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.75,
          color: AppColors.textPrimary,
        ),
        headlineLarge: baseTextTheme.headlineLarge?.copyWith(
          fontSize: 22,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
          color: AppColors.textPrimary,
        ),
        headlineMedium: baseTextTheme.headlineMedium?.copyWith(
          fontSize: 18,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
          color: AppColors.textPrimary,
        ),
        titleLarge: baseTextTheme.titleLarge?.copyWith(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
        titleMedium: baseTextTheme.titleMedium?.copyWith(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
        bodyLarge: baseTextTheme.bodyLarge?.copyWith(
          fontSize: 15,
          fontWeight: FontWeight.w400,
          color: AppColors.textPrimary,
          height: 1.5,
        ),
        bodyMedium: baseTextTheme.bodyMedium?.copyWith(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: AppColors.textSecondary,
          height: 1.5,
        ),
        bodySmall: baseTextTheme.bodySmall?.copyWith(
          fontSize: 12,
          fontWeight: FontWeight.w400,
          color: AppColors.textMuted,
          height: 1.4,
        ),
        labelLarge: baseTextTheme.labelLarge?.copyWith(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
        labelMedium: baseTextTheme.labelMedium?.copyWith(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
          color: AppColors.textSecondary,
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.surface,
        elevation: 0,
        centerTitle: false,
        scrolledUnderElevation: 0.5,
        iconTheme: IconThemeData(color: AppColors.textPrimary, size: 20),
        titleTextStyle: TextStyle(
          color: AppColors.textPrimary,
          fontSize: 17,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
      ),
      cardTheme: CardThemeData(
        color: AppColors.card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          side: const BorderSide(color: AppColors.border, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.border,
        thickness: 1,
        space: 1,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.xl),
          side: const BorderSide(color: AppColors.border),
        ),
        titleTextStyle: const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
        contentTextStyle: const TextStyle(
          color: AppColors.textSecondary,
          fontSize: 14,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.8),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.error),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.error, width: 1.8),
        ),
        hintStyle: const TextStyle(color: AppColors.textMuted, fontSize: 14),
        labelStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.2,
          ),
        ),
      ),
    );
  }

  // ── Dark Theme ─────────────────────────────────────────────────────────────
  static ThemeData get darkTheme {
    final baseTextTheme = GoogleFonts.interTextTheme(ThemeData.dark().textTheme);

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.darkBackground,
      primaryColor: AppColors.primary400,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.primary,
        onPrimary: Colors.white,
        primaryContainer: Color(0xFF1E3A8A),
        onPrimaryContainer: Color(0xFFDBEAFE),
        secondary: AppColors.info,
        onSecondary: Colors.white,
        surface: AppColors.darkSurface,
        onSurface: AppColors.darkTextPrimary,
        error: AppColors.error,
        onError: Colors.white,
      ),
      textTheme: baseTextTheme.copyWith(
        displayLarge: baseTextTheme.displayLarge?.copyWith(
          fontSize: 32,
          fontWeight: FontWeight.w800,
          letterSpacing: -1.0,
          color: AppColors.darkTextPrimary,
        ),
        displayMedium: baseTextTheme.displayMedium?.copyWith(
          fontSize: 26,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.75,
          color: AppColors.darkTextPrimary,
        ),
        headlineLarge: baseTextTheme.headlineLarge?.copyWith(
          fontSize: 22,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
          color: AppColors.darkTextPrimary,
        ),
        headlineMedium: baseTextTheme.headlineMedium?.copyWith(
          fontSize: 18,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
          color: AppColors.darkTextPrimary,
        ),
        titleLarge: baseTextTheme.titleLarge?.copyWith(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: AppColors.darkTextPrimary,
        ),
        titleMedium: baseTextTheme.titleMedium?.copyWith(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: AppColors.darkTextPrimary,
        ),
        bodyLarge: baseTextTheme.bodyLarge?.copyWith(
          fontSize: 15,
          fontWeight: FontWeight.w400,
          color: AppColors.darkTextPrimary,
          height: 1.5,
        ),
        bodyMedium: baseTextTheme.bodyMedium?.copyWith(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: AppColors.darkTextSecondary,
          height: 1.5,
        ),
        bodySmall: baseTextTheme.bodySmall?.copyWith(
          fontSize: 12,
          fontWeight: FontWeight.w400,
          color: AppColors.darkTextMuted,
          height: 1.4,
        ),
        labelLarge: baseTextTheme.labelLarge?.copyWith(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: AppColors.darkTextPrimary,
        ),
        labelMedium: baseTextTheme.labelMedium?.copyWith(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
          color: AppColors.darkTextSecondary,
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.darkSurface,
        elevation: 0,
        centerTitle: false,
        scrolledUnderElevation: 0.5,
        iconTheme: IconThemeData(color: AppColors.darkTextPrimary, size: 20),
        titleTextStyle: TextStyle(
          color: AppColors.darkTextPrimary,
          fontSize: 17,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
      ),
      cardTheme: CardThemeData(
        color: AppColors.darkCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          side: const BorderSide(color: AppColors.darkBorder, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.darkBorder,
        thickness: 1,
        space: 1,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.darkSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.xl),
          side: const BorderSide(color: AppColors.darkBorder),
        ),
        titleTextStyle: const TextStyle(
          color: AppColors.darkTextPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
        contentTextStyle: const TextStyle(
          color: AppColors.darkTextSecondary,
          fontSize: 14,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.darkCard,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.darkBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.darkBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.primary400, width: 1.8),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.error),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.error, width: 1.8),
        ),
        hintStyle: const TextStyle(color: AppColors.darkTextMuted, fontSize: 14),
        labelStyle: const TextStyle(color: AppColors.darkTextSecondary, fontSize: 14),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.2,
          ),
        ),
      ),
    );
  }
}
