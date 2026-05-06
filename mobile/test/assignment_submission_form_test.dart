import 'package:coursum_mobile/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('validateSubmissionForm', () {
    test('rejects short answer', () {
      final result = validateSubmissionForm(
        isRu: true,
        answer: 'short',
        link: '',
      );
      expect(result.hasErrors, isTrue);
      expect(result.answerError, isNotNull);
    });

    test('rejects malformed link', () {
      final result = validateSubmissionForm(
        isRu: false,
        answer: 'This answer has enough content.',
        link: 'notaurl',
      );
      expect(result.hasErrors, isTrue);
      expect(result.linkError, isNotNull);
    });

    test('accepts valid payload', () {
      final result = validateSubmissionForm(
        isRu: false,
        answer: 'Implemented solution and verified expected behavior.',
        link: 'https://example.com/submission',
      );
      expect(result.hasErrors, isFalse);
    });
  });

  group('AssignmentSubmissionDraft', () {
    test('serializes and deserializes attached files', () {
      const draft = AssignmentSubmissionDraft(
        textAnswer: 'answer',
        linkAnswer: 'https://example.com',
        fileUrls: ['/media/a.pdf', '/media/b.png'],
        updatedAtIso: '2026-05-06T10:10:10Z',
      );
      final restored = AssignmentSubmissionDraft.fromJson(draft.toJson());
      expect(restored, isNotNull);
      expect(restored!.fileUrls.length, 2);
      expect(restored.linkAnswer, 'https://example.com');
    });
  });
}
