import 'package:flutter_test/flutter_test.dart';
import 'package:simcards_app/features/ba/performance/performance_screen.dart';

void main() {
  group('toDoubleOrZero', () {
    test('parses num values', () {
      expect(toDoubleOrZero(5), 5.0);
      expect(toDoubleOrZero(5.25), 5.25);
      expect(toDoubleOrZero(0), 0.0);
    });

    test('parses numeric strings', () {
      expect(toDoubleOrZero('3.75'), 3.75);
      expect(toDoubleOrZero('0.00'), 0.0);
      expect(toDoubleOrZero('0'), 0.0);
      expect(toDoubleOrZero('-1.5'), -1.5);
    });

    test('falls back to 0 on null or non-numeric', () {
      expect(toDoubleOrZero(null), 0.0);
      expect(toDoubleOrZero(''), 0.0);
      expect(toDoubleOrZero('abc'), 0.0);
    });
  });
}