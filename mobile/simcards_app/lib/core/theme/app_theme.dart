import 'package:flutter/material.dart';

/// Safaricom brand palette + typography.
class AppTheme {
  AppTheme._();

  // Safaricom green
  static const Color _primary = Color(0xFF4CAF50);
  static const Color _primaryDark = Color(0xFF388E3C);
  static const Color _primaryLight = Color(0xFFC8E6C9);
  static const Color _accent = Color(0xFFFF5722);
  static const Color _error = Color(0xFFD32F2F);
  static const Color _success = Color(0xFF2E7D32);
  static const Color _warning = Color(0xFFF57F17);

  static ThemeData light() {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: _primary,
        primary: _primary,
        secondary: _accent,
        error: _error,
        brightness: Brightness.light,
      ),
      scaffoldBackgroundColor: const Color(0xFFF5F5F5),
    );
    return base.copyWith(
      appBarTheme: AppBarTheme(
        backgroundColor: _primary,
        foregroundColor: Colors.white,
        elevation: 2,
        titleTextStyle: base.textTheme.titleLarge?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w600,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: _primary,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        color: Colors.white,
      ),
      extensions: const [AppColors(
        success: _success,
        warning: _warning,
        primaryDark: _primaryDark,
        primaryLight: _primaryLight,
      )],
    );
  }

  static ThemeData dark() {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: _primary,
        primary: _primary,
        secondary: _accent,
        error: _error,
        brightness: Brightness.dark,
      ),
    );
    return base.copyWith(
      extensions: const [AppColors(
        success: _success,
        warning: _warning,
        primaryDark: _primaryDark,
        primaryLight: _primaryLight,
      )],
    );
  }
}

/// Custom theme extension for semantic colours not in ColorScheme.
@immutable
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({
    required this.success,
    required this.warning,
    required this.primaryDark,
    required this.primaryLight,
  });

  final Color success;
  final Color warning;
  final Color primaryDark;
  final Color primaryLight;

  @override
  AppColors copyWith({
    Color? success,
    Color? warning,
    Color? primaryDark,
    Color? primaryLight,
  }) {
    return AppColors(
      success: success ?? this.success,
      warning: warning ?? this.warning,
      primaryDark: primaryDark ?? this.primaryDark,
      primaryLight: primaryLight ?? this.primaryLight,
    );
  }

  @override
  AppColors lerp(AppColors? other, double t) {
    if (other == null) return this;
    return AppColors(
      success: Color.lerp(success, other.success, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      primaryDark: Color.lerp(primaryDark, other.primaryDark, t)!,
      primaryLight: Color.lerp(primaryLight, other.primaryLight, t)!,
    );
  }
}
