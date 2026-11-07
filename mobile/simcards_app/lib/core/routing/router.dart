import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../auth/auth_notifier.dart';
import '../auth/auth_user.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/forgot_password_screen.dart';
import '../../features/auth/reset_password_screen.dart';
import '../../features/ba/scan/scan_screen.dart';
import '../../features/ba/performance/performance_screen.dart';
import '../../features/branch/bas/ba_list_screen.dart';
import '../../features/branch/bas/create_ba_screen.dart';
import '../../features/branch/bas/ba_detail_screen.dart';
import '../../features/branch/stock/branch_stock_screen.dart';
import '../../features/branch/reports/branch_reports_screen.dart';
import '../../features/hq/stock/stock_intake_screen.dart';
import '../../features/hq/stock/distribute_screen.dart';
import '../../features/hq/stock/return_request_screen.dart';
import '../../features/hq/commission/commission_config_screen.dart';
import '../../features/hq/reconciliation/reconciliation_upload_screen.dart';
import '../../features/hq/reconciliation/reconciliation_summary_screen.dart';
import '../../features/hq/reconciliation/reconciliation_detail_screen.dart';
import '../../features/hq/reports/hq_reports_screen.dart';
import '../../features/hq/flags/flags_screen.dart';
import '../../features/hq/hq_home_screen.dart';
import '../../features/branch/stock/branch_returns_screen.dart';
import '../../features/branch/branch_home_screen.dart';
import '../../features/ba/ba_home_screen.dart';
import '../../features/ba/stock/ba_stock_screen.dart';

class AppRoutes {
  static const login = '/login';
  static const forgotPassword = '/forgot-password';
  static const resetPassword = '/reset-password';
  static const baHome = '/ba';
  static const baScan = '/ba/scan';
  static const baPerformance = '/ba/performance';
  static const baStock = '/ba/stock';
  static const branchHome = '/branch';
  static const branchBas = '/branch/bas';
  static const branchCreateBa = '/branch/bas/create';
  static const branchBaDetail = '/branch/bas/:baId';
  static const branchStock = '/branch/stock';
  static const branchReturns = '/branch/stock/returns';
  static const branchReports = '/branch/reports';
  static const hqHome = '/hq';
  static const hqStock = '/hq/stock';
  static const hqDistribute = '/hq/distribute';
  static const hqReturnRequest = '/hq/stock/returns';
  static const hqCommission = '/hq/commission';
  static const hqReconciliation = '/hq/reconciliation';
  static const hqReconciliationSummary = '/hq/reconciliation/:importId';
  static const hqReconciliationDetail = '/hq/reconciliation/:importId/detail';
  static const hqReports = '/hq/reports';
  static const hqFlags = '/hq/flags';
}

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: AppRoutes.login,
    redirect: (context, state) {
      final location = state.matchedLocation;
      final isLoginRoute = location == AppRoutes.login;
      final isPublicRoute = location == AppRoutes.forgotPassword ||
          location == AppRoutes.resetPassword;

      if (authState is AuthLoading) {
        return null; // stay, splash will show
      }

      if (authState is AuthUnauthenticated || authState is AuthError) {
        // Public password-reset routes must stay reachable while signed out.
        if (isLoginRoute || isPublicRoute) return null;
        return AppRoutes.login;
      }

      if (authState is AuthAuthenticated) {
        if (isLoginRoute) {
          return _homeForRole(authState.user.role);
        }
      }
      return null;
    },
    routes: [
      GoRoute(path: AppRoutes.login, builder: (_, __) => const LoginScreen()),
      GoRoute(path: AppRoutes.forgotPassword, builder: (_, __) => const ForgotPasswordScreen()),
      GoRoute(
        path: AppRoutes.resetPassword,
        builder: (_, state) {
          final token = state.uri.queryParameters['token'];
          if (token == null || token.isEmpty) {
            return const ForgotPasswordScreen();
          }
          return ResetPasswordScreen(token: token);
        },
      ),

      // BA routes
      GoRoute(path: AppRoutes.baHome, builder: (_, __) => const BaHomeScreen()),
      GoRoute(path: AppRoutes.baScan, builder: (_, __) => const ScanScreen()),
      GoRoute(path: AppRoutes.baPerformance, builder: (_, __) => const PerformanceScreen()),
      GoRoute(path: AppRoutes.baStock, builder: (_, __) => const BaStockScreen()),

      // Branch routes
      GoRoute(path: AppRoutes.branchHome, builder: (_, __) => const BranchHomeScreen()),
      GoRoute(path: AppRoutes.branchBas, builder: (_, __) => const BaListScreen()),
      GoRoute(path: AppRoutes.branchCreateBa, builder: (_, __) => const CreateBaScreen()),
      GoRoute(
        path: AppRoutes.branchBaDetail,
        builder: (_, state) => BaDetailScreen(baId: int.parse(state.pathParameters['baId']!)),
      ),
      GoRoute(path: AppRoutes.branchStock, builder: (_, __) => const BranchStockScreen()),
      GoRoute(path: AppRoutes.branchReturns, builder: (_, __) => const BranchReturnsScreen()),
      GoRoute(path: AppRoutes.branchReports, builder: (_, __) => const BranchReportsScreen()),

      // HQ routes
      GoRoute(path: AppRoutes.hqHome, builder: (_, __) => const HqHomeScreen()),
      GoRoute(path: AppRoutes.hqStock, builder: (_, __) => const StockIntakeScreen()),
      GoRoute(path: AppRoutes.hqDistribute, builder: (_, __) => const DistributeScreen()),
      GoRoute(path: AppRoutes.hqReturnRequest, builder: (_, __) => const ReturnRequestScreen()),
      GoRoute(path: AppRoutes.hqCommission, builder: (_, __) => const CommissionConfigScreen()),
      GoRoute(path: AppRoutes.hqReconciliation, builder: (_, __) => const ReconciliationUploadScreen()),
      GoRoute(
        path: AppRoutes.hqReconciliationSummary,
        builder: (_, state) => ReconciliationSummaryScreen(
          importId: int.parse(state.pathParameters['importId']!),
        ),
      ),
      GoRoute(
        path: AppRoutes.hqReconciliationDetail,
        builder: (_, state) => ReconciliationDetailScreen(
          importId: int.parse(state.pathParameters['importId']!),
        ),
      ),
      GoRoute(path: AppRoutes.hqReports, builder: (_, __) => const HqReportsScreen()),
      GoRoute(path: AppRoutes.hqFlags, builder: (_, __) => const FlagsScreen()),
    ],
  );
});

String _homeForRole(UserRole role) {
  switch (role) {
    case UserRole.ba:
      return AppRoutes.baHome;
    case UserRole.branch:
      return AppRoutes.branchHome;
    case UserRole.hq:
      return AppRoutes.hqHome;
  }
}
