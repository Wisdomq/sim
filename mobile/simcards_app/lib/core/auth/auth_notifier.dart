import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/api_config.dart';
import '../network/api_client.dart';
import '../storage/secure_storage.dart';
import 'auth_user.dart';

/// Current authentication state.
sealed class AuthState {
  const AuthState();
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

class AuthAuthenticated extends AuthState {
  const AuthAuthenticated(this.user);
  final AuthUser user;
}

class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}

class AuthError extends AuthState {
  const AuthError(this.message);
  final String message;
}

/// Provider for current auth user — null when unauthenticated.
final currentUserProvider = StateProvider<AuthUser?>((ref) => null);

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._ref) : super(const AuthLoading()) {
    _tryRestoreSession();
  }

  final Ref _ref;

  SecureStorageService get _storage => _ref.read(secureStorageProvider);
  ApiClient get _client => _ref.read(apiClientProvider);

  Future<void> _tryRestoreSession() async {
    final token = await _storage.getAccessToken();
    if (token == null) {
      state = const AuthUnauthenticated();
      return;
    }
    try {
      final user = AuthUser.fromJwt(token);
      _ref.read(currentUserProvider.notifier).state = user;
      state = AuthAuthenticated(user);
    } catch (_) {
      await _storage.clearTokens();
      state = const AuthUnauthenticated();
    }
  }

  Future<void> login(String email, String password) async {
    state = const AuthLoading();
    try {
      final resp = await _client.post(
        ApiConfig.login,
        data: {'email': email, 'password': password},
      );
      final accessToken = resp.data['access_token'] as String;
      final refreshToken = resp.data['refresh_token'] as String;
      await _storage.saveTokens(
        accessToken: accessToken,
        refreshToken: refreshToken,
      );
      final user = AuthUser.fromJwt(accessToken);
      _ref.read(currentUserProvider.notifier).state = user;
      state = AuthAuthenticated(user);
    } catch (e) {
      state = AuthError(_friendlyError(e));
    }
  }

  Future<void> logout() async {
    await _storage.clearTokens();
    _ref.read(currentUserProvider.notifier).state = null;
    state = const AuthUnauthenticated();
  }

  String _friendlyError(Object e) {
    // DioException carries response body in e.response?.data
    final data = (e as dynamic).response?.data;
    if (data is Map && data['detail'] != null) {
      return data['detail'].toString();
    }
    return 'Login failed. Check your connection and try again.';
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(ref),
);
