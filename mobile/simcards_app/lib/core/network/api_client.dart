import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/api_config.dart';
import '../storage/secure_storage.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  final storage = ref.watch(secureStorageProvider);
  return ApiClient(storage);
});

class ApiClient {
  ApiClient(this._storage) {
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiConfig.baseUrl,
        connectTimeout: ApiConfig.connectTimeout,
        receiveTimeout: ApiConfig.receiveTimeout,
        headers: {'Content-Type': 'application/json'},
      ),
    );
    _dio.interceptors.add(_AuthInterceptor(_storage, _dio));
  }

  final SecureStorageService _storage;
  late final Dio _dio;

  Dio get dio => _dio;

  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? queryParameters}) =>
      _dio.get(path, queryParameters: queryParameters);

  Future<Response<T>> post<T>(String path, {dynamic data}) =>
      _dio.post(path, data: data);

  Future<Response<T>> postMultipart<T>(String path, FormData data) =>
      _dio.post(path, data: data);

  Future<Response<T>> delete<T>(String path) => _dio.delete(path);
}

/// Attaches the JWT access token to every request.
/// On 401, attempts a single token refresh then retries the original request.
class _AuthInterceptor extends Interceptor {
  _AuthInterceptor(this._storage, this._dio);

  final SecureStorageService _storage;
  final Dio _dio;
  bool _refreshing = false;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Don't attach tokens to the login / refresh calls themselves
    if (_isPublicPath(options.path)) {
      return handler.next(options);
    }
    final token = await _storage.getAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401 && !_refreshing) {
      _refreshing = true;
      try {
        final refreshToken = await _storage.getRefreshToken();
        if (refreshToken == null) {
          await _storage.clearTokens();
          return handler.next(err);
        }

        // Attempt token refresh (use a fresh Dio to avoid interceptor loop)
        final refreshDio = Dio(BaseOptions(baseUrl: ApiConfig.baseUrl));
        final refreshResp = await refreshDio.post(
          ApiConfig.refresh,
          data: {'refresh_token': refreshToken},
        );

        final newAccess = refreshResp.data['access_token'] as String;
        final newRefresh = refreshResp.data['refresh_token'] as String;
        await _storage.saveTokens(
          accessToken: newAccess,
          refreshToken: newRefresh,
        );

        // Retry original request with new token
        final opts = err.requestOptions;
        opts.headers['Authorization'] = 'Bearer $newAccess';
        final retryResp = await _dio.fetch(opts);
        handler.resolve(retryResp);
      } catch (_) {
        await _storage.clearTokens();
        handler.next(err);
      } finally {
        _refreshing = false;
      }
    } else {
      handler.next(err);
    }
  }

  bool _isPublicPath(String path) =>
      path.contains('/auth/login') || path.contains('/auth/refresh');
}
