import 'package:flutter/material.dart';

enum AppLanguage { ru, en }

extension AppLanguageCodec on AppLanguage {
  String get code => switch (this) {
        AppLanguage.ru => 'ru',
        AppLanguage.en => 'en',
      };

  String get settingsLabel => switch (this) {
        AppLanguage.ru => 'Русский',
        AppLanguage.en => 'English',
      };

  static AppLanguage fromCode(String? value) {
    return switch (value) {
      'en' => AppLanguage.en,
      _ => AppLanguage.ru,
    };
  }
}

class AppLanguageRuntime {
  static AppLanguage language = AppLanguage.ru;

  static AppStrings get strings => AppStrings(language);
}

class AppLanguageController extends ChangeNotifier {
  AppLanguageController(this._language) {
    AppLanguageRuntime.language = _language;
  }

  AppLanguage _language;

  AppLanguage get language => _language;

  void setLanguage(AppLanguage nextLanguage) {
    if (_language == nextLanguage) {
      return;
    }
    _language = nextLanguage;
    AppLanguageRuntime.language = nextLanguage;
    notifyListeners();
  }
}

class AppLocalizationScope extends InheritedNotifier<AppLanguageController> {
  const AppLocalizationScope({
    super.key,
    required this.controller,
    required this.onLanguageChanged,
    required super.child,
  }) : super(notifier: controller);

  final AppLanguageController controller;
  final Future<void> Function(AppLanguage language) onLanguageChanged;

  AppStrings get strings => AppStrings(controller.language);

  static AppLocalizationScope? maybeOf(BuildContext context) {
    return context.dependOnInheritedWidgetOfExactType<AppLocalizationScope>();
  }
}

extension AppLocalizationBuildContext on BuildContext {
  AppStrings get strings =>
      AppLocalizationScope.maybeOf(this)?.strings ?? AppLanguageRuntime.strings;

  AppLanguage get currentAppLanguage =>
      AppLocalizationScope.maybeOf(this)?.controller.language ??
      AppLanguageRuntime.language;

  Future<void> setAppLanguage(AppLanguage language) async {
    final scope = AppLocalizationScope.maybeOf(this);
    if (scope == null) {
      AppLanguageRuntime.language = language;
      return;
    }
    await scope.onLanguageChanged(language);
  }
}

class AppStrings {
  const AppStrings(this.language);

  final AppLanguage language;

  bool get isRu => language == AppLanguage.ru;

  String durationMinutes(int minutes) {
    final safeMinutes = minutes <= 0 ? 5 : minutes;
    return isRu ? '$safeMinutes мин' : '$safeMinutes min';
  }

  String get appTitle => 'Coursum';
  String get courseFallback => isRu ? 'Курс' : 'Course';
  String get lessonFallback => isRu ? 'Урок' : 'Lesson';
  String get assignmentFallback =>
      isRu ? 'Практическое задание' : 'Practical assignment';
  String assignmentStatusLabel(String? rawStatus) {
    final normalized = (rawStatus ?? '').trim().toLowerCase();
    return switch (normalized) {
      'submitted' || 'pending_review' || 'in_review' =>
        (isRu ? 'Отправлено' : 'Submitted'),
      'approved' || 'accepted' => (isRu ? 'Принято' : 'Approved'),
      'rejected' || 'needs_revision' || 'revision_requested' =>
        (isRu ? 'Нужна доработка' : 'Needs revision'),
      'draft' => (isRu ? 'Черновик' : 'Draft'),
      'not_started' || '' => (isRu ? 'Не начато' : 'Not started'),
      _ => isRu ? 'Не начато' : 'Not started',
    };
  }
  String get pageFallback => isRu ? 'Страница' : 'Page';
  String get loginSubtitle => isRu
      ? 'Войдите в Coursum и продолжите назначенные курсы.'
      : 'Sign in to Coursum and continue your assigned courses.';
  String get email => isRu ? 'Эл. почта' : 'Email';
  String get password => isRu ? 'Пароль' : 'Password';
  String get tenantCode => isRu ? 'Код организации' : 'Tenant code';
  String get backendUrl => isRu ? 'URL backend' : 'Backend URL';
  String get rememberCredentials =>
      isRu ? 'Запомнить логин и пароль' : 'Remember login and password';
  String get savedAccountsTitle => isRu ? 'Выберите аккаунт' : 'Choose account';
  String get savedAccountsHint => isRu
      ? 'Нажмите на поле почты или организации, чтобы выбрать сохраненный аккаунт.'
      : 'Tap email or organization field to choose a saved account.';
  String get savedAccountsEmpty =>
      isRu ? 'Сохраненных аккаунтов пока нет.' : 'No saved accounts yet.';
  String savedAccountUseSingle(String login, String organizationCode) => isRu
      ? 'Использовать: $login ($organizationCode)'
      : 'Use: $login ($organizationCode)';
  String savedAccountRow(String login, String organizationCode) =>
      '$login ($organizationCode)';
  String get savedAccountDelete => isRu ? 'Удалить аккаунт' : 'Delete account';
  String savedAccountDeleteConfirm(String login) => isRu
      ? 'Удалить сохраненный аккаунт $login?'
      : 'Delete saved account $login?';
  String get savedAccountsDeleteAll =>
      isRu ? 'Удалить все аккаунты' : 'Delete all accounts';
  String get savedAccountsDeleteAllConfirm => isRu
      ? 'Удалить все сохраненные аккаунты с устройства?'
      : 'Delete all saved accounts from this device?';
  String get cancelAction => isRu ? 'Отмена' : 'Cancel';
  String get deleteAction => isRu ? 'Удалить' : 'Delete';
  String get loginFieldsRequired => isRu
      ? 'Введите почту, пароль и код организации.'
      : 'Enter email, password, and tenant code.';
  String get signIn => isRu ? 'Войти' : 'Sign in';
  String get signingIn => isRu ? 'Входим...' : 'Signing in...';
  String get languageRussian => 'Русский';
  String get languageEnglish => 'English';
  String get organizationContactTitle => isRu
      ? 'Хотите подключить организацию?'
      : 'Want to connect your organization?';
  String get organizationContactBody => isRu
      ? 'Напишите нам, и мы обсудим пилот, доступы и настройку курсов.'
      : 'Contact us to discuss a pilot, access setup, and course configuration.';
  String get organizationContactAction =>
      isRu ? 'Связаться по сотрудничеству' : 'Contact us for partnership';
  String get organizationContactEmailSubject => isRu
      ? 'Заявка на подключение Coursum'
      : 'Coursum organization onboarding request';
  String get organizationContactEmailBody => isRu
      ? 'Здравствуйте! Хотим обсудить подключение организации к Coursum.\n\nОрганизация:\nКонтактное лицо:\nТелефон/Telegram:\nКоличество учеников:\n'
      : 'Hello! We would like to discuss connecting our organization to Coursum.\n\nOrganization:\nContact person:\nPhone/Telegram:\nLearner count:\n';
  String get organizationContactOpenFailed => isRu
      ? 'Не удалось открыть почтовое приложение. Напишите нам: partnership@coursum.online'
      : 'Could not open the mail app. Email us: partnership@coursum.online';

  String tenantWithCode(String code) =>
      isRu ? 'Организация: $code' : 'Tenant: $code';

  String get coursesTab => isRu ? 'Курсы' : 'Courses';
  String get recommendationsTab => isRu ? 'Рекомендации' : 'Recommendations';
  String get profileTab => isRu ? 'Профиль' : 'Profile';

  String coursesLoadFailed(String error) => isRu
      ? 'Не удалось загрузить курсы.\n$error'
      : 'Courses failed to load.\n$error';
  String get noAssignedCourses =>
      isRu ? 'Пока нет назначенных курсов.' : 'No assigned courses yet.';
  String courseOutlineLoadFailed(String error) => isRu
      ? 'Не удалось загрузить структуру курса.\n$error'
      : 'Course outline failed to load.\n$error';
  String lessonsCompleted(int completed, int total) => isRu
      ? '$completed/$total уроков завершено'
      : '$completed/$total lessons completed';
  String progressPercent(int percent) =>
      isRu ? 'Прогресс $percent%' : 'Progress $percent%';
  String adaptiveTestsCount(int count) =>
      isRu ? '$count адаптивный тест' : '$count adaptive test';
  String get resumeCourse => isRu ? 'Продолжить курс' : 'Resume course';
  String get startAdaptiveTest =>
      isRu ? 'Начать адаптивный тест' : 'Start adaptive test';
  String get lessonOutline => isRu ? 'Структура курса' : 'Lesson outline';
  String pagesCount(int count) => isRu ? '$count стр.' : '$count pages';
  String pagesWithDuration(int pages, String duration) =>
      isRu ? '$duration • $pages стр.' : '$duration • $pages pages';
  String get coursePlayer => isRu ? 'Плеер курса' : 'Course player';
  String lessonPlayerLoadFailed(String error) => isRu
      ? 'Не удалось загрузить урок.\n$error'
      : 'Lesson player failed to load.\n$error';
  String get noPagesYet => isRu
      ? 'В этом уроке пока нет страниц.'
      : 'This lesson does not contain any pages yet.';
  String pageOf(int current, int total) =>
      isRu ? 'Страница $current из $total' : 'Page $current of $total';
  String pagesCompleted(int count) =>
      isRu ? '$count страниц пройдено' : '$count pages completed';
  String get contents => isRu ? 'Содержание' : 'Contents';
  String get previousLesson => isRu ? 'Предыдущий урок' : 'Previous lesson';
  String get nextLesson => isRu ? 'Следующий урок' : 'Next lesson';
  String get previousPage => isRu ? 'Предыдущая страница' : 'Previous page';
  String get nextPage => isRu ? 'Следующая страница' : 'Next page';
  String get lastPageReached => isRu
      ? 'Это последняя страница урока'
      : 'This is the last page of the lesson';
  String openNextLesson(String lessonTitle) => isRu
      ? 'Открыть следующий урок: $lessonTitle'
      : 'Open next lesson: $lessonTitle';
  String get nextLessonAvailable => isRu
      ? 'Дальше откроется следующий урок.'
      : 'The next lesson will open after this page.';
  String get noMoreLessons => isRu
      ? 'Это финал урока в курсе.'
      : 'This is the final lesson in the course.';
  String get completeLesson => isRu ? 'Завершить урок' : 'Complete lesson';
  String get markLessonComplete =>
      isRu ? 'Отметить урок завершенным' : 'Mark lesson complete';
  String get lessonCompleted => isRu ? 'Урок завершен' : 'Lesson completed';

  String get adaptiveTest => isRu ? 'Адаптивный тест' : 'Adaptive test';
  String get linkOpenFailed => isRu
      ? 'РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РєСЂС‹С‚СЊ СЃСЃС‹Р»РєСѓ.'
      : 'Could not open the link.';
  String get testIntro => isRu
      ? 'Используйте тест, чтобы проверить понимание после изучения уроков.'
      : 'Use the test to validate understanding after studying the lesson sequence.';
  String get loadQuestion => isRu ? 'Загрузить вопрос' : 'Load question';
  String get questionFallback => isRu ? 'Вопрос' : 'Question';
  String get optionFallback => isRu ? 'Вариант' : 'Option';
  String get submitAnswer => isRu ? 'Отправить ответ' : 'Submit answer';
  String get correctAnswerDifficultyIncreased => isRu
      ? 'Ответ верный. Сложность повышена.'
      : 'Correct answer. Difficulty increased.';
  String get incorrectAnswerDifficultyDecreased => isRu
      ? 'Ответ неверный. Сложность понижена.'
      : 'Incorrect answer. Difficulty decreased.';
  String scorePercent(int score) =>
      isRu ? 'Результат: $score%' : 'Score: $score%';
  String recommendationsCount(int count) =>
      isRu ? 'Рекомендации: $count' : 'Recommendations: $count';
  String weakTopics(String topics) =>
      isRu ? 'Слабые темы: $topics' : 'Weak topics: $topics';

  String get adaptiveTestIntroDetail => isRu
      ? 'Адаптивность подстраивает сложность вопроса после каждого ответа и помогает быстро найти темы для повторения.'
      : 'Adaptive difficulty adjusts the next question after every answer and helps surface the topics that need review.';
  String get startTest => isRu ? 'Начать тест' : 'Start test';
  String get loadingQuestion =>
      isRu ? 'Загружаем следующий вопрос...' : 'Loading the next question...';
  String questionProgress(int current, int total) =>
      isRu ? 'Вопрос $current из $total' : 'Question $current of $total';
  String get topicsLabel => isRu ? 'Темы' : 'Topics';
  String adaptiveDifficulty(int level) =>
      isRu ? 'Целевая сложность: $level/5' : 'Target difficulty: $level/5';
  String questionDifficulty(int level) =>
      isRu ? 'Сложность вопроса: $level/5' : 'Question difficulty: $level/5';
  String estimatedTimeSeconds(int seconds) => isRu
      ? 'Ожидаемое время: ${seconds.clamp(1, 999)} с'
      : 'Expected time: ${seconds.clamp(1, 999)}s';
  String testLevelLabel(int level) =>
      isRu ? 'Уровень теста: $level/5' : 'Test level: $level/5';
  String currentQuestionLevelLabel(int level) =>
      isRu ? 'Уровень этого вопроса: $level/5' : 'This question: $level/5';
  String get adaptiveDifficultyHint => isRu
      ? 'Уровень теста показывает, на каком уровне сейчас подбираются вопросы. Уровень вопроса относится именно к текущему вопросу.'
      : 'Test level shows the difficulty the engine is currently aiming for. This question describes the difficulty of the item you are answering now.';
  String get selectAnswerPrompt => isRu
      ? 'Выберите один вариант, чтобы продолжить.'
      : 'Select one answer to continue.';
  String get nextQuestion => isRu ? 'Следующий вопрос' : 'Next question';
  String get finishTest => isRu ? 'Завершить тест' : 'Finish test';
  String get answerExplanation => isRu ? 'Пояснение' : 'Explanation';
  String correctAnswerLabel(String answer) =>
      isRu ? 'Правильный ответ: $answer' : 'Correct answer: $answer';
  String get answerWasCorrect => isRu ? 'Верно' : 'Correct';
  String get answerWasIncorrect => isRu ? 'Есть ошибка' : 'Needs review';
  String difficultyShift(int previous, int current) => isRu
      ? 'Сложность: $previous/5 -> $current/5'
      : 'Difficulty: $previous/5 -> $current/5';
  String correctAnswersCount(int correct, int total) => isRu
      ? 'Верных ответов: $correct из $total'
      : 'Correct answers: $correct of $total';
  String averageResponseTime(int seconds) => isRu
      ? 'Среднее время ответа: ${seconds.clamp(0, 999)} с'
      : 'Average response time: ${seconds.clamp(0, 999)}s';
  String finalDifficulty(int level) =>
      isRu ? 'Финальная сложность: $level/5' : 'Final difficulty: $level/5';
  String difficultyPath(List<int> path) => isRu
      ? 'Как менялась сложность: ${path.join(" -> ")}'
      : 'Difficulty progression: ${path.join(" -> ")}';
  String get generatedRecommendations =>
      isRu ? 'Что повторить' : 'Recommended follow-up';
  String get noWeakTopics => isRu
      ? 'Явных слабых тем не собралось.'
      : 'No clear weak topics were detected.';
  String get nextQuestionUnavailable => isRu
      ? 'Следующий вопрос пока недоступен.'
      : 'The next question is not available yet.';

  String recommendationsLoadFailed(String error) => isRu
      ? 'Не удалось загрузить рекомендации.\n$error'
      : 'Recommendations failed to load.\n$error';
  String get noRecommendationsYet => isRu
      ? 'Пока нет рекомендаций. Пройдите тест по курсу, чтобы получить советы для повторения.'
      : 'No recommendations yet. Complete a course test to generate revision guidance.';

  String tenantLabel(String tenantName) =>
      isRu ? 'Организация: $tenantName' : 'Organization: $tenantName';
  String tenantCodeValue(String tenantCode) =>
      isRu ? 'Код организации: $tenantCode' : 'Organization code: $tenantCode';
  String apiLabel(String baseUrl) => isRu ? 'API: $baseUrl' : 'API: $baseUrl';
  String get logout => isRu ? 'Выйти' : 'Logout';
  String get settings => isRu ? 'Настройки' : 'Settings';
  String get interfaceLanguage =>
      isRu ? 'Язык интерфейса' : 'Interface language';
  String get retry => isRu ? 'Повторить' : 'Retry';

  String get courseContents => isRu ? 'Содержание курса' : 'Course contents';
  String get lessons => isRu ? 'Уроки' : 'Lessons';
  String get pagesInLesson =>
      isRu ? 'Страницы этого урока' : 'Pages in this lesson';
  String get currentLesson => isRu ? 'Текущий урок' : 'Current lesson';
  String get currentPage => isRu ? 'Текущая страница' : 'Current page';

  String get imageUnavailable =>
      isRu ? 'Изображение недоступно' : 'Image unavailable';
  String get lessonVideo => isRu ? 'Видео урока' : 'Lesson video';

  String get openFullscreen =>
      isRu ? 'Открыть на весь экран' : 'Open fullscreen';
  String get exitFullscreen =>
      isRu ? 'Выйти из полноэкранного режима' : 'Exit fullscreen';
  String get zoomToFill => isRu ? 'Увеличить до заполнения' : 'Zoom to fill';
  String get fitInsideScreen => isRu ? 'Уместить в экран' : 'Fit inside screen';
  String get playVideo => isRu ? 'Воспроизвести' : 'Play video';
  String get pauseVideo => isRu ? 'Пауза' : 'Pause video';
  String get replayTenSeconds =>
      isRu ? 'Назад на 10 секунд' : 'Replay 10 seconds';
  String get skipForwardTenSeconds =>
      isRu ? 'Вперед на 10 секунд' : 'Skip forward 10 seconds';
  String get resetZoom => isRu ? 'Сбросить масштаб' : 'Reset zoom';

  String get unsupportedVideoSource =>
      isRu ? 'Неподдерживаемый источник видео' : 'Unsupported video source';
  String get invalidVideoUrl =>
      isRu ? 'Некорректный URL видео' : 'Invalid video URL';
  String videoCouldNotBeLoaded([String? details]) {
    if (details == null || details.isEmpty) {
      return isRu
          ? 'Видео не удалось загрузить.'
          : 'Video could not be loaded.';
    }
    return isRu
        ? 'Видео не удалось загрузить: $details'
        : 'Video could not be loaded: $details';
  }

  String get interactivePreviewSurface => isRu
      ? 'Интерактивная область предпросмотра'
      : 'Interactive preview surface';

  String get requestTimedOut => isRu
      ? 'Время ожидания истекло. Проверьте URL backend и доступ по локальной сети.'
      : 'Request timed out. Check backend URL and local network access.';
  String get requestFailed =>
      isRu ? 'Запрос завершился ошибкой' : 'Request failed';
}
