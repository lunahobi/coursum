import 'package:coursum_mobile/main.dart';
import 'package:coursum_mobile/app_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const sampleSession = SessionState(
  accessToken: 'token',
  tenantCode: 'acme',
  baseUrl: 'http://localhost:8000/api/v1',
);

bool richTextHasTapRecognizer(WidgetTester tester, String text) {
  bool inspectSpan(InlineSpan span) {
    if (span is TextSpan) {
      if ((span.text?.contains(text) ?? false) &&
          span.recognizer is TapGestureRecognizer) {
        return true;
      }
      return span.children?.any(inspectSpan) ?? false;
    }
    return false;
  }

  return tester.widgetList<RichText>(find.byType(RichText)).any(
        (richText) => inspectSpan(richText.text),
      );
}

bool richTextPlainTextContains(WidgetTester tester, String text) {
  return tester.widgetList<RichText>(find.byType(RichText)).any(
        (richText) => richText.text.toPlainText().contains(text),
      );
}

CourseOutlinePayload sampleOutline({required int currentLessonId}) {
  return CourseOutlinePayload(
    courseId: 1,
    courseTitle: 'Security Essentials',
    description: 'A sample course for the mobile player.',
    totalLessons: 2,
    completedLessons: currentLessonId == 2 ? 1 : 0,
    progressPercent: currentLessonId == 2 ? 50 : 0,
    resumeLessonId: currentLessonId,
    sections: const [
      CourseOutlineSection(
        id: 101,
        title: 'Core module',
        sortOrder: 1,
        isVisible: true,
      ),
      CourseOutlineSection(
        id: 102,
        title: 'Follow-up',
        sortOrder: 2,
        isVisible: true,
      ),
    ],
    lessons: [
      CourseOutlineLesson(
        id: 1,
        sectionId: 101,
        title: 'Password managers',
        summary: 'Why unique credentials matter.',
        sortOrder: 1,
        durationMinutes: 8,
        pageCount: 2,
        currentPageIndex: currentLessonId == 1 ? 0 : 1,
        isCompleted: currentLessonId == 2,
        isCurrent: currentLessonId == 1,
        hasVideo: true,
      ),
      CourseOutlineLesson(
        id: 2,
        sectionId: 102,
        title: 'Phishing signals',
        summary: 'How to slow down and inspect suspicious messages.',
        sortOrder: 2,
        durationMinutes: 7,
        pageCount: 2,
        currentPageIndex: 0,
        isCompleted: false,
        isCurrent: currentLessonId == 2,
        hasVideo: false,
      ),
    ],
  );
}

LessonPlayerPayload buildPayload({
  required int lessonId,
  required String lessonTitle,
  required int? previousLessonId,
  required int? nextLessonId,
  required List<LessonPageData> pages,
}) {
  final chapters = <String, List<LessonChapterPageData>>{};
  for (var index = 0; index < pages.length; index += 1) {
    final page = pages[index];
    chapters.putIfAbsent(page.chapterTitle, () => []);
    chapters[page.chapterTitle]!.add(
      LessonChapterPageData(
        pageId: page.pageId,
        pageTitle: page.pageTitle,
        pageIndex: index,
      ),
    );
  }
  return LessonPlayerPayload(
    courseId: 1,
    courseTitle: 'Security Essentials',
    lessonId: lessonId,
    lessonTitle: lessonTitle,
    summary: 'Sample structured lesson',
    durationMinutes: 8,
    pages: pages,
    chapters: chapters.entries
        .map((entry) =>
            LessonChapterData(chapterTitle: entry.key, pages: entry.value))
        .toList(),
    outline: sampleOutline(currentLessonId: lessonId),
    state: const LessonPlayerStateData(
      currentPageIndex: 0,
      completedPageIds: [],
      isCompleted: false,
      lastVideoPositionSeconds: 0,
    ),
    previousLessonId: previousLessonId,
    nextLessonId: nextLessonId,
  );
}

final lessonOne = buildPayload(
  lessonId: 1,
  lessonTitle: 'Password managers',
  previousLessonId: null,
  nextLessonId: 2,
  pages: const [
    LessonPageData(
      pageId: 'page-1',
      chapterTitle: 'Context',
      pageTitle: 'Why password managers matter',
      blocks: [
        LessonBlockData(
            type: 'text', text: 'Unique credentials reduce breach reuse risk.'),
        LessonBlockData(
            type: 'video',
            url: 'https://cdn.example.com/passwords.mp4',
            title: 'Password manager demo'),
      ],
    ),
    LessonPageData(
      pageId: 'page-2',
      chapterTitle: 'Practice',
      pageTitle: 'Daily habits',
      blocks: [
        LessonBlockData(
            type: 'text', text: '- Use the approved manager\n- Enable MFA'),
      ],
    ),
  ],
);

final lessonTwo = buildPayload(
  lessonId: 2,
  lessonTitle: 'Phishing signals',
  previousLessonId: 1,
  nextLessonId: null,
  pages: const [
    LessonPageData(
      pageId: 'page-3',
      chapterTitle: 'Context',
      pageTitle: 'Pause before you click',
      blocks: [
        LessonBlockData(
            type: 'text',
            text: 'Check sender, urgency, and the real destination.'),
      ],
    ),
    LessonPageData(
      pageId: 'page-4',
      chapterTitle: 'Practice',
      pageTitle: 'Report the message',
      blocks: [
        LessonBlockData(type: 'text', text: 'Use the approved reporting flow.'),
      ],
    ),
  ],
);

final htmlLesson = buildPayload(
  lessonId: 3,
  lessonTitle: 'Rich lesson',
  previousLessonId: null,
  nextLessonId: null,
  pages: const [
    LessonPageData(
      pageId: 'page-html',
      chapterTitle: 'Rich text',
      pageTitle: 'HTML page',
      blocks: [
        LessonBlockData(
          type: 'html',
          html:
              '<h2>Checklist</h2><p>Use the <strong>approved</strong> flow and open <a href="/media/notes.pdf">Download notes</a>. Скачайте и ознакомьтесь с <a href="/media/summary.pdf">конспектом</a> урока.</p><pre><code>Subject: Update request</code></pre><a href="/media/handout.pdf">Open handout</a>',
        ),
      ],
    ),
  ],
);

const sampleAttemptReview = AttemptReviewPayload(
  attemptId: 77,
  testId: 1,
  testTitle: 'Security Checkpoint',
  courseId: 1,
  courseTitle: 'Security Essentials',
  scorePercent: 50,
  correctAnswers: 1,
  totalQuestions: 2,
  averageResponseSeconds: 9,
  finalDifficulty: 1,
  difficultyPath: [3, 4, 1],
  weakTopics: [
    {'topic_title': 'Phishing', 'score': 3},
  ],
  startedAt: null,
  finishedAt: null,
  questions: [
    AttemptReviewQuestion(
      questionId: 1001,
      questionNumber: 1,
      text: 'Which practice keeps account access safer?',
      difficulty: 3,
      responseSeconds: 12,
      isCorrect: true,
      explanation: 'A password manager reduces reuse and phishing risk.',
      topicTitles: ['Passwords'],
      selectedOptionId: 1,
      selectedOptionText: 'Use the approved password manager',
      correctOptionId: 1,
      correctOptionText: 'Use the approved password manager',
      options: [
        AttemptReviewOption(
          id: 2,
          text: 'Reuse one complex password everywhere',
          isSelected: false,
          isCorrect: false,
        ),
        AttemptReviewOption(
          id: 1,
          text: 'Use the approved password manager',
          isSelected: true,
          isCorrect: true,
        ),
      ],
    ),
    AttemptReviewQuestion(
      questionId: 1002,
      questionNumber: 2,
      text: 'How should you respond to a suspicious email?',
      difficulty: 2,
      responseSeconds: 15,
      isCorrect: false,
      explanation:
          'Reporting suspicious mail early protects the rest of the team.',
      topicTitles: ['Phishing'],
      selectedOptionId: 4,
      selectedOptionText: 'Forward it to colleagues for opinions',
      correctOptionId: 3,
      correctOptionText: 'Report it through the approved channel',
      options: [
        AttemptReviewOption(
          id: 4,
          text: 'Forward it to colleagues for opinions',
          isSelected: true,
          isCorrect: false,
        ),
        AttemptReviewOption(
          id: 3,
          text: 'Report it through the approved channel',
          isSelected: false,
          isCorrect: true,
        ),
      ],
    ),
  ],
);

class CoursePlayerHarness extends StatefulWidget {
  const CoursePlayerHarness({
    super.key,
    required this.payloads,
    this.videoPreviewModes = const {
      'https://cdn.example.com/passwords.mp4': InlineVideoPreviewMode.embedded,
    },
  });

  final Map<int, LessonPlayerPayload> payloads;
  final Map<String, InlineVideoPreviewMode> videoPreviewModes;

  @override
  State<CoursePlayerHarness> createState() => _CoursePlayerHarnessState();
}

class _CoursePlayerHarnessState extends State<CoursePlayerHarness> {
  late int lessonId;
  int pageIndex = 0;
  Set<String> completedPageIds = <String>{};

  LessonPlayerPayload get payload => widget.payloads[lessonId]!;

  @override
  void initState() {
    super.initState();
    lessonId = widget.payloads.keys.first;
  }

  void goToPage(int targetPageIndex) {
    setState(() {
      if (targetPageIndex > pageIndex && payload.pages.isNotEmpty) {
        completedPageIds = {
          ...completedPageIds,
          payload.pages[pageIndex].pageId
        };
      }
      pageIndex = targetPageIndex;
    });
  }

  void openLesson(int targetLessonId) {
    setState(() {
      lessonId = targetLessonId;
      pageIndex = 0;
      completedPageIds = <String>{};
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        body: CoursePlayerBody(
          session: sampleSession,
          payload: payload,
          currentPageIndex: pageIndex,
          completedPageIds: completedPageIds,
          savedVideoPositionFor: (_) => 0,
          onGoToPage: goToPage,
          onGoToPreviousPage: () => goToPage(pageIndex - 1),
          onGoToNextPage: () {
            if (pageIndex >= payload.pages.length - 1) {
              setState(() => completedPageIds =
                  payload.pages.map((page) => page.pageId).toSet());
              if (payload.nextLessonId != null) {
                openLesson(payload.nextLessonId!);
              }
            } else {
              goToPage(pageIndex + 1);
            }
          },
          onOpenLesson: openLesson,
          onMarkComplete: () async => setState(() => completedPageIds =
              payload.pages.map((page) => page.pageId).toSet()),
          onVideoPositionChanged: (_, __) {},
          videoPreviewModes: widget.videoPreviewModes,
        ),
      ),
    );
  }
}

class FakeAdaptiveApiClient extends ApiClient {
  FakeAdaptiveApiClient() : super(baseUrl: sampleSession.baseUrl);

  int nextQuestionIndex = 0;
  final List<int> capturedResponseSeconds = <int>[];

  @override
  Future<Map<String, dynamic>> startAttempt(
      int testId, SessionState session) async {
    nextQuestionIndex = 0;
    capturedResponseSeconds.clear();
    return {
      'attempt_id': 99,
      'status': 'in_progress',
      'question_limit': 2,
      'baseline_difficulty': 3,
    };
  }

  @override
  Future<Map<String, dynamic>?> getAttemptQuestion(
      int attemptId, SessionState session) async {
    if (nextQuestionIndex == 0) {
      return {
        'id': 1001,
        'text': 'Which practice keeps account access safer?',
        'difficulty': 3,
        'estimated_seconds': 25,
        'question_number': 1,
        'total_questions': 2,
        'remaining_questions': 1,
        'target_difficulty': 3,
        'topic_titles': ['Passwords'],
        'options': [
          {'id': 1, 'text': 'Use the approved password manager'},
          {'id': 2, 'text': 'Reuse one complex password everywhere'},
        ],
      };
    }
    if (nextQuestionIndex == 1) {
      return {
        'id': 1002,
        'text': 'How should you respond to a suspicious email?',
        'difficulty': 2,
        'estimated_seconds': 20,
        'question_number': 2,
        'total_questions': 2,
        'remaining_questions': 0,
        'target_difficulty': 2,
        'topic_titles': ['Phishing'],
        'options': [
          {'id': 3, 'text': 'Report it through the approved channel'},
          {'id': 4, 'text': 'Forward it to colleagues for opinions'},
        ],
      };
    }
    return null;
  }

  @override
  Future<Map<String, dynamic>> submitAttemptAnswer(
    int attemptId,
    SessionState session, {
    required int questionId,
    required int answerOptionId,
    required int responseSeconds,
  }) async {
    capturedResponseSeconds.add(responseSeconds);
    if (questionId == 1001) {
      nextQuestionIndex = 1;
      return {
        'is_correct': true,
        'previous_difficulty': 3,
        'current_difficulty': 4,
        'next_question_difficulty': 2,
        'answered_questions': 1,
        'total_questions': 2,
        'remaining_questions': 1,
        'correct_option_id': 1,
        'correct_option_text': 'Use the approved password manager',
        'explanation': 'A password manager reduces reuse and phishing risk.',
        'topic_titles': ['Passwords'],
      };
    }
    nextQuestionIndex = 2;
    return {
      'is_correct': false,
      'previous_difficulty': 2,
      'current_difficulty': 1,
      'next_question_difficulty': null,
      'answered_questions': 2,
      'total_questions': 2,
      'remaining_questions': 0,
      'correct_option_id': 3,
      'correct_option_text': 'Report it through the approved channel',
      'explanation':
          'Reporting suspicious mail early protects the rest of the team.',
      'topic_titles': ['Phishing'],
    };
  }

  @override
  Future<Map<String, dynamic>> finishAttempt(
      int attemptId, SessionState session) async {
    return {
      'score_percent': 50,
      'recommendation_count': 1,
      'recommendations': [
        {
          'priority': 1,
          'text': 'Repeat the phishing lesson before the next attempt.',
          'topic_id': 2,
          'topic_title': 'Phishing',
          'lesson_id': 22,
          'lesson_title': 'Phishing signals',
          'course_id': 1,
          'course_title': 'Security Essentials',
          'signal_score': 3,
          'signal_level': 'medium',
          'reason':
              'Phishing included incorrect or slower-than-expected answers.',
        },
      ],
      'weak_topics': [
        {'topic_id': 2, 'topic_title': 'Phishing', 'score': 3},
      ],
      'correct_answers': 1,
      'total_questions': 2,
      'average_response_seconds': 9,
      'final_difficulty': 1,
      'difficulty_path': [3, 4, 1],
    };
  }

  @override
  Future<List<AttemptHistoryItem>> getAttemptHistory(
    SessionState session, {
    int? courseId,
  }) async {
    return const [
      AttemptHistoryItem(
        attemptId: 77,
        testId: 1,
        testTitle: 'Security Checkpoint',
        courseId: 1,
        courseTitle: 'Security Essentials',
        scorePercent: 50,
        correctAnswers: 1,
        totalQuestions: 2,
        averageResponseSeconds: 9,
        finalDifficulty: 1,
        difficultyPath: [3, 4, 1],
        weakTopics: [
          {'topic_title': 'Phishing', 'score': 3},
        ],
        recommendationCount: 1,
        startedAt: null,
        finishedAt: null,
      ),
    ];
  }

  @override
  Future<AttemptReviewPayload> getAttemptReview(
    int attemptId,
    SessionState session,
  ) async {
    return sampleAttemptReview;
  }
}

class FakeRecommendationsApiClient extends ApiClient {
  FakeRecommendationsApiClient() : super(baseUrl: sampleSession.baseUrl);

  @override
  Future<List<RecommendationInfo>> getRecommendations(
      SessionState session) async {
    return const [
      RecommendationInfo(
        priority: 1,
        text: 'Repeat the phishing lesson before the next attempt.',
        topicId: 2,
        topicTitle: 'Phishing',
        lessonId: 22,
        lessonTitle: 'Phishing signals',
        courseId: 1,
        courseTitle: 'Security Essentials',
        signalScore: 3,
        signalLevel: 'medium',
        reason: 'Phishing included incorrect or slower-than-expected answers.',
      ),
    ];
  }

  @override
  Future<LessonPlayerPayload> getLessonPlayer(
      int lessonId, SessionState session) async {
    return lessonTwo;
  }

  @override
  Future<List<AttemptHistoryItem>> getAttemptHistory(
    SessionState session, {
    int? courseId,
  }) async {
    return const [
      AttemptHistoryItem(
        attemptId: 77,
        testId: 1,
        testTitle: 'Security Checkpoint',
        courseId: 1,
        courseTitle: 'Security Essentials',
        scorePercent: 50,
        correctAnswers: 1,
        totalQuestions: 2,
        averageResponseSeconds: 9,
        finalDifficulty: 1,
        difficultyPath: [3, 4, 1],
        weakTopics: [
          {'topic_title': 'Phishing', 'score': 3},
        ],
        recommendationCount: 1,
        startedAt: null,
        finishedAt: null,
      ),
    ];
  }

  @override
  Future<AttemptReviewPayload> getAttemptReview(
    int attemptId,
    SessionState session,
  ) async {
    return sampleAttemptReview;
  }
}

double overlayOpacity(WidgetTester tester) {
  final widget = tester.widget<AnimatedOpacity>(
    find.byKey(const ValueKey('video-overlay-opacity')).first,
  );
  return widget.opacity;
}

String videoTimeLabel(WidgetTester tester) {
  final widget = tester.widget<Text>(
    find.byKey(const ValueKey('video-time-label')).first,
  );
  return widget.data ?? '';
}

Future<void> tapVideoSurface(WidgetTester tester) async {
  final surface = find.byKey(const ValueKey('video-surface')).first;
  final rect = tester.getRect(surface);
  await tester.tapAt(Offset(rect.left + 28, rect.bottom - 28));
}

Future<void> doubleTapFullscreenSurface(WidgetTester tester) async {
  final surface = find.byKey(const ValueKey('video-surface')).first;
  final rect = tester.getRect(surface);
  final point = Offset(rect.right - 72, rect.top + rect.height * 0.28);
  await tester.tapAt(point);
  await tester.pump(const Duration(milliseconds: 80));
  await tester.tapAt(point);
}

Future<void> configureViewport(WidgetTester tester) async {
  tester.view.physicalSize = const Size(1440, 2600);
  tester.view.devicePixelRatio = 1;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

void main() {
  SharedPreferences.setMockInitialValues({});
  FlutterSecureStorage.setMockInitialValues({});

  testWidgets('renders login title', (tester) async {
    await tester.pumpWidget(const CoursumApp());
    await tester.pumpAndSettle();
    expect(find.bySemanticsLabel('Coursum'), findsOneWidget);
  });

  testWidgets('course overview resumes the current lesson', (tester) async {
    await configureViewport(tester);
    int? openedLessonId;
    var startedTest = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CourseOverviewBody(
            session: sampleSession,
            course: const CourseInfo(
              id: 1,
              title: 'Security Essentials',
              description: 'A sample course for the mobile player.',
              imageUrl: 'https://cdn.example.com/course-cover.jpg',
            ),
            outline: sampleOutline(currentLessonId: 1),
            testCount: 1,
            onOpenLesson: (lessonId) => openedLessonId = lessonId,
            onStartTest: () => startedTest = true,
            onViewAttemptHistory: () {},
          ),
        ),
      ),
    );

    await tester.tap(find.byKey(const ValueKey('resume-course-button')));
    await tester.pump();

    expect(openedLessonId, 1);
    await tester.tap(find.text('Начать адаптивный тест'));
    await tester.pump();
    expect(startedTest, isTrue);
  });

  testWidgets(
      'course player navigates between pages and highlights current position',
      (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
        CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}));

    expect(find.text('Why password managers matter'), findsOneWidget);
    await tester.tap(find.text('Содержание'));
    await tester.pumpAndSettle();
    expect(find.text('Текущий урок'), findsOneWidget);
    expect(find.text('Текущая страница'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('outline-page-page-2')));
    await tester.pumpAndSettle();
    expect(find.text('Daily habits'), findsOneWidget);

    await tester.tap(find.text('Содержание'));
    await tester.pumpAndSettle();
    expect(find.text('Текущая страница'), findsOneWidget);
    expect(find.byIcon(Icons.check), findsAtLeastNWidgets(1));
  });

  testWidgets('next lesson is shown only on the last page and opens from there',
      (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
        CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}));

    expect(find.text('Password managers'), findsAtLeastNWidgets(1));
    expect(find.byKey(const ValueKey('lesson-transition-card')), findsNothing);

    await tester.tap(find.byKey(const ValueKey('next-page-button')));
    await tester.pumpAndSettle();

    expect(
        find.byKey(const ValueKey('lesson-transition-card')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('next-page-button')));
    await tester.pumpAndSettle();

    expect(find.text('Phishing signals'), findsAtLeastNWidgets(1));
    expect(find.text('Pause before you click'), findsOneWidget);
  });

  testWidgets('embedded video is rendered inline inside the lesson page',
      (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      CoursePlayerHarness(
        payloads: {1: lessonOne, 2: lessonTwo},
        videoPreviewModes: const {
          'https://cdn.example.com/passwords.mp4':
              InlineVideoPreviewMode.embedded
        },
      ),
    );

    expect(find.byKey(const ValueKey('embedded-video')), findsOneWidget);
  });

  testWidgets('html lesson blocks render headings and code content',
      (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(CoursePlayerHarness(payloads: {3: htmlLesson}));

    expect(find.text('Checklist'), findsOneWidget);
    expect(find.textContaining('approved'), findsOneWidget);
    expect(find.textContaining('Download notes'), findsOneWidget);
    expect(find.textContaining('конспектом'), findsOneWidget);
    expect(find.textContaining('Open handout'), findsOneWidget);
    expect(richTextHasTapRecognizer(tester, 'Download notes'), isTrue);
    expect(richTextHasTapRecognizer(tester, 'конспектом'), isTrue);
    expect(richTextHasTapRecognizer(tester, 'Open handout'), isTrue);
    expect(richTextPlainTextContains(tester, 'с конспектом'), isTrue);
    expect(find.textContaining('Subject: Update request'), findsOneWidget);
  });

  testWidgets('video player enters and exits fullscreen', (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}),
    );

    await tester.tap(find.byKey(const ValueKey('enter-fullscreen-button')));
    await tester.pumpAndSettle();
    expect(
        find.byKey(const ValueKey('fullscreen-video-screen')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('exit-fullscreen-button')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('fullscreen-video-screen')), findsNothing);
  });

  testWidgets('fullscreen defaults to contain fit mode', (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}),
    );

    await tester.tap(find.byKey(const ValueKey('enter-fullscreen-button')));
    await tester.pumpAndSettle();

    expect(
      find.descendant(
        of: find.byKey(const ValueKey('fullscreen-video-screen')),
        matching: find.byKey(const ValueKey('video-fit-contain')),
      ),
      findsOneWidget,
    );
  });

  testWidgets('fullscreen fit toggle switches between contain and cover',
      (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}),
    );

    await tester.tap(find.byKey(const ValueKey('enter-fullscreen-button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('fit-toggle-button')));
    await tester.pumpAndSettle();

    expect(
      find.descendant(
        of: find.byKey(const ValueKey('fullscreen-video-screen')),
        matching: find.byKey(const ValueKey('video-fit-cover')),
      ),
      findsOneWidget,
    );
  });

  testWidgets('fullscreen quick zoom can be toggled and reset', (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}),
    );

    await tester.tap(find.byKey(const ValueKey('enter-fullscreen-button')));
    await tester.pumpAndSettle();

    await doubleTapFullscreenSurface(tester);
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('video-zoom-label')), findsOneWidget);
    expect(find.byKey(const ValueKey('reset-zoom-button')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('reset-zoom-button')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('video-zoom-label')), findsNothing);
    expect(find.byKey(const ValueKey('reset-zoom-button')), findsNothing);
  });

  testWidgets('tap toggles player overlays', (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}),
    );

    expect(overlayOpacity(tester), 1);

    await tapVideoSurface(tester);
    await tester.pump(const Duration(milliseconds: 220));
    expect(overlayOpacity(tester), 0);

    await tapVideoSurface(tester);
    await tester.pump(const Duration(milliseconds: 220));
    expect(overlayOpacity(tester), 1);
  });

  testWidgets('controls auto-hide while video is playing', (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}),
    );

    await tester.tap(find.byKey(const ValueKey('play-pause-button')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 4));

    expect(overlayOpacity(tester), 0);
  });

  testWidgets('controls remain visible while paused', (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}),
    );

    await tester.tap(find.byKey(const ValueKey('play-pause-button')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    await tester.tap(find.byKey(const ValueKey('play-pause-button')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 4));

    expect(overlayOpacity(tester), 1);
  });

  testWidgets('playback and seek controls still work after overlay toggling',
      (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      CoursePlayerHarness(payloads: {1: lessonOne, 2: lessonTwo}),
    );

    await tester.tap(find.byKey(const ValueKey('play-pause-button')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));

    await tapVideoSurface(tester);
    await tester.pump(const Duration(milliseconds: 220));
    await tapVideoSurface(tester);
    await tester.pump(const Duration(milliseconds: 220));

    await tester.tap(find.byKey(const ValueKey('forward-10-button')));
    await tester.pump();

    expect(
      videoTimeLabel(tester),
      anyOf(startsWith('00:12 / 00:13'), startsWith('00:13 / 00:13')),
    );
  });

  testWidgets(
      'adaptive test progresses through questions and shows result summary',
      (tester) async {
    await configureViewport(tester);
    final api = FakeAdaptiveApiClient();
    final previousLanguage = AppLanguageRuntime.language;
    AppLanguageRuntime.language = AppLanguage.en;
    addTearDown(() => AppLanguageRuntime.language = previousLanguage);

    await tester.pumpWidget(
      MaterialApp(
        home: TestFlowScreen(api: api, session: sampleSession, testId: 1),
      ),
    );

    await tester.tap(find.text('Start test'));
    await tester.pumpAndSettle();

    expect(find.text('Question 1 of 2'), findsOneWidget);
    expect(find.text('Which practice keeps account access safer?'),
        findsOneWidget);

    await tester.tap(find.text('Use the approved password manager'));
    await tester.pump();
    await tester.tap(find.text('Submit answer'));
    await tester.pumpAndSettle();

    expect(find.text('Correct'), findsOneWidget);
    expect(
        find.textContaining('Target difficulty: 3/5 -> 4/5'), findsOneWidget);
    expect(find.text('Next question will be level 2/5'), findsOneWidget);

    await tester.tap(find.text('Next question'));
    await tester.pumpAndSettle();

    expect(find.text('Question 2 of 2'), findsOneWidget);
    expect(find.text('How should you respond to a suspicious email?'),
        findsOneWidget);

    await tester.tap(find.text('Forward it to colleagues for opinions'));
    await tester.pump();
    await tester.tap(find.text('Submit answer'));
    await tester.pumpAndSettle();

    expect(find.text('Needs review'), findsOneWidget);
    await tester.tap(find.text('Finish test'));
    await tester.pumpAndSettle();

    expect(find.text('Score: 50%'), findsOneWidget);
    expect(find.text('Correct answers: 1 of 2'), findsOneWidget);
    expect(find.textContaining('Repeat the phishing lesson'), findsOneWidget);
    expect(api.capturedResponseSeconds, everyElement(greaterThanOrEqualTo(1)));
  });

  testWidgets('attempt history opens from adaptive test result',
      (tester) async {
    await configureViewport(tester);
    final api = FakeAdaptiveApiClient();
    final previousLanguage = AppLanguageRuntime.language;
    AppLanguageRuntime.language = AppLanguage.en;
    addTearDown(() => AppLanguageRuntime.language = previousLanguage);

    await tester.pumpWidget(
      MaterialApp(
        home: TestFlowScreen(api: api, session: sampleSession, testId: 1),
      ),
    );

    await tester.tap(find.text('Start test'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Use the approved password manager'));
    await tester.pump();
    await tester.tap(find.text('Submit answer'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Next question'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Forward it to colleagues for opinions'));
    await tester.pump();
    await tester.tap(find.text('Submit answer'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Finish test'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('attempt-history-button')));
    await tester.pumpAndSettle();

    expect(find.text('Security Checkpoint'), findsOneWidget);
    expect(find.text('Phishing'), findsOneWidget);
  });

  testWidgets('invalid video sources show an in-app fallback state',
      (tester) async {
    await configureViewport(tester);
    final invalidPayload = buildPayload(
      lessonId: 1,
      lessonTitle: 'Invalid video lesson',
      previousLessonId: null,
      nextLessonId: null,
      pages: const [
        LessonPageData(
          pageId: 'page-error',
          chapterTitle: 'Context',
          pageTitle: 'Unsupported media',
          blocks: [
            LessonBlockData(
              type: 'video',
              url: 'https://cdn.example.com/bad-source',
              title: 'Broken video',
              status: 'invalid',
              error: 'Unsupported video source',
            ),
          ],
        ),
      ],
    );

    await tester.pumpWidget(CoursePlayerHarness(payloads: {1: invalidPayload}));

    expect(find.byKey(const ValueKey('video-error-message')), findsOneWidget);
    expect(find.text('Unsupported video source'), findsOneWidget);
  });

  testWidgets('recommendations screen explains what to review and why',
      (tester) async {
    await configureViewport(tester);
    final previousLanguage = AppLanguageRuntime.language;
    AppLanguageRuntime.language = AppLanguage.en;
    addTearDown(() => AppLanguageRuntime.language = previousLanguage);

    await tester.pumpWidget(
      MaterialApp(
        home: RecommendationsScreen(
          api: FakeRecommendationsApiClient(),
          session: sampleSession,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Phishing'), findsOneWidget);
    expect(find.textContaining('Security Essentials'), findsOneWidget);
    expect(find.text('Why this is recommended'), findsOneWidget);
    expect(find.textContaining('slower-than-expected answers'), findsOneWidget);
    expect(find.text('Recommended action'), findsOneWidget);
  });

  testWidgets('attempt history screen renders completed attempts',
      (tester) async {
    await configureViewport(tester);
    final previousLanguage = AppLanguageRuntime.language;
    AppLanguageRuntime.language = AppLanguage.en;
    addTearDown(() => AppLanguageRuntime.language = previousLanguage);

    await tester.pumpWidget(
      MaterialApp(
        home: AttemptHistoryScreen(
          api: FakeRecommendationsApiClient(),
          session: sampleSession,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Security Checkpoint'), findsOneWidget);
    expect(find.text('Security Essentials'), findsOneWidget);
    expect(find.textContaining('Correct answers: 1 of 2'), findsOneWidget);
  });

  testWidgets('tapping an attempt opens the detailed review screen',
      (tester) async {
    await configureViewport(tester);
    final previousLanguage = AppLanguageRuntime.language;
    AppLanguageRuntime.language = AppLanguage.en;
    addTearDown(() => AppLanguageRuntime.language = previousLanguage);

    await tester.pumpWidget(
      MaterialApp(
        home: AttemptHistoryScreen(
          api: FakeRecommendationsApiClient(),
          session: sampleSession,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('attempt-history-card-77')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('attempt-review-screen')), findsOneWidget);
    expect(find.text('Review: Security Checkpoint'), findsOneWidget);
    expect(find.text('Which practice keeps account access safer?'),
        findsOneWidget);
    expect(find.text('Your answer: Forward it to colleagues for opinions'),
        findsOneWidget);
    expect(find.text('Correct answer: Report it through the approved channel'),
        findsOneWidget);
  });

  testWidgets('tapping a recommendation opens the linked lesson',
      (tester) async {
    await configureViewport(tester);
    final previousLanguage = AppLanguageRuntime.language;
    AppLanguageRuntime.language = AppLanguage.en;
    addTearDown(() => AppLanguageRuntime.language = previousLanguage);

    await tester.pumpWidget(
      MaterialApp(
        home: RecommendationsScreen(
          api: FakeRecommendationsApiClient(),
          session: sampleSession,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Open lesson'));
    await tester.pumpAndSettle();

    expect(find.text('Phishing signals'), findsAtLeastNWidgets(1));
    expect(find.text('Pause before you click'), findsOneWidget);
  });
}
