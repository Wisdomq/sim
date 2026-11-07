/// API configuration.
///
/// The base URL is injected at build time via --dart-define:
///
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
///
/// Falls back to Android-emulator-friendly localhost for local dev.
class ApiConfig {
  ApiConfig._();

  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );

  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // Auth endpoints
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String me = '/auth/me';

  // Stock endpoints
  static const String simCards = '/stock/sim-cards';
  static const String sales = '/stock/sales';
  static const String sync = '/stock/sync';
  static const String distribute = '/stock/distribute';
  static const String assignToBa = '/stock/assign-to-ba';
  static const String returnToBranch = '/stock/return-to-branch';
  static const String returnRequests = '/stock/return-requests';
  static const String intakeBoxScan = '/stock/intake/box-scan';
  static const String intakePickListPdf = '/stock/intake/pick-list-pdf';

  // Account endpoints
  static const String branches = '/branches';
  static const String brandAmbassadors = '/brand-ambassadors';

  // Commission / performance
  static const String commissionPerformance = '/commission/performance';
  static const String commissionEarned = '/commission/earned';
  static const String commissionBaDailyTarget = '/commission/ba-daily-target';
  static const String commissionRules = '/commission/rules';
  static const String commissionTargets = '/commission/targets';

  // Reports
  static const String reports = '/reports';
  static const String reportsExport = '/reports/export';
  static const String reportsList = '/reports/list';
  static const String reportsDownload = '/reports/download/';

  // Reconciliation
  static const String reconciliationImports = '/reconciliation/imports';

  // Flags / notifications
  static const String flags = '/flags';
  static const String flagsNotifications = '/flags/notifications';
  static const String notificationRead = '/flags/notifications';
}
