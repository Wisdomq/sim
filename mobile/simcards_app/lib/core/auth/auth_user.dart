import 'dart:convert';

/// The JWT claims returned by the backend on login.
/// Claims: sub (user id), dealer_id, role, branch_id, ba_id.
class AuthUser {
  const AuthUser({
    required this.userId,
    required this.dealerId,
    required this.role,
    this.branchId,
    this.baId,
    required this.email,
  });

  final int userId;
  final int dealerId;
  final UserRole role;
  final int? branchId;
  final int? baId;
  final String email;

  static AuthUser fromJwt(String token) {
    final parts = token.split('.');
    if (parts.length != 3) throw const FormatException('Invalid JWT');
    final payload = utf8.decode(
      base64Url.decode(base64Url.normalize(parts[1])),
    );
    final claims = jsonDecode(payload) as Map<String, dynamic>;
    return AuthUser(
      userId: int.parse(claims['sub'] as String),
      dealerId: claims['dealer_id'] as int,
      role: UserRole.fromValue(claims['role'] as String),
      branchId: claims['branch_id'] as int?,
      baId: claims['ba_id'] as int?,
      email: '',  // populated separately from /auth/me if needed
    );
  }

  bool get isHq => role == UserRole.hq;
  bool get isBranch => role == UserRole.branch;
  bool get isBa => role == UserRole.ba;
}

enum UserRole {
  hq,
  branch,
  ba;

  static UserRole fromValue(String v) {
    switch (v.toUpperCase()) {
      case 'HQ':
        return UserRole.hq;
      case 'BRANCH':
        return UserRole.branch;
      case 'BA':
        return UserRole.ba;
      default:
        throw ArgumentError('Unknown role: $v');
    }
  }
}
