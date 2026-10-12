import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:simcards_app/core/auth/auth_user.dart';

void main() {
  group('AuthUser JWT parsing', () {
    test('parses BA token claims properly', () {
      final header = base64Url.encode(utf8.encode(jsonEncode({'alg': 'HS256', 'typ': 'JWT'})));
      final payload = base64Url.encode(utf8.encode(jsonEncode({
        'sub': '42',
        'dealer_id': 1,
        'role': 'BA',
        'branch_id': 5,
        'ba_id': 10,
      })));
      final fakeJwt = '$header.$payload.signature';

      final user = AuthUser.fromJwt(fakeJwt);
      expect(user.userId, 42);
      expect(user.dealerId, 1);
      expect(user.role, UserRole.ba);
      expect(user.isBa, isTrue);
      expect(user.isBranch, isFalse);
      expect(user.isHq, isFalse);
      expect(user.branchId, 5);
      expect(user.baId, 10);
    });

    test('parses Branch and HQ token roles', () {
      final header = base64Url.encode(utf8.encode(jsonEncode({'alg': 'HS256'})));
      final branchPayload = base64Url.encode(utf8.encode(jsonEncode({
        'sub': '100',
        'dealer_id': 2,
        'role': 'BRANCH',
        'branch_id': 7,
      })));
      final branchUser = AuthUser.fromJwt('$header.$branchPayload.sig');
      expect(branchUser.isBranch, isTrue);

      final hqPayload = base64Url.encode(utf8.encode(jsonEncode({
        'sub': '1',
        'dealer_id': 2,
        'role': 'HQ',
      })));
      final hqUser = AuthUser.fromJwt('$header.$hqPayload.sig');
      expect(hqUser.isHq, isTrue);
    });
  });
}
