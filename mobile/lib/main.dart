import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show defaultTargetPlatform, kDebugMode;
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import 'app_localization.dart';
import 'player/lesson_video_player.dart';
import 'widgets/lesson_html_block.dart';
import 'widgets/lesson_media_frame.dart';

export 'player/lesson_video_player.dart';

void main() {
  runApp(const CoursumApp());
}

Map<String, dynamic> jsonMap(dynamic value) =>
    Map<String, dynamic>.from(value as Map);

List<Map<String, dynamic>> jsonList(dynamic value) {
  final items = value as List<dynamic>? ?? const [];
  return items.map((item) => Map<String, dynamic>.from(item as Map)).toList();
}

String normalizeTenantCode(String value) => value.trim().toLowerCase();
String normalizeLogin(String value) => value.trim().toLowerCase();

String formatDurationLabel(int minutes) =>
    AppLanguageRuntime.strings.durationMinutes(minutes);

String formatSecondsClock(int seconds) {
  final safeSeconds = seconds.clamp(0, 35999);
  final minutes = (safeSeconds ~/ 60).toString().padLeft(2, '0');
  final remainder = (safeSeconds % 60).toString().padLeft(2, '0');
  return '$minutes:$remainder';
}

TextStyle courseCardTitleStyle(BuildContext context) =>
    Theme.of(context).textTheme.headlineSmall?.copyWith(
      fontSize: 22,
      fontWeight: FontWeight.w700,
      height: 1.18,
      letterSpacing: 0,
      wordSpacing: 0,
      fontFeatures: const [],
    ) ??
    const TextStyle(
      fontSize: 22,
      fontWeight: FontWeight.w700,
      height: 1.18,
      letterSpacing: 0,
      wordSpacing: 0,
    );

const _mediaCacheVersion = '20260407-course-covers';
const _enableDevAuthPrefill =
    bool.fromEnvironment('ENABLE_DEV_AUTH_PREFILL', defaultValue: false);
const _devLoginEmail = String.fromEnvironment('DEV_LOGIN_EMAIL');
const _devLoginPassword = String.fromEnvironment('DEV_LOGIN_PASSWORD');
const _devTenantCode = String.fromEnvironment('DEV_TENANT_CODE');

String recommendationIntro(AppStrings strings) => strings.isRu
    ? 'Здесь собраны темы, где в адаптивных тестах было больше ошибок или медленных ответов. Откройте нужный урок и повторите материал перед следующей попыткой.'
    : 'This list highlights topics with more incorrect or slower answers in adaptive tests. Open the linked lesson and review the material before the next attempt.';

String recommendationPriorityLabel(AppStrings strings, int priority) {
  if (strings.isRu) {
    if (priority <= 1) return 'Сначала';
    if (priority == 2) return 'Далее';
    return 'Потом';
  }
  if (priority <= 1) return 'Start here';
  if (priority == 2) return 'Next';
  return 'Later';
}

String recommendationLevelLabel(AppStrings strings, String signalLevel) {
  switch (signalLevel) {
    case 'high':
      return strings.isRu ? 'Высокий приоритет' : 'High priority';
    case 'medium':
      return strings.isRu ? 'Средний приоритет' : 'Medium priority';
    default:
      return strings.isRu ? 'Низкий приоритет' : 'Low priority';
  }
}

String recommendationWhyLabel(AppStrings strings) =>
    strings.isRu ? 'Почему это рекомендовано' : 'Why this is recommended';

String recommendationActionLabel(AppStrings strings) =>
    strings.isRu ? 'Что сделать' : 'Recommended action';

String recommendationLocationLabel(AppStrings strings) =>
    strings.isRu ? 'Где повторить' : 'Where to review';

String recommendationOpenLessonLabel(AppStrings strings) =>
    strings.isRu ? 'Открыть урок' : 'Open lesson';

String recommendationOpenCourseLabel(AppStrings strings) =>
    strings.isRu ? 'Открыть курс' : 'Open course';

String recommendationUnavailableLabel(AppStrings strings) => strings.isRu
    ? 'Для этой рекомендации пока не привязан конкретный урок.'
    : 'This recommendation is not linked to a lesson yet.';

String attemptHistoryTitle(AppStrings strings, {String? courseTitle}) {
  if (courseTitle != null && courseTitle.trim().isNotEmpty) {
    return strings.isRu
        ? 'Попытки тестов: $courseTitle'
        : 'Test attempts: $courseTitle';
  }
  return strings.isRu ? 'История попыток' : 'Attempt history';
}

String attemptHistoryIntro(AppStrings strings) => strings.isRu
    ? 'Здесь показаны завершенные попытки тестов: результат, слабые темы и уровень сложности на момент завершения.'
    : 'This screen shows completed test attempts with scores, weak topics, and the final difficulty level.';

String attemptHistoryEmptyLabel(AppStrings strings) => strings.isRu
    ? 'Пока нет завершенных попыток. Пройдите адаптивный тест, и история появится здесь.'
    : 'No completed attempts yet. Finish an adaptive test and the history will appear here.';

String viewAttemptHistoryLabel(AppStrings strings) =>
    strings.isRu ? 'История попыток' : 'Attempt history';

String openAttemptHistoryFromCourseLabel(AppStrings strings) =>
    strings.isRu ? 'Попытки по курсу' : 'Course attempts';

String completedAtLabel(AppStrings strings, DateTime? value) {
  if (value == null) {
    return strings.isRu ? 'Дата неизвестна' : 'Date unavailable';
  }
  final dd = value.day.toString().padLeft(2, '0');
  final mm = value.month.toString().padLeft(2, '0');
  final yyyy = value.year.toString();
  final hh = value.hour.toString().padLeft(2, '0');
  final min = value.minute.toString().padLeft(2, '0');
  return strings.isRu
      ? 'Завершено $dd.$mm.$yyyy в $hh:$min'
      : 'Completed $yyyy-$mm-$dd at $hh:$min';
}

String attemptReviewTitle(AppStrings strings, {required String testTitle}) {
  final normalized = testTitle.trim();
  if (normalized.isEmpty) {
    return strings.isRu ? 'Разбор попытки' : 'Attempt review';
  }
  return strings.isRu ? 'Разбор: $normalized' : 'Review: $normalized';
}

String attemptReviewIntro(AppStrings strings) => strings.isRu
    ? 'Здесь собраны все вопросы завершенной попытки: что вы выбрали, какой ответ был верным и что стоит повторить перед следующим тестом.'
    : 'This view summarizes every question from the completed attempt, including your answer, the correct answer, and the follow-up explanation.';

String openAttemptReviewLabel(AppStrings strings) =>
    strings.isRu ? 'Открыть разбор' : 'Open review';

String yourAnswerLabel(AppStrings strings, String answer) =>
    strings.isRu ? 'Ваш ответ: $answer' : 'Your answer: $answer';

String noAnswerSelectedLabel(AppStrings strings) =>
    strings.isRu ? 'ответ не выбран' : 'no answer selected';

String responseTimeLabel(AppStrings strings, int seconds) => strings.isRu
    ? 'Время ответа: ${seconds.clamp(0, 999)} с'
    : 'Response time: ${seconds.clamp(0, 999)}s';

String answerOptionsLabel(AppStrings strings) =>
    strings.isRu ? 'Варианты ответа' : 'Answer choices';

String questionsInAttemptLabel(AppStrings strings, int count) => strings.isRu
    ? 'Вопросов в попытке: $count'
    : 'Questions in this attempt: $count';

class SessionState {
  const SessionState({
    required this.accessToken,
    this.refreshToken,
    required this.tenantCode,
    required this.baseUrl,
  });

  final String accessToken;
  final String? refreshToken;
  final String tenantCode;
  final String baseUrl;
}

class SavedAccount {
  const SavedAccount({
    required this.id,
    required this.organizationCode,
    required this.login,
    this.displayName,
    required this.lastUsedAt,
  });

  final String id;
  final String organizationCode;
  final String login;
  final String? displayName;
  final String lastUsedAt;

  Map<String, dynamic> toJson() => {
        'id': id,
        'organizationCode': organizationCode,
        'login': login,
        'displayName': displayName,
        'lastUsedAt': lastUsedAt,
      };

  factory SavedAccount.fromJson(Map<String, dynamic> json) {
    final organizationCode =
        normalizeTenantCode(json['organizationCode'] as String? ?? '');
    final login = normalizeLogin(json['login'] as String? ?? '');
    final id = (json['id'] as String?)?.trim().isNotEmpty == true
        ? (json['id'] as String).trim()
        : AuthStorage.accountId(organizationCode, login);
    return SavedAccount(
      id: id,
      organizationCode: organizationCode,
      login: login,
      displayName: (json['displayName'] as String?)?.trim().isNotEmpty == true
          ? (json['displayName'] as String).trim()
          : null,
      lastUsedAt: (json['lastUsedAt'] as String?)?.trim().isNotEmpty == true
          ? (json['lastUsedAt'] as String).trim()
          : DateTime.fromMillisecondsSinceEpoch(0).toIso8601String(),
    );
  }
}

class AuthStorage {
  AuthStorage({FlutterSecureStorage? secureStorage})
      : _secureStorage = secureStorage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _secureStorage;

  static const _savedAccountsKey = 'saved_accounts_v1';
  static const _rememberCredentialsKey = 'remember_credentials';
  static const _legacySavedEmailKey = 'saved_login_email';
  static const _legacySavedPasswordKey = 'saved_login_password';
  static const _legacySavedTenantCodeKey = 'saved_login_tenant_code';

  static const _activeAccessTokenKey = 'active_session_access_token';
  static const _activeRefreshTokenKey = 'active_session_refresh_token';
  static const _activeTenantCodeKey = 'active_session_tenant_code';
  static const _activeBaseUrlKey = 'active_session_base_url';

  static String accountId(String organizationCode, String login) =>
      '${normalizeTenantCode(organizationCode)}::${normalizeLogin(login)}';

  String _accountPasswordKey(String id) => 'saved_account_password::$id';

  Future<List<SavedAccount>> readSavedAccounts() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_savedAccountsKey);
    if (raw == null || raw.trim().isEmpty) {
      return const [];
    }
    try {
      final payload = jsonDecode(raw);
      if (payload is! List) {
        return const [];
      }
      final accounts = payload
          .map((item) {
            if (item is! Map) {
              return null;
            }
            return SavedAccount.fromJson(Map<String, dynamic>.from(item));
          })
          .whereType<SavedAccount>()
          .where((item) =>
              item.organizationCode.isNotEmpty && item.login.isNotEmpty)
          .toList(growable: false);
      return _sortAccounts(accounts);
    } catch (_) {
      return const [];
    }
  }

  Future<void> writeSavedAccounts(List<SavedAccount> accounts) async {
    final prefs = await SharedPreferences.getInstance();
    if (accounts.isEmpty) {
      await prefs.remove(_savedAccountsKey);
      return;
    }
    await prefs.setString(
      _savedAccountsKey,
      jsonEncode(_sortAccounts(accounts).map((item) => item.toJson()).toList()),
    );
  }

  Future<void> upsertSavedAccount(
    SavedAccount account, {
    String? password,
  }) async {
    final normalized = SavedAccount(
      id: accountId(account.organizationCode, account.login),
      organizationCode: normalizeTenantCode(account.organizationCode),
      login: normalizeLogin(account.login),
      displayName: account.displayName,
      lastUsedAt: account.lastUsedAt,
    );
    final existing = await readSavedAccounts();
    final next = [
      normalized,
      ...existing.where((item) => item.id != normalized.id),
    ];
    await writeSavedAccounts(next);
    if (password != null && password.isNotEmpty) {
      await _secureStorage.write(
        key: _accountPasswordKey(normalized.id),
        value: password,
      );
    }
  }

  Future<void> removeSavedAccount(String accountId) async {
    final existing = await readSavedAccounts();
    final next =
        existing.where((item) => item.id != accountId).toList(growable: false);
    await writeSavedAccounts(next);
    await _secureStorage.delete(key: _accountPasswordKey(accountId));
  }

  Future<void> removeAllSavedAccounts() async {
    final existing = await readSavedAccounts();
    await writeSavedAccounts(const []);
    for (final account in existing) {
      await _secureStorage.delete(key: _accountPasswordKey(account.id));
    }
  }

  Future<String?> readPassword(String accountId) {
    return _secureStorage.read(key: _accountPasswordKey(accountId));
  }

  Future<void> setRememberCredentials(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_rememberCredentialsKey, value);
  }

  Future<bool> getRememberCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_rememberCredentialsKey) ?? false;
  }

  Future<void> saveActiveSession(SessionState session) async {
    await _secureStorage.write(
        key: _activeAccessTokenKey, value: session.accessToken);
    await _secureStorage.write(
        key: _activeTenantCodeKey, value: session.tenantCode);
    await _secureStorage.write(key: _activeBaseUrlKey, value: session.baseUrl);
    if (session.refreshToken?.isNotEmpty == true) {
      await _secureStorage.write(
          key: _activeRefreshTokenKey, value: session.refreshToken);
    } else {
      await _secureStorage.delete(key: _activeRefreshTokenKey);
    }
  }

  Future<SessionState?> readActiveSession() async {
    final accessToken = await _secureStorage.read(key: _activeAccessTokenKey);
    final tenantCode = await _secureStorage.read(key: _activeTenantCodeKey);
    final baseUrl = await _secureStorage.read(key: _activeBaseUrlKey);
    if (accessToken == null ||
        accessToken.trim().isEmpty ||
        tenantCode == null ||
        tenantCode.trim().isEmpty ||
        baseUrl == null ||
        baseUrl.trim().isEmpty) {
      return null;
    }
    final refreshToken = await _secureStorage.read(key: _activeRefreshTokenKey);
    return SessionState(
      accessToken: accessToken,
      refreshToken: (refreshToken ?? '').trim().isEmpty ? null : refreshToken,
      tenantCode: normalizeTenantCode(tenantCode),
      baseUrl: baseUrl,
    );
  }

  Future<void> clearActiveSession() async {
    await _secureStorage.delete(key: _activeAccessTokenKey);
    await _secureStorage.delete(key: _activeRefreshTokenKey);
    await _secureStorage.delete(key: _activeTenantCodeKey);
    await _secureStorage.delete(key: _activeBaseUrlKey);
  }

  Future<void> migrateLegacyRememberedCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    final hadLegacyPassword = prefs.containsKey(_legacySavedPasswordKey);
    final shouldRemember = prefs.getBool(_rememberCredentialsKey) ?? false;
    final legacyEmail =
        normalizeLogin(prefs.getString(_legacySavedEmailKey) ?? '');
    final legacyTenant =
        normalizeTenantCode(prefs.getString(_legacySavedTenantCodeKey) ?? '');
    final legacyPassword = prefs.getString(_legacySavedPasswordKey) ?? '';

    if (shouldRemember && legacyEmail.isNotEmpty && legacyTenant.isNotEmpty) {
      await upsertSavedAccount(
        SavedAccount(
          id: accountId(legacyTenant, legacyEmail),
          organizationCode: legacyTenant,
          login: legacyEmail,
          lastUsedAt: DateTime.now().toIso8601String(),
        ),
        password: legacyPassword,
      );
    }

    if (hadLegacyPassword) {
      await prefs.remove(_legacySavedPasswordKey);
    }
    if (prefs.containsKey(_legacySavedEmailKey)) {
      await prefs.remove(_legacySavedEmailKey);
    }
    if (prefs.containsKey(_legacySavedTenantCodeKey)) {
      await prefs.remove(_legacySavedTenantCodeKey);
    }
  }

  List<SavedAccount> _sortAccounts(List<SavedAccount> accounts) {
    final sorted = [...accounts];
    DateTime parseSafe(String value) =>
        DateTime.tryParse(value) ?? DateTime.fromMillisecondsSinceEpoch(0);
    sorted.sort(
      (a, b) => parseSafe(b.lastUsedAt).compareTo(parseSafe(a.lastUsedAt)),
    );
    return sorted;
  }
}

class CourseInfo {
  const CourseInfo({
    required this.id,
    required this.title,
    required this.description,
    required this.imageUrl,
  });

  final int id;
  final String title;
  final String description;
  final String? imageUrl;

  factory CourseInfo.fromJson(Map<String, dynamic> json) => CourseInfo(
        id: json['id'] as int,
        title: json['title'] as String? ??
            AppLanguageRuntime.strings.courseFallback,
        description: json['description'] as String? ?? '',
        imageUrl: json['image_url'] as String?,
      );
}

class TenantInfo {
  const TenantInfo({
    required this.id,
    required this.name,
    required this.code,
    required this.locale,
  });

  final int id;
  final String name;
  final String code;
  final String locale;

  factory TenantInfo.fromJson(Map<String, dynamic> json) => TenantInfo(
        id: json['id'] as int,
        name: json['name'] as String? ?? '',
        code: json['code'] as String? ?? '',
        locale: json['locale'] as String? ?? 'ru',
      );
}

class TestInfo {
  const TestInfo({
    required this.id,
    required this.courseId,
    required this.title,
  });

  final int id;
  final int courseId;
  final String title;

  factory TestInfo.fromJson(Map<String, dynamic> json) => TestInfo(
        id: json['id'] as int,
        courseId: json['course_id'] as int,
        title:
            json['title'] as String? ?? AppLanguageRuntime.strings.adaptiveTest,
      );
}

class RecommendationInfo {
  const RecommendationInfo({
    required this.priority,
    required this.text,
    required this.topicId,
    required this.topicTitle,
    required this.lessonId,
    required this.lessonTitle,
    required this.courseId,
    required this.courseTitle,
    required this.signalScore,
    required this.signalLevel,
    required this.reason,
  });

  final int priority;
  final String text;
  final int? topicId;
  final String topicTitle;
  final int? lessonId;
  final String lessonTitle;
  final int? courseId;
  final String courseTitle;
  final int signalScore;
  final String signalLevel;
  final String reason;

  String get focusTitle => topicTitle.trim().isNotEmpty ? topicTitle : text;

  bool get hasLocation =>
      lessonTitle.trim().isNotEmpty || courseTitle.trim().isNotEmpty;

  factory RecommendationInfo.fromJson(Map<String, dynamic> json) =>
      RecommendationInfo(
        priority: json['priority'] as int? ?? 1,
        text: json['text'] as String? ?? '',
        topicId: json['topic_id'] as int?,
        topicTitle: json['topic_title'] as String? ?? '',
        lessonId: json['lesson_id'] as int?,
        lessonTitle: json['lesson_title'] as String? ?? '',
        courseId: json['course_id'] as int?,
        courseTitle: json['course_title'] as String? ?? '',
        signalScore: json['signal_score'] as int? ?? 0,
        signalLevel: json['signal_level'] as String? ?? '',
        reason: json['reason'] as String? ?? '',
      );
}

class AttemptHistoryItem {
  const AttemptHistoryItem({
    required this.attemptId,
    required this.testId,
    required this.testTitle,
    required this.courseId,
    required this.courseTitle,
    required this.scorePercent,
    required this.correctAnswers,
    required this.totalQuestions,
    required this.averageResponseSeconds,
    required this.finalDifficulty,
    required this.difficultyPath,
    required this.weakTopics,
    required this.recommendationCount,
    required this.startedAt,
    required this.finishedAt,
  });

  final int attemptId;
  final int testId;
  final String testTitle;
  final int courseId;
  final String courseTitle;
  final int scorePercent;
  final int correctAnswers;
  final int totalQuestions;
  final int averageResponseSeconds;
  final int finalDifficulty;
  final List<int> difficultyPath;
  final List<Map<String, dynamic>> weakTopics;
  final int recommendationCount;
  final DateTime? startedAt;
  final DateTime? finishedAt;

  factory AttemptHistoryItem.fromJson(Map<String, dynamic> json) =>
      AttemptHistoryItem(
        attemptId: json['attempt_id'] as int,
        testId: json['test_id'] as int? ?? 0,
        testTitle: json['test_title'] as String? ?? '',
        courseId: json['course_id'] as int? ?? 0,
        courseTitle: json['course_title'] as String? ?? '',
        scorePercent: json['score_percent'] as int? ?? 0,
        correctAnswers: json['correct_answers'] as int? ?? 0,
        totalQuestions: json['total_questions'] as int? ?? 0,
        averageResponseSeconds: json['average_response_seconds'] as int? ?? 0,
        finalDifficulty: json['final_difficulty'] as int? ?? 1,
        difficultyPath: (json['difficulty_path'] as List<dynamic>? ?? const [])
            .map((item) => item as int)
            .toList(),
        weakTopics: jsonList(json['weak_topics']),
        recommendationCount: json['recommendation_count'] as int? ?? 0,
        startedAt: json['started_at'] == null
            ? null
            : DateTime.tryParse(json['started_at'] as String),
        finishedAt: json['finished_at'] == null
            ? null
            : DateTime.tryParse(json['finished_at'] as String),
      );
}

class AttemptReviewOption {
  const AttemptReviewOption({
    required this.id,
    required this.text,
    required this.isSelected,
    required this.isCorrect,
  });

  final int id;
  final String text;
  final bool isSelected;
  final bool isCorrect;

  factory AttemptReviewOption.fromJson(Map<String, dynamic> json) =>
      AttemptReviewOption(
        id: json['id'] as int? ?? 0,
        text: json['text'] as String? ?? '',
        isSelected: json['is_selected'] as bool? ?? false,
        isCorrect: json['is_correct'] as bool? ?? false,
      );
}

class AttemptReviewQuestion {
  const AttemptReviewQuestion({
    required this.questionId,
    required this.questionNumber,
    required this.text,
    required this.difficulty,
    required this.responseSeconds,
    required this.isCorrect,
    required this.explanation,
    required this.topicTitles,
    required this.selectedOptionId,
    required this.selectedOptionText,
    required this.correctOptionId,
    required this.correctOptionText,
    required this.options,
  });

  final int questionId;
  final int questionNumber;
  final String text;
  final int difficulty;
  final int responseSeconds;
  final bool isCorrect;
  final String explanation;
  final List<String> topicTitles;
  final int? selectedOptionId;
  final String selectedOptionText;
  final int? correctOptionId;
  final String correctOptionText;
  final List<AttemptReviewOption> options;

  factory AttemptReviewQuestion.fromJson(Map<String, dynamic> json) =>
      AttemptReviewQuestion(
        questionId: json['question_id'] as int? ?? 0,
        questionNumber: json['question_number'] as int? ?? 0,
        text: json['text'] as String? ?? '',
        difficulty: json['difficulty'] as int? ?? 1,
        responseSeconds: json['response_seconds'] as int? ?? 0,
        isCorrect: json['is_correct'] as bool? ?? false,
        explanation: json['explanation'] as String? ?? '',
        topicTitles: (json['topic_titles'] as List<dynamic>? ?? const [])
            .map((item) => item as String)
            .toList(),
        selectedOptionId: json['selected_option_id'] as int?,
        selectedOptionText: json['selected_option_text'] as String? ?? '',
        correctOptionId: json['correct_option_id'] as int?,
        correctOptionText: json['correct_option_text'] as String? ?? '',
        options: (json['options'] as List<dynamic>? ?? const [])
            .map((item) => AttemptReviewOption.fromJson(jsonMap(item)))
            .toList(),
      );
}

class AttemptReviewPayload {
  const AttemptReviewPayload({
    required this.attemptId,
    required this.testId,
    required this.testTitle,
    required this.courseId,
    required this.courseTitle,
    required this.scorePercent,
    required this.correctAnswers,
    required this.totalQuestions,
    required this.averageResponseSeconds,
    required this.finalDifficulty,
    required this.difficultyPath,
    required this.weakTopics,
    required this.startedAt,
    required this.finishedAt,
    required this.questions,
  });

  final int attemptId;
  final int testId;
  final String testTitle;
  final int courseId;
  final String courseTitle;
  final int scorePercent;
  final int correctAnswers;
  final int totalQuestions;
  final int averageResponseSeconds;
  final int finalDifficulty;
  final List<int> difficultyPath;
  final List<Map<String, dynamic>> weakTopics;
  final DateTime? startedAt;
  final DateTime? finishedAt;
  final List<AttemptReviewQuestion> questions;

  factory AttemptReviewPayload.fromJson(Map<String, dynamic> json) =>
      AttemptReviewPayload(
        attemptId: json['attempt_id'] as int? ?? 0,
        testId: json['test_id'] as int? ?? 0,
        testTitle: json['test_title'] as String? ?? '',
        courseId: json['course_id'] as int? ?? 0,
        courseTitle: json['course_title'] as String? ?? '',
        scorePercent: json['score_percent'] as int? ?? 0,
        correctAnswers: json['correct_answers'] as int? ?? 0,
        totalQuestions: json['total_questions'] as int? ?? 0,
        averageResponseSeconds: json['average_response_seconds'] as int? ?? 0,
        finalDifficulty: json['final_difficulty'] as int? ?? 1,
        difficultyPath: (json['difficulty_path'] as List<dynamic>? ?? const [])
            .map((item) => item as int)
            .toList(),
        weakTopics: jsonList(json['weak_topics']),
        startedAt: json['started_at'] == null
            ? null
            : DateTime.tryParse(json['started_at'] as String),
        finishedAt: json['finished_at'] == null
            ? null
            : DateTime.tryParse(json['finished_at'] as String),
        questions: (json['questions'] as List<dynamic>? ?? const [])
            .map((item) => AttemptReviewQuestion.fromJson(jsonMap(item)))
            .toList(),
      );
}

class UserProfile {
  const UserProfile({
    required this.id,
    required this.email,
    required this.fullName,
  });

  final int id;
  final String email;
  final String fullName;

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        id: json['id'] as int,
        email: json['email'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
      );
}

class CourseOutlineSection {
  const CourseOutlineSection({
    required this.id,
    required this.title,
    required this.sortOrder,
    required this.isVisible,
  });

  final int id;
  final String title;
  final int sortOrder;
  final bool isVisible;

  factory CourseOutlineSection.fromJson(Map<String, dynamic> json) =>
      CourseOutlineSection(
        id: json['id'] as int,
        title: json['title'] as String? ?? '',
        sortOrder: json['sort_order'] as int? ?? 0,
        isVisible: json['is_visible'] as bool? ?? true,
      );
}

class CourseOutlineLesson {
  const CourseOutlineLesson({
    required this.id,
    required this.sectionId,
    required this.title,
    required this.summary,
    required this.sortOrder,
    required this.durationMinutes,
    required this.pageCount,
    required this.currentPageIndex,
    required this.isCompleted,
    required this.isCurrent,
    required this.hasVideo,
  });

  final int id;
  final int? sectionId;
  final String title;
  final String summary;
  final int sortOrder;
  final int durationMinutes;
  final int pageCount;
  final int currentPageIndex;
  final bool isCompleted;
  final bool isCurrent;
  final bool hasVideo;

  factory CourseOutlineLesson.fromJson(Map<String, dynamic> json) =>
      CourseOutlineLesson(
        id: json['id'] as int,
        sectionId: json['section_id'] as int?,
        title: json['title'] as String? ??
            AppLanguageRuntime.strings.lessonFallback,
        summary: json['summary'] as String? ?? '',
        sortOrder: json['sort_order'] as int? ?? 0,
        durationMinutes: json['duration_minutes'] as int? ?? 0,
        pageCount: json['page_count'] as int? ?? 1,
        currentPageIndex: json['current_page_index'] as int? ?? 0,
        isCompleted: json['is_completed'] as bool? ?? false,
        isCurrent: json['is_current'] as bool? ?? false,
        hasVideo: json['has_video'] as bool? ?? false,
      );
}

class CourseOutlinePayload {
  const CourseOutlinePayload({
    required this.courseId,
    required this.courseTitle,
    required this.description,
    required this.totalLessons,
    required this.completedLessons,
    required this.progressPercent,
    required this.resumeLessonId,
    required this.sections,
    required this.lessons,
  });

  final int courseId;
  final String courseTitle;
  final String description;
  final int totalLessons;
  final int completedLessons;
  final int progressPercent;
  final int? resumeLessonId;
  final List<CourseOutlineSection> sections;
  final List<CourseOutlineLesson> lessons;

  factory CourseOutlinePayload.fromJson(Map<String, dynamic> json) =>
      CourseOutlinePayload(
        courseId: json['course_id'] as int,
        courseTitle: json['course_title'] as String? ??
            AppLanguageRuntime.strings.courseFallback,
        description: json['description'] as String? ?? '',
        totalLessons: json['total_lessons'] as int? ?? 0,
        completedLessons: json['completed_lessons'] as int? ?? 0,
        progressPercent: json['progress_percent'] as int? ?? 0,
        resumeLessonId: json['resume_lesson_id'] as int?,
        sections: jsonList(json['sections'])
            .map(CourseOutlineSection.fromJson)
            .toList(),
        lessons: jsonList(json['lessons'])
            .map(CourseOutlineLesson.fromJson)
            .toList(),
      );
}

class CourseOutlineSectionGroup {
  const CourseOutlineSectionGroup({
    required this.id,
    required this.title,
    required this.lessons,
    required this.isFallback,
  });

  final int? id;
  final String title;
  final List<CourseOutlineLesson> lessons;
  final bool isFallback;

  bool get hasSectionTitle => !isFallback && title.trim().isNotEmpty;
}

String normalizeSectionTitle(String rawTitle, AppStrings strings) {
  final normalized = rawTitle.trim();
  return normalized.isEmpty ? strings.lessonFallback : normalized;
}

List<CourseOutlineSectionGroup> buildOutlineSectionGroups(
  CourseOutlinePayload outline,
  AppStrings strings,
) {
  final lessonBuckets = <int?, List<CourseOutlineLesson>>{};
  for (final lesson in outline.lessons) {
    lessonBuckets.putIfAbsent(lesson.sectionId, () => <CourseOutlineLesson>[]);
    lessonBuckets[lesson.sectionId]!.add(lesson);
  }

  final groups = <CourseOutlineSectionGroup>[];
  for (final section in outline.sections) {
    final lessons =
        lessonBuckets.remove(section.id) ?? const <CourseOutlineLesson>[];
    if (lessons.isEmpty) {
      continue;
    }
    groups.add(
      CourseOutlineSectionGroup(
        id: section.id,
        title: normalizeSectionTitle(section.title, strings),
        lessons: lessons,
        isFallback: false,
      ),
    );
  }

  final unsectioned = <CourseOutlineLesson>[
    ...(lessonBuckets.remove(null) ?? const <CourseOutlineLesson>[]),
  ];
  for (final lessons in lessonBuckets.values) {
    unsectioned.addAll(lessons);
  }
  if (unsectioned.isNotEmpty) {
    groups.add(
      CourseOutlineSectionGroup(
        id: null,
        title: '',
        lessons: unsectioned,
        isFallback: true,
      ),
    );
  }
  return groups;
}

class LessonBlockData {
  const LessonBlockData({
    required this.type,
    this.text,
    this.html,
    this.url,
    this.alt,
    this.title,
    this.status,
    this.error,
  });

  final String type;
  final String? text;
  final String? html;
  final String? url;
  final String? alt;
  final String? title;
  final String? status;
  final String? error;

  factory LessonBlockData.fromJson(Map<String, dynamic> json) =>
      LessonBlockData(
        type: json['type'] as String? ?? 'text',
        text: json['text'] as String?,
        html: json['html'] as String?,
        url: json['url'] as String?,
        alt: json['alt'] as String?,
        title: json['title'] as String?,
        status: json['status'] as String?,
        error: json['error'] as String?,
      );
}

class LessonPageData {
  const LessonPageData({
    required this.pageId,
    required this.chapterTitle,
    required this.pageTitle,
    required this.isPractice,
    required this.blocks,
  });

  final String pageId;
  final String chapterTitle;
  final String pageTitle;
  final bool isPractice;
  final List<LessonBlockData> blocks;

  factory LessonPageData.fromJson(Map<String, dynamic> json) => LessonPageData(
        pageId: json['page_id'] as String? ?? 'page-1',
        chapterTitle: json['chapter_title'] as String? ??
            AppLanguageRuntime.strings.lessonFallback,
        pageTitle: json['page_title'] as String? ??
            AppLanguageRuntime.strings.pageFallback,
        isPractice: json['is_practice'] as bool? ?? false,
        blocks: jsonList(json['blocks']).map(LessonBlockData.fromJson).toList(),
      );
}

class LessonChapterPageData {
  const LessonChapterPageData({
    required this.pageId,
    required this.pageTitle,
    required this.pageIndex,
  });

  final String pageId;
  final String pageTitle;
  final int pageIndex;

  factory LessonChapterPageData.fromJson(Map<String, dynamic> json) =>
      LessonChapterPageData(
        pageId: json['page_id'] as String? ?? 'page-1',
        pageTitle: json['page_title'] as String? ??
            AppLanguageRuntime.strings.pageFallback,
        pageIndex: json['page_index'] as int? ?? 0,
      );
}

class LessonChapterData {
  const LessonChapterData({
    required this.chapterTitle,
    required this.pages,
  });

  final String chapterTitle;
  final List<LessonChapterPageData> pages;

  factory LessonChapterData.fromJson(Map<String, dynamic> json) =>
      LessonChapterData(
        chapterTitle: json['chapter_title'] as String? ??
            AppLanguageRuntime.strings.lessonFallback,
        pages: jsonList(json['pages'])
            .map(LessonChapterPageData.fromJson)
            .toList(),
      );
}

class LessonPlayerStateData {
  const LessonPlayerStateData({
    required this.currentPageIndex,
    required this.completedPageIds,
    required this.isCompleted,
    required this.lastVideoPositionSeconds,
  });

  final int currentPageIndex;
  final List<String> completedPageIds;
  final bool isCompleted;
  final int lastVideoPositionSeconds;

  factory LessonPlayerStateData.fromJson(Map<String, dynamic> json) =>
      LessonPlayerStateData(
        currentPageIndex: json['current_page_index'] as int? ?? 0,
        completedPageIds:
            ((json['completed_page_ids'] as List<dynamic>? ?? const [])
                    .cast<String>())
                .toList(),
        isCompleted: json['is_completed'] as bool? ?? false,
        lastVideoPositionSeconds:
            json['last_video_position_seconds'] as int? ?? 0,
      );
}

class LessonPlayerPayload {
  const LessonPlayerPayload({
    required this.courseId,
    required this.courseTitle,
    required this.lessonId,
    required this.lessonTitle,
    required this.summary,
    required this.durationMinutes,
    required this.pages,
    required this.chapters,
    required this.outline,
    required this.state,
    required this.previousLessonId,
    required this.nextLessonId,
  });

  final int courseId;
  final String courseTitle;
  final int lessonId;
  final String lessonTitle;
  final String summary;
  final int durationMinutes;
  final List<LessonPageData> pages;
  final List<LessonChapterData> chapters;
  final CourseOutlinePayload outline;
  final LessonPlayerStateData state;
  final int? previousLessonId;
  final int? nextLessonId;

  factory LessonPlayerPayload.fromJson(Map<String, dynamic> json) =>
      LessonPlayerPayload(
        courseId: json['course_id'] as int,
        courseTitle: json['course_title'] as String? ??
            AppLanguageRuntime.strings.courseFallback,
        lessonId: json['lesson_id'] as int,
        lessonTitle: json['lesson_title'] as String? ??
            AppLanguageRuntime.strings.lessonFallback,
        summary: json['summary'] as String? ?? '',
        durationMinutes: json['duration_minutes'] as int? ?? 0,
        pages: jsonList(json['pages']).map(LessonPageData.fromJson).toList(),
        chapters:
            jsonList(json['chapters']).map(LessonChapterData.fromJson).toList(),
        outline: CourseOutlinePayload.fromJson(jsonMap(json['outline'])),
        state: LessonPlayerStateData.fromJson(jsonMap(json['state'])),
        previousLessonId: json['previous_lesson_id'] as int?,
        nextLessonId: json['next_lesson_id'] as int?,
      );
}

class AssignmentInfo {
  const AssignmentInfo({
    required this.id,
    required this.courseId,
    required this.lessonId,
    required this.title,
    required this.description,
    required this.isActive,
  });

  final int id;
  final int courseId;
  final int? lessonId;
  final String title;
  final String description;
  final bool isActive;

  factory AssignmentInfo.fromJson(Map<String, dynamic> json) => AssignmentInfo(
        id: json['id'] as int,
        courseId: json['course_id'] as int,
        lessonId: json['lesson_id'] as int?,
        title: json['title'] as String? ??
            AppLanguageRuntime.strings.assignmentFallback,
        description: json['description'] as String? ?? '',
        isActive: json['is_active'] as bool? ?? true,
      );
}

class AssignmentSubmissionInfo {
  const AssignmentSubmissionInfo({
    required this.id,
    required this.assignmentId,
    required this.studentUserId,
    required this.status,
    required this.textAnswer,
    required this.linkAnswer,
    required this.reviewerComment,
    required this.reviewerGrade,
    required this.fileUrls,
  });

  final int id;
  final int assignmentId;
  final int studentUserId;
  final String status;
  final String textAnswer;
  final String? linkAnswer;
  final String? reviewerComment;
  final int? reviewerGrade;
  final List<String> fileUrls;

  factory AssignmentSubmissionInfo.fromJson(Map<String, dynamic> json) {
    final latestReview = jsonMap(json['latest_review'] ?? const {});
    final files = jsonList(json['files']).map((item) => item['file_url'] as String? ?? '').where((item) => item.trim().isNotEmpty).toList();
    return AssignmentSubmissionInfo(
      id: json['id'] as int,
      assignmentId: json['assignment_id'] as int,
      studentUserId: json['student_user_id'] as int,
      status: (json['status'] as String? ?? 'draft').toLowerCase(),
      textAnswer: json['text_answer'] as String? ?? '',
      linkAnswer: json['link_answer'] as String?,
      reviewerComment:
          latestReview.isEmpty ? null : latestReview['comment'] as String?,
      reviewerGrade: latestReview.isEmpty ? null : latestReview['grade'] as int?,
      fileUrls: files,
    );
  }
}

String resolveMediaUrl(SessionState session, String? rawUrl) {
  if (rawUrl == null || rawUrl.trim().isEmpty) {
    return '';
  }
  if (rawUrl.startsWith('http://') || rawUrl.startsWith('https://')) {
    return rawUrl;
  }
  final baseUri = Uri.parse(session.baseUrl);
  final origin = Uri.parse('${baseUri.scheme}://${baseUri.authority}/');
  final resolved = origin.resolve(rawUrl);
  if (!resolved.path.startsWith('/media/')) {
    return resolved.toString();
  }
  final queryParameters = Map<String, String>.from(resolved.queryParameters);
  queryParameters.putIfAbsent('v', () => _mediaCacheVersion);
  return resolved.replace(queryParameters: queryParameters).toString();
}

Map<String, String>? resolveMediaHeaders(
    SessionState session, String mediaUrl) {
  final trimmed = mediaUrl.trim();
  if (trimmed.isEmpty) {
    return null;
  }
  final mediaUri = Uri.tryParse(trimmed);
  final baseUri = Uri.tryParse(session.baseUrl);
  if (mediaUri == null || baseUri == null) {
    return null;
  }
  final isSameOrigin = mediaUri.scheme == baseUri.scheme &&
      mediaUri.authority == baseUri.authority;
  if (!isSameOrigin || !mediaUri.path.startsWith('/media/')) {
    return null;
  }
  return <String, String>{
    'Authorization': 'Bearer ${session.accessToken}',
    'X-Tenant-Code': session.tenantCode,
  };
}

class ApiClient {
  ApiClient({
    String? baseUrl,
    this.onSessionUpdate,
    this.onSessionInvalid,
  }) : baseUrl = baseUrl ?? _defaultBaseUrl();

  final String baseUrl;
  final ValueChanged<SessionState>? onSessionUpdate;
  final VoidCallback? onSessionInvalid;

  static String _defaultBaseUrl() {
    const envBase = String.fromEnvironment('API_BASE');
    if (envBase.isNotEmpty) {
      return envBase;
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'https://api.coursum.online/api/v1';
    }
    return 'https://api.coursum.online/api/v1';
  }

  Future<dynamic> request(
    String path, {
    String method = 'GET',
    SessionState? session,
    Object? body,
    bool didRefresh = false,
  }) async {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (session != null) {
      headers['Authorization'] = 'Bearer ${session.accessToken}';
      headers['X-Tenant-Code'] = session.tenantCode;
    }
    final httpRequest = http.Request(method, Uri.parse('$baseUrl$path'));
    httpRequest.headers.addAll(headers);
    if (body != null) {
      httpRequest.body = jsonEncode(body);
    }
    final response = await httpRequest
        .send()
        .then(http.Response.fromStream)
        .timeout(const Duration(seconds: 15), onTimeout: () {
      throw Exception(AppLanguageRuntime.strings.requestTimedOut);
    });
    final isAuthEndpoint = path == '/auth/login' || path == '/auth/refresh';
    final canRefresh = !didRefresh &&
        !isAuthEndpoint &&
        session?.refreshToken != null &&
        response.statusCode == 401;
    if (canRefresh) {
      try {
        final refreshed = await _refreshTokens(session!.refreshToken!);
        final nextSession = SessionState(
          accessToken:
              refreshed['access_token'] as String? ?? session.accessToken,
          refreshToken:
              refreshed['refresh_token'] as String? ?? session.refreshToken,
          tenantCode: session.tenantCode,
          baseUrl: session.baseUrl,
        );
        onSessionUpdate?.call(nextSession);
        return request(
          path,
          method: method,
          session: nextSession,
          body: body,
          didRefresh: true,
        );
      } catch (_) {
        onSessionInvalid?.call();
        throw Exception('Session expired');
      }
    }
    if (response.statusCode >= 400) {
      if (response.statusCode == 401 && !isAuthEndpoint && session != null) {
        onSessionInvalid?.call();
      }
      throw Exception(_extractError(response.body));
    }
    if (response.body.trim().isEmpty) {
      return <String, dynamic>{};
    }
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> _refreshTokens(String refreshToken) async {
    final request = http.Request('POST', Uri.parse('$baseUrl/auth/refresh'));
    request.headers['Content-Type'] = 'application/json';
    request.body = jsonEncode({'refresh_token': refreshToken});
    final response = await request
        .send()
        .then(http.Response.fromStream)
        .timeout(const Duration(seconds: 15), onTimeout: () {
      throw Exception(AppLanguageRuntime.strings.requestTimedOut);
    });
    if (response.statusCode >= 400) {
      throw Exception(_extractError(response.body));
    }
    return jsonMap(jsonDecode(response.body));
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    return jsonMap(await request(
      '/auth/login',
      method: 'POST',
      body: {'email': email.trim(), 'password': password},
    ));
  }

  Future<List<CourseInfo>> getCourses(SessionState session) async {
    final payload =
        await request('/courses', session: session) as List<dynamic>;
    return payload.map((item) => CourseInfo.fromJson(jsonMap(item))).toList();
  }

  Future<List<TestInfo>> getTests(SessionState session) async {
    final payload = await request('/tests', session: session) as List<dynamic>;
    return payload.map((item) => TestInfo.fromJson(jsonMap(item))).toList();
  }

  Future<List<RecommendationInfo>> getRecommendations(
      SessionState session) async {
    final payload =
        await request('/recommendations/me', session: session) as List<dynamic>;
    return payload
        .map((item) => RecommendationInfo.fromJson(jsonMap(item)))
        .toList();
  }

  Future<List<AssignmentInfo>> getAssignments(
    SessionState session, {
    int? courseId,
    int? lessonId,
  }) async {
    final query = <String>[];
    if (courseId != null) {
      query.add('course_id=$courseId');
    }
    if (lessonId != null) {
      query.add('lesson_id=$lessonId');
    }
    final suffix = query.isEmpty ? '' : '?${query.join('&')}';
    final payload =
        await request('/assignments$suffix', session: session) as List<dynamic>;
    return payload
        .map((item) => AssignmentInfo.fromJson(jsonMap(item)))
        .toList();
  }

  Future<List<AssignmentSubmissionInfo>> getAssignmentSubmissions(
    int assignmentId,
    SessionState session,
  ) async {
    final payload = await request('/assignments/$assignmentId/submissions',
        session: session) as List<dynamic>;
    return payload
        .map((item) => AssignmentSubmissionInfo.fromJson(jsonMap(item)))
        .toList();
  }

  Future<AssignmentSubmissionInfo> submitAssignment(
    int assignmentId,
    SessionState session, {
    required String textAnswer,
    String? linkAnswer,
    List<String> fileUrls = const [],
  }) async {
    final payload = await request(
      '/assignments/$assignmentId/submissions',
      method: 'POST',
      session: session,
      body: {
        'status': 'submitted',
        'text_answer': textAnswer,
        'link_answer': linkAnswer,
        'file_urls': fileUrls,
      },
    );
    return AssignmentSubmissionInfo.fromJson(jsonMap(payload));
  }

  Future<Map<String, String>> uploadAssignmentSubmissionFile(
    SessionState session, {
    required int assignmentId,
    required PlatformFile file,
  }) async {
    final uri = Uri.parse('$baseUrl/assignments/submissions/upload');
    final request = http.MultipartRequest('POST', uri);
    request.headers['Authorization'] = 'Bearer ${session.accessToken}';
    request.headers['X-Tenant-Code'] = session.tenantCode;
    request.fields['assignment_id'] = '$assignmentId';
    if (file.bytes != null) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          file.bytes!,
          filename: file.name,
        ),
      );
    } else if (file.path != null) {
      request.files.add(
        await http.MultipartFile.fromPath(
          'file',
          file.path!,
          filename: file.name,
        ),
      );
    } else {
      throw Exception('Cannot read selected file');
    }
    final response = await request.send().then(http.Response.fromStream);
    final payload = response.body.trim().isEmpty
        ? <String, dynamic>{}
        : jsonMap(jsonDecode(response.body));
    if (response.statusCode >= 400) {
      throw Exception(payload['detail'] ?? 'Upload failed');
    }
    return {
      'file_url': payload['file_url'] as String? ?? '',
      'file_name': payload['file_name'] as String? ?? file.name,
    };
  }

  Future<List<AttemptHistoryItem>> getAttemptHistory(
    SessionState session, {
    int? courseId,
  }) async {
    final query = courseId == null ? '' : '?course_id=$courseId';
    final payload = await request('/attempts/history$query', session: session)
        as List<dynamic>;
    return payload
        .map((item) => AttemptHistoryItem.fromJson(jsonMap(item)))
        .toList();
  }

  Future<AttemptReviewPayload> getAttemptReview(
    int attemptId,
    SessionState session,
  ) async {
    return AttemptReviewPayload.fromJson(
      jsonMap(
        await request('/attempts/$attemptId/review', session: session),
      ),
    );
  }

  Future<UserProfile> getProfile(SessionState session) async {
    return UserProfile.fromJson(
        jsonMap(await request('/auth/me', session: session)));
  }

  Future<TenantInfo> getCurrentTenant(SessionState session) async {
    return TenantInfo.fromJson(
        jsonMap(await request('/tenants/current', session: session)));
  }

  Future<CourseOutlinePayload> getCourseOutline(
      int courseId, SessionState session) async {
    return CourseOutlinePayload.fromJson(
        jsonMap(await request('/courses/$courseId/outline', session: session)));
  }

  Future<LessonPlayerPayload> getLessonPlayer(
      int lessonId, SessionState session) async {
    return LessonPlayerPayload.fromJson(
        jsonMap(await request('/lessons/$lessonId/player', session: session)));
  }

  Future<Map<String, dynamic>> saveLessonState(
    int lessonId,
    SessionState session, {
    int? currentPageIndex,
    List<String>? completedPageIds,
    int? lastVideoPositionSeconds,
    bool? isCompleted,
  }) async {
    return jsonMap(await request(
      '/lessons/$lessonId/state',
      method: 'POST',
      session: session,
      body: {
        if (currentPageIndex != null) 'current_page_index': currentPageIndex,
        if (completedPageIds != null) 'completed_page_ids': completedPageIds,
        if (lastVideoPositionSeconds != null)
          'last_video_position_seconds': lastVideoPositionSeconds,
        if (isCompleted != null) 'is_completed': isCompleted,
      },
    ));
  }

  Future<Map<String, dynamic>> startAttempt(
      int testId, SessionState session) async {
    return jsonMap(await request('/tests/$testId/start',
        method: 'POST', session: session, body: const {}));
  }

  Future<Map<String, dynamic>?> getAttemptQuestion(
      int attemptId, SessionState session) async {
    final payload =
        await request('/attempts/$attemptId/next-question', session: session);
    if (payload == null) {
      return null;
    }
    return jsonMap(payload);
  }

  Future<Map<String, dynamic>> submitAttemptAnswer(
    int attemptId,
    SessionState session, {
    required int questionId,
    required int answerOptionId,
    required int responseSeconds,
  }) async {
    return jsonMap(await request(
      '/attempts/$attemptId/submit-answer',
      method: 'POST',
      session: session,
      body: {
        'question_id': questionId,
        'answer_option_id': answerOptionId,
        'response_seconds': responseSeconds
      },
    ));
  }

  Future<Map<String, dynamic>> finishAttempt(
      int attemptId, SessionState session) async {
    return jsonMap(await request('/attempts/$attemptId/finish',
        method: 'POST', session: session, body: const {}));
  }

  String _extractError(String body) {
    try {
      final payload = jsonMap(jsonDecode(body));
      return payload['detail'] as String? ??
          AppLanguageRuntime.strings.requestFailed;
    } catch (_) {
      return AppLanguageRuntime.strings.requestFailed;
    }
  }
}

class CoursumApp extends StatefulWidget {
  const CoursumApp({super.key});

  @override
  State<CoursumApp> createState() => _CoursumAppState();
}

class _CoursumAppState extends State<CoursumApp> {
  static const _languagePreferenceKey = 'app_language';
  late final AppLanguageController _languageController =
      AppLanguageController(AppLanguage.ru);

  @override
  void initState() {
    super.initState();
    _restoreLanguage();
  }

  Future<void> _restoreLanguage() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedLanguage = prefs.getString(_languagePreferenceKey);
      _languageController.setLanguage(AppLanguageCodec.fromCode(savedLanguage));
    } catch (_) {
      // Keep default Russian if preferences are unavailable.
    }
  }

  Future<void> _updateLanguage(AppLanguage language) async {
    _languageController.setLanguage(language);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_languagePreferenceKey, language.code);
    } catch (_) {
      // The UI should still switch instantly even if persistence fails.
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _languageController,
      builder: (context, _) {
        final strings = AppStrings(_languageController.language);
        return AppLocalizationScope(
          controller: _languageController,
          onLanguageChanged: _updateLanguage,
          child: MaterialApp(
            title: strings.appTitle,
            debugShowCheckedModeBanner: false,
            locale: Locale(_languageController.language.code),
            supportedLocales: const [Locale('ru'), Locale('en')],
            localizationsDelegates: const [
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            theme: ThemeData(
              colorScheme: ColorScheme.fromSeed(
                seedColor: const Color(0xFF0B1D3A),
                primary: const Color(0xFF0B1D3A),
                secondary: const Color(0xFF22C55E),
                tertiary: const Color(0xFF2563EB),
                surface: const Color(0xFFFFFCF4),
              ),
              scaffoldBackgroundColor: const Color(0xFFF7F3E6),
              useMaterial3: true,
              appBarTheme: const AppBarTheme(
                backgroundColor: Color(0xFFF7F3E6),
                foregroundColor: Color(0xFF0B1D3A),
                centerTitle: false,
              ),
              cardTheme: CardThemeData(
                color: Colors.white,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(28),
                ),
              ),
              filledButtonTheme: FilledButtonThemeData(
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF0B1D3A),
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(48),
                ),
              ),
            ),
            home: const SessionCoordinator(),
          ),
        );
      },
    );
  }
}

class SessionCoordinator extends StatefulWidget {
  const SessionCoordinator({super.key});

  @override
  State<SessionCoordinator> createState() => _SessionCoordinatorState();
}

class _SessionCoordinatorState extends State<SessionCoordinator> {
  final AuthStorage _authStorage = AuthStorage();
  SessionState? session;
  bool initializing = true;

  @override
  void initState() {
    super.initState();
    unawaited(_restoreSession());
  }

  Future<void> _restoreSession() async {
    await _authStorage.migrateLegacyRememberedCredentials();
    final restoredSession = await _authStorage.readActiveSession();
    if (!mounted) {
      return;
    }
    setState(() {
      session = restoredSession;
      initializing = false;
    });
  }

  Future<void> _handleLogin(SessionState nextSession) async {
    await _authStorage.saveActiveSession(nextSession);
    if (!mounted) {
      return;
    }
    setState(() => session = nextSession);
  }

  void _handleSessionUpdate(SessionState nextSession) {
    unawaited(_authStorage.saveActiveSession(nextSession));
    if (mounted) {
      setState(() => session = nextSession);
    }
  }

  void _handleLogout() {
    unawaited(_authStorage.clearActiveSession());
    if (mounted) {
      setState(() => session = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (initializing) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (session == null) {
      return LoginScreen(onLogin: _handleLogin, authStorage: _authStorage);
    }
    return HomeShell(
      session: session!,
      onSessionUpdate: _handleSessionUpdate,
      onLogout: _handleLogout,
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.onLogin,
    required this.authStorage,
  });

  final Future<void> Function(SessionState value) onLogin;
  final AuthStorage authStorage;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final emailController = TextEditingController(
      text: kDebugMode && _enableDevAuthPrefill ? _devLoginEmail : '');
  final passwordController = TextEditingController(
      text: kDebugMode && _enableDevAuthPrefill ? _devLoginPassword : '');
  final tenantCodeController = TextEditingController(
      text: kDebugMode && _enableDevAuthPrefill ? _devTenantCode : '');
  List<SavedAccount> savedAccounts = const [];
  String selectedAccountId = '';
  bool loadingSavedAccounts = true;
  bool rememberCredentials = false;
  bool loading = false;
  String error = '';

  @override
  void initState() {
    super.initState();
    unawaited(_restoreSavedState());
  }

  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    tenantCodeController.dispose();
    super.dispose();
  }

  Future<void> _restoreSavedState() async {
    try {
      final shouldRemember = await widget.authStorage.getRememberCredentials();
      final accounts = await widget.authStorage.readSavedAccounts();
      if (!mounted) {
        return;
      }
      setState(() {
        rememberCredentials = shouldRemember;
        savedAccounts = accounts;
        loadingSavedAccounts = false;
      });
      if (accounts.length == 1 && !kDebugMode) {
        await _selectSavedAccount(accounts.first);
      }
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        loadingSavedAccounts = false;
      });
    }
  }

  Future<void> _selectSavedAccount(SavedAccount account) async {
    final password = await widget.authStorage.readPassword(account.id);
    if (!mounted) {
      return;
    }
    setState(() {
      selectedAccountId = account.id;
      emailController.text = account.login;
      tenantCodeController.text = account.organizationCode;
      passwordController.text = password ?? '';
      error = '';
    });
  }

  Future<void> _removeSavedAccount(SavedAccount account) async {
    await widget.authStorage.removeSavedAccount(account.id);
    final accounts = await widget.authStorage.readSavedAccounts();
    if (!mounted) {
      return;
    }
    setState(() {
      savedAccounts = accounts;
      if (selectedAccountId == account.id) {
        selectedAccountId = '';
      }
    });
  }

  Future<void> _removeAllSavedAccounts() async {
    await widget.authStorage.removeAllSavedAccounts();
    if (!mounted) {
      return;
    }
    setState(() {
      savedAccounts = const [];
      selectedAccountId = '';
      emailController.clear();
      tenantCodeController.clear();
      passwordController.clear();
    });
  }

  Future<void> _persistRememberedAccount({
    required String login,
    required String organizationCode,
    required String password,
  }) async {
    await widget.authStorage.setRememberCredentials(rememberCredentials);
    if (!rememberCredentials) {
      return;
    }
    await widget.authStorage.upsertSavedAccount(
      SavedAccount(
        id: AuthStorage.accountId(organizationCode, login),
        organizationCode: organizationCode,
        login: login,
        lastUsedAt: DateTime.now().toIso8601String(),
      ),
      password: password,
    );
    final accounts = await widget.authStorage.readSavedAccounts();
    if (!mounted) {
      return;
    }
    setState(() {
      savedAccounts = accounts;
      selectedAccountId = AuthStorage.accountId(organizationCode, login);
    });
  }

  Future<void> _confirmDeleteAccount(SavedAccount account) async {
    final strings = context.strings;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(strings.savedAccountDelete),
        content: Text(strings.savedAccountDeleteConfirm(account.login)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(strings.cancelAction),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(strings.deleteAction),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await _removeSavedAccount(account);
    }
  }

  Future<void> _confirmDeleteAllAccounts() async {
    final strings = context.strings;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(strings.savedAccountsDeleteAll),
        content: Text(strings.savedAccountsDeleteAllConfirm),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(strings.cancelAction),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(strings.deleteAction),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await _removeAllSavedAccounts();
    }
  }

  Future<void> submit() async {
    final tenantCode = normalizeTenantCode(tenantCodeController.text);
    final normalizedLogin = normalizeLogin(emailController.text);
    final password = passwordController.text;
    if (tenantCode.isEmpty || normalizedLogin.isEmpty || password.isEmpty) {
      setState(() {
        error = context.strings.loginFieldsRequired;
      });
      return;
    }
    setState(() {
      loading = true;
      error = '';
    });
    final api = ApiClient();
    try {
      final tokens = await api.login(normalizedLogin, password);
      await _persistRememberedAccount(
        login: normalizedLogin,
        organizationCode: tenantCode,
        password: password,
      );
      await widget.onLogin(
        SessionState(
          accessToken: tokens['access_token'] as String,
          refreshToken: tokens['refresh_token'] as String?,
          tenantCode: tenantCode,
          baseUrl: api.baseUrl,
        ),
      );
    } catch (exception) {
      if (mounted) {
        setState(
            () => error = exception.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  Future<void> _openSavedAccountsPicker() async {
    final strings = context.strings;
    if (loadingSavedAccounts || savedAccounts.isEmpty) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(sheetContext).size.height * 0.7,
            ),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          strings.savedAccountsTitle,
                          style: Theme.of(sheetContext).textTheme.titleMedium,
                        ),
                      ),
                      TextButton(
                        onPressed: () async {
                          Navigator.of(sheetContext).pop();
                          await _confirmDeleteAllAccounts();
                        },
                        child: Text(strings.savedAccountsDeleteAll),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Expanded(
                    child: ListView.separated(
                      itemCount: savedAccounts.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (_, index) {
                        final account = savedAccounts[index];
                        return Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () async {
                                  Navigator.of(sheetContext).pop();
                                  await _selectSavedAccount(account);
                                },
                                child: Align(
                                  alignment: Alignment.centerLeft,
                                  child: Text(
                                    strings.savedAccountRow(
                                      account.login,
                                      account.organizationCode,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            IconButton(
                              tooltip: strings.savedAccountDelete,
                              onPressed: () async {
                                Navigator.of(sheetContext).pop();
                                await _confirmDeleteAccount(account);
                              },
                              icon: const Icon(Icons.delete_outline),
                            ),
                          ],
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> openOrganizationContact() async {
    final strings = context.strings;
    final uri = Uri.parse(
      'mailto:partnership@coursum.online'
      '?subject=${Uri.encodeComponent(strings.organizationContactEmailSubject)}'
      '&body=${Uri.encodeComponent(strings.organizationContactEmailBody)}',
    );
    final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!opened && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(strings.organizationContactOpenFailed)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final currentLanguage = context.currentAppLanguage;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Align(
                        alignment: Alignment.centerRight,
                        child: SegmentedButton<AppLanguage>(
                          segments: [
                            ButtonSegment(
                              value: AppLanguage.ru,
                              label: Text(strings.languageRussian),
                            ),
                            ButtonSegment(
                              value: AppLanguage.en,
                              label: Text(strings.languageEnglish),
                            ),
                          ],
                          selected: {currentLanguage},
                          onSelectionChanged: (values) {
                            final nextLanguage = values.first;
                            if (nextLanguage != currentLanguage) {
                              unawaited(context.setAppLanguage(nextLanguage));
                            }
                          },
                        ),
                      ),
                      const SizedBox(height: 16),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Semantics(
                          label: strings.appTitle,
                          image: true,
                          child: SvgPicture.asset(
                            'assets/brand/website_logo.svg',
                            width: 220,
                            fit: BoxFit.contain,
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(strings.loginSubtitle),
                      const SizedBox(height: 20),
                      TextField(
                        controller: emailController,
                        keyboardType: TextInputType.emailAddress,
                        onTap: _openSavedAccountsPicker,
                        decoration: InputDecoration(
                          labelText: strings.email,
                          suffixIcon: savedAccounts.isNotEmpty
                              ? const Icon(Icons.arrow_drop_down)
                              : null,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: passwordController,
                        obscureText: true,
                        decoration:
                            InputDecoration(labelText: strings.password),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: tenantCodeController,
                        decoration:
                            InputDecoration(labelText: strings.tenantCode),
                      ),
                      const SizedBox(height: 8),
                      CheckboxListTile(
                        value: rememberCredentials,
                        onChanged: loading
                            ? null
                            : (value) {
                                setState(() {
                                  rememberCredentials = value ?? false;
                                });
                              },
                        contentPadding: EdgeInsets.zero,
                        controlAffinity: ListTileControlAffinity.leading,
                        title: Text(strings.rememberCredentials),
                      ),
                      const SizedBox(height: 20),
                      FilledButton(
                        onPressed: loading ? null : submit,
                        child:
                            Text(loading ? strings.signingIn : strings.signIn),
                      ),
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Theme.of(context)
                              .colorScheme
                              .surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(18),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              strings.organizationContactTitle,
                              style: Theme.of(context).textTheme.titleSmall,
                            ),
                            const SizedBox(height: 6),
                            Text(strings.organizationContactBody),
                            const SizedBox(height: 10),
                            OutlinedButton.icon(
                              onPressed: openOrganizationContact,
                              icon: const Icon(Icons.mail_outline),
                              label: Text(strings.organizationContactAction),
                            ),
                          ],
                        ),
                      ),
                      if (error.isNotEmpty) ...[
                        const SizedBox(height: 12),
                        Text(
                          error,
                          style: TextStyle(
                              color: Theme.of(context).colorScheme.error),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.session,
    required this.onLogout,
    required this.onSessionUpdate,
  });

  final SessionState session;
  final VoidCallback onLogout;
  final ValueChanged<SessionState> onSessionUpdate;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;
  late ApiClient api;
  late Future<TenantInfo> tenantFuture;

  @override
  void initState() {
    super.initState();
    api = ApiClient(
      baseUrl: widget.session.baseUrl,
      onSessionUpdate: widget.onSessionUpdate,
      onSessionInvalid: widget.onLogout,
    );
    tenantFuture = api.getCurrentTenant(widget.session);
  }

  @override
  void didUpdateWidget(covariant HomeShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.session.baseUrl != widget.session.baseUrl) {
      api = ApiClient(
        baseUrl: widget.session.baseUrl,
        onSessionUpdate: widget.onSessionUpdate,
        onSessionInvalid: widget.onLogout,
      );
      tenantFuture = api.getCurrentTenant(widget.session);
      return;
    }
    if (oldWidget.session.tenantCode != widget.session.tenantCode) {
      tenantFuture = api.getCurrentTenant(widget.session);
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final pages = [
      CourseListScreen(api: api, session: widget.session),
      RecommendationsScreen(api: api, session: widget.session),
      ProfileScreen(
          api: api, session: widget.session, onLogout: widget.onLogout),
    ];
    return Scaffold(
      appBar: AppBar(
        title: FutureBuilder<TenantInfo>(
          future: tenantFuture,
          builder: (context, snapshot) {
            final tenantName = snapshot.data?.name.isNotEmpty == true
                ? snapshot.data!.name
                : _humanizeTenantCode(widget.session.tenantCode);
            return Row(
              children: [
                _OrganizationMark(label: tenantName),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    tenantName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            );
          },
        ),
      ),
      body: IndexedStack(index: index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (value) => setState(() => index = value),
        destinations: [
          NavigationDestination(
              icon: const Icon(Icons.menu_book_outlined),
              label: strings.coursesTab),
          NavigationDestination(
              icon: const Icon(Icons.lightbulb_outline),
              label: strings.recommendationsTab),
          NavigationDestination(
              icon: const Icon(Icons.person_outline),
              label: strings.profileTab),
        ],
      ),
    );
  }
}

class CourseListScreen extends StatefulWidget {
  const CourseListScreen({
    super.key,
    required this.api,
    required this.session,
  });

  final ApiClient api;
  final SessionState session;

  @override
  State<CourseListScreen> createState() => _CourseListScreenState();
}

class _CourseListScreenState extends State<CourseListScreen> {
  List<CourseInfo> courses = const [];
  CourseInfo? continueCourse;
  CourseOutlinePayload? continueOutline;
  bool loadingContinueCard = false;
  bool loading = true;
  String error = '';

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = '';
    });
    try {
      final payload = await widget.api.getCourses(widget.session);
      if (mounted) {
        setState(() => courses = payload);
      }
      await _refreshContinueCard(payload);
    } catch (exception) {
      if (mounted) {
        setState(
            () => error = exception.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  Future<void> _refreshContinueCard(List<CourseInfo> items) async {
    if (!mounted) {
      return;
    }
    if (items.isEmpty) {
      setState(() {
        continueCourse = null;
        continueOutline = null;
        loadingContinueCard = false;
      });
      return;
    }
    setState(() {
      loadingContinueCard = true;
      continueCourse = null;
      continueOutline = null;
    });

    CourseInfo? selectedCourse;
    CourseOutlinePayload? selectedOutline;
    for (final course in items) {
      try {
        final outline =
            await widget.api.getCourseOutline(course.id, widget.session);
        if (selectedOutline == null) {
          selectedCourse = course;
          selectedOutline = outline;
        }
        if (outline.resumeLessonId != null) {
          selectedCourse = course;
          selectedOutline = outline;
          break;
        }
      } catch (_) {
        // Course list stays usable even if one outline request fails.
      }
    }

    if (!mounted) {
      return;
    }
    setState(() {
      continueCourse = selectedCourse;
      continueOutline = selectedOutline;
      loadingContinueCard = false;
    });
  }

  Future<void> openCourseOverview(CourseInfo course) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => CourseOverviewScreen(
            api: widget.api, session: widget.session, course: course),
      ),
    );
    if (mounted) {
      await load();
    }
  }

  Future<void> openContinueLesson() async {
    final outline = continueOutline;
    if (outline?.resumeLessonId == null) {
      return;
    }
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => CoursePlayerScreen(
          api: widget.api,
          session: widget.session,
          initialLessonId: outline!.resumeLessonId!,
        ),
      ),
    );
    if (mounted) {
      await load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    if (loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (error.isNotEmpty) {
      return ErrorPanel(text: strings.coursesLoadFailed(error), onRetry: load);
    }
    if (courses.isEmpty) {
      return ErrorPanel(text: strings.noAssignedCourses);
    }
    return RefreshIndicator(
      onRefresh: load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (loadingContinueCard)
            const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: LinearProgressIndicator(),
            ),
          if (continueCourse != null && continueOutline != null)
            Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(strings.resumeCourse,
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    Text(
                      continueCourse!.title,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    LinearProgressIndicator(
                      value: continueOutline!.totalLessons == 0
                          ? 0
                          : continueOutline!.completedLessons /
                              continueOutline!.totalLessons,
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        InfoPill(
                          label: strings.lessonsCompleted(
                            continueOutline!.completedLessons,
                            continueOutline!.totalLessons,
                          ),
                        ),
                        InfoPill(
                          label: strings.progressPercent(
                              continueOutline!.progressPercent),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: [
                        FilledButton.icon(
                          onPressed: continueOutline!.resumeLessonId == null
                              ? null
                              : openContinueLesson,
                          icon: const Icon(Icons.play_circle_fill),
                          label: Text(strings.resumeCourse),
                        ),
                        OutlinedButton.icon(
                          onPressed: () => openCourseOverview(continueCourse!),
                          icon: const Icon(Icons.menu_book),
                          label: Text(strings.lessonOutline),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ...courses.map((course) {
            final imageUrl = resolveMediaUrl(widget.session, course.imageUrl);
            final imageHeaders = resolveMediaHeaders(widget.session, imageUrl);
            return Card(
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () => openCourseOverview(course),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (imageUrl.isNotEmpty)
                      AspectRatio(
                        aspectRatio: 16 / 9,
                        child: Image.network(
                          imageUrl,
                          headers: imageHeaders,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => _CourseCoverFallback(
                            title: course.title,
                          ),
                        ),
                      ),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  course.title,
                                  style: courseCardTitleStyle(context),
                                  maxLines: 3,
                                  overflow: TextOverflow.ellipsis,
                                  softWrap: true,
                                  strutStyle: const StrutStyle(
                                    fontSize: 22,
                                    height: 1.18,
                                    forceStrutHeight: true,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(course.description),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          const Icon(Icons.chevron_right),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class CourseOverviewScreen extends StatefulWidget {
  const CourseOverviewScreen({
    super.key,
    required this.api,
    required this.session,
    required this.course,
  });

  final ApiClient api;
  final SessionState session;
  final CourseInfo course;

  @override
  State<CourseOverviewScreen> createState() => _CourseOverviewScreenState();
}

class _CourseOverviewScreenState extends State<CourseOverviewScreen> {
  CourseOutlinePayload? outline;
  List<TestInfo> tests = const [];
  bool loading = true;
  String error = '';

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = '';
    });
    try {
      final outlinePayload =
          await widget.api.getCourseOutline(widget.course.id, widget.session);

      List<TestInfo> testsPayload = const [];
      try {
        testsPayload = await widget.api.getTests(widget.session);
      } catch (_) {
        testsPayload = const [];
      }

      if (mounted) {
        setState(() {
          outline = outlinePayload;
          tests = testsPayload
              .where((item) => item.courseId == widget.course.id)
              .toList();
        });
      }
    } catch (exception) {
      if (mounted) {
        setState(
            () => error = exception.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  Future<void> openLesson(int lessonId) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => CoursePlayerScreen(
            api: widget.api,
            session: widget.session,
            initialLessonId: lessonId),
      ),
    );
    if (mounted) {
      load();
    }
  }

  Future<void> openAdaptiveTest() async {
    if (tests.isEmpty) {
      return;
    }
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => TestFlowScreen(
            api: widget.api, session: widget.session, testId: tests.first.id),
      ),
    );
    if (mounted) {
      load();
    }
  }

  Future<void> openAttemptHistory() async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AttemptHistoryScreen(
          api: widget.api,
          session: widget.session,
          courseId: widget.course.id,
          courseTitle: widget.course.title,
        ),
      ),
    );
    if (mounted) {
      load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    return Scaffold(
      appBar: AppBar(title: Text(widget.course.title)),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error.isNotEmpty
              ? ErrorPanel(
                  text: strings.courseOutlineLoadFailed(error), onRetry: load)
              : CourseOverviewBody(
                  session: widget.session,
                  course: widget.course,
                  outline: outline!,
                  testCount: tests.length,
                  onOpenLesson: openLesson,
                  onStartTest: openAdaptiveTest,
                  onViewAttemptHistory: openAttemptHistory,
                ),
    );
  }
}

class CourseOverviewBody extends StatelessWidget {
  const CourseOverviewBody({
    super.key,
    required this.session,
    required this.course,
    required this.outline,
    required this.testCount,
    required this.onOpenLesson,
    required this.onStartTest,
    required this.onViewAttemptHistory,
  });

  final SessionState session;
  final CourseInfo course;
  final CourseOutlinePayload outline;
  final int testCount;
  final ValueChanged<int> onOpenLesson;
  final VoidCallback onStartTest;
  final VoidCallback onViewAttemptHistory;

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final sectionGroups = buildOutlineSectionGroups(outline, strings);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  outline.courseTitle,
                  style: courseCardTitleStyle(context),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  softWrap: true,
                  strutStyle: const StrutStyle(
                    fontSize: 22,
                    height: 1.18,
                    forceStrutHeight: true,
                  ),
                ),
                if ((course.imageUrl ?? '').trim().isNotEmpty) ...[
                  const SizedBox(height: 16),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(20),
                    child: AspectRatio(
                      aspectRatio: 16 / 9,
                      child: Image.network(
                        resolveMediaUrl(session, course.imageUrl),
                        headers: resolveMediaHeaders(
                          session,
                          resolveMediaUrl(session, course.imageUrl),
                        ),
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) =>
                            _CourseCoverFallback(title: course.title),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
                const SizedBox(height: 8),
                Text(outline.description),
                const SizedBox(height: 16),
                LinearProgressIndicator(
                    value: outline.totalLessons == 0
                        ? 0
                        : outline.completedLessons / outline.totalLessons),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    InfoPill(
                        label: strings.lessonsCompleted(
                            outline.completedLessons, outline.totalLessons)),
                    InfoPill(
                        label:
                            strings.progressPercent(outline.progressPercent)),
                    if (testCount > 0)
                      InfoPill(label: strings.adaptiveTestsCount(testCount)),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    if (outline.resumeLessonId != null)
                      FilledButton.icon(
                        key: const ValueKey('resume-course-button'),
                        onPressed: () => onOpenLesson(outline.resumeLessonId!),
                        icon: const Icon(Icons.play_circle_fill),
                        label: Text(strings.resumeCourse),
                      ),
                    if (testCount > 0)
                      OutlinedButton.icon(
                        onPressed: onStartTest,
                        icon: const Icon(Icons.quiz_outlined),
                        label: Text(strings.startAdaptiveTest),
                      ),
                    if (testCount > 0)
                      OutlinedButton.icon(
                        key: const ValueKey('course-attempt-history-button'),
                        onPressed: onViewAttemptHistory,
                        icon: const Icon(Icons.history),
                        label: Text(
                          openAttemptHistoryFromCourseLabel(strings),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Text(strings.lessonOutline,
            style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        ...sectionGroups.map(
          (group) => Card(
            key: ValueKey('outline-section-${group.id ?? "general"}'),
            child: Padding(
              padding: EdgeInsets.only(
                top: group.hasSectionTitle ? 8 : 2,
                bottom: 6,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (group.hasSectionTitle) ...[
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              group.title,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                          ),
                          Text(
                            '${group.lessons.length}',
                            style: Theme.of(context).textTheme.labelLarge,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 4),
                  ],
                  ...group.lessons.asMap().entries.map((entry) {
                    final lesson = entry.value;
                    return Column(
                      children: [
                        if (entry.key > 0) const Divider(height: 1),
                        ListTile(
                          key: ValueKey('lesson-card-${lesson.id}'),
                          title: Text(lesson.title),
                          subtitle: Text(
                            lesson.summary.isEmpty
                                ? strings.pagesWithDuration(
                                    lesson.pageCount,
                                    formatDurationLabel(lesson.durationMinutes),
                                  )
                                : '${strings.pagesWithDuration(lesson.pageCount, formatDurationLabel(lesson.durationMinutes))}\n${lesson.summary}',
                          ),
                          isThreeLine: lesson.summary.isNotEmpty,
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                lesson.isCompleted
                                    ? Icons.check_circle
                                    : Icons.radio_button_unchecked,
                                color: lesson.isCompleted
                                    ? Theme.of(context).colorScheme.primary
                                    : null,
                              ),
                              if (lesson.hasVideo)
                                const Icon(Icons.play_circle_outline, size: 18),
                            ],
                          ),
                          onTap: () => onOpenLesson(lesson.id),
                        ),
                      ],
                    );
                  }),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class AssignmentSubmissionDraft {
  const AssignmentSubmissionDraft({
    required this.textAnswer,
    required this.linkAnswer,
    required this.fileUrls,
    required this.updatedAtIso,
  });

  final String textAnswer;
  final String linkAnswer;
  final List<String> fileUrls;
  final String updatedAtIso;

  Map<String, dynamic> toJson() => {
        'text_answer': textAnswer,
        'link_answer': linkAnswer,
        'file_urls': fileUrls,
        'updated_at': updatedAtIso,
      };

  static AssignmentSubmissionDraft? fromJson(Map<String, dynamic>? json) {
    if (json == null) return null;
    return AssignmentSubmissionDraft(
      textAnswer: (json['text_answer'] as String? ?? '').trim(),
      linkAnswer: (json['link_answer'] as String? ?? '').trim(),
      fileUrls: (json['file_urls'] as List<dynamic>? ?? const [])
          .map((item) => '$item')
          .where((item) => item.trim().isNotEmpty)
          .toList(),
      updatedAtIso: (json['updated_at'] as String? ?? '').trim(),
    );
  }
}

class SubmissionValidationResult {
  const SubmissionValidationResult({
    this.answerError,
    this.linkError,
    this.generalError,
  });

  final String? answerError;
  final String? linkError;
  final String? generalError;

  bool get hasErrors => answerError != null || linkError != null || generalError != null;
}

String _draftStorageKey(int assignmentId) =>
    'assignment_submission_draft_$assignmentId';

Future<void> _saveSubmissionDraft(
  int assignmentId,
  AssignmentSubmissionDraft draft,
) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString(_draftStorageKey(assignmentId), jsonEncode(draft.toJson()));
}

Future<AssignmentSubmissionDraft?> _loadSubmissionDraft(int assignmentId) async {
  final prefs = await SharedPreferences.getInstance();
  final raw = prefs.getString(_draftStorageKey(assignmentId));
  if (raw == null || raw.trim().isEmpty) {
    return null;
  }
  try {
    return AssignmentSubmissionDraft.fromJson(jsonMap(jsonDecode(raw)));
  } catch (_) {
    return null;
  }
}

Future<void> _clearSubmissionDraft(int assignmentId) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.remove(_draftStorageKey(assignmentId));
}

void _trackSubmissionAnalytics(String eventName, Map<String, dynamic> payload) {
  if (!kDebugMode) {
    return;
  }
  debugPrint('analytics::$eventName::$payload');
}

SubmissionValidationResult validateSubmissionForm({
  required bool isRu,
  required String answer,
  required String link,
}) {
  final normalizedAnswer = answer.trim();
  final normalizedLink = link.trim();
  if (normalizedAnswer.length < 10) {
    return SubmissionValidationResult(
      answerError: isRu
          ? 'Добавьте более подробный ответ (минимум 10 символов).'
          : 'Please provide a fuller answer (at least 10 characters).',
    );
  }
  if (normalizedAnswer.length > 4000) {
    return SubmissionValidationResult(
      answerError: isRu
          ? 'Ответ слишком длинный (максимум 4000 символов).'
          : 'Response is too long (maximum 4000 characters).',
    );
  }
  if (normalizedLink.isNotEmpty) {
    final parsed = Uri.tryParse(normalizedLink);
    final valid = parsed != null &&
        (parsed.scheme == 'http' || parsed.scheme == 'https') &&
        parsed.host.isNotEmpty;
    if (!valid) {
      return SubmissionValidationResult(
        linkError: isRu
            ? 'Укажите корректную ссылку с http/https.'
            : 'Provide a valid http/https link.',
      );
    }
  }
  return const SubmissionValidationResult();
}

Future<void> _openAssignmentSubmitSheet(
  BuildContext context, {
  required ApiClient api,
  required SessionState session,
  required AssignmentInfo assignment,
  required AssignmentSubmissionInfo? currentSubmission,
  required Future<void> Function(
    int assignmentId,
    String textAnswer,
    String? linkAnswer,
    List<String> fileUrls,
  ) onSubmit,
}) async {
  final answerController =
      TextEditingController(text: currentSubmission?.textAnswer ?? '');
  final linkController =
      TextEditingController(text: currentSubmission?.linkAnswer ?? '');
  final attachmentUrls = <String>[...(currentSubmission?.fileUrls ?? const <String>[])];
  var busy = false;
  var uploading = false;
  String? answerError;
  String? linkError;
  String? generalError;
  String? draftInfo;
  Timer? autosaveDebounce;

  void scheduleDraftSave(StateSetter setModalState) {
    autosaveDebounce?.cancel();
    autosaveDebounce = Timer(const Duration(milliseconds: 650), () async {
      final draft = AssignmentSubmissionDraft(
        textAnswer: answerController.text,
        linkAnswer: linkController.text,
        fileUrls: attachmentUrls,
        updatedAtIso: DateTime.now().toIso8601String(),
      );
      await _saveSubmissionDraft(assignment.id, draft);
      if (context.mounted) {
        setModalState(() {
          draftInfo = context.strings.isRu ? 'Черновик сохранён' : 'Draft saved';
        });
      }
    });
  }

  Future<void> tryUploadFile(StateSetter setModalState) async {
    final picked = await FilePicker.platform.pickFiles(
      withData: true,
      allowMultiple: false,
      type: FileType.custom,
      allowedExtensions: const [
        'pdf',
        'doc',
        'docx',
        'ppt',
        'pptx',
        'xls',
        'xlsx',
        'txt',
        'png',
        'jpg',
        'jpeg',
        'gif',
        'webp'
      ],
    );
    if (picked == null || picked.files.isEmpty) return;
    setModalState(() {
      uploading = true;
      generalError = null;
    });
    try {
      final uploaded = await api.uploadAssignmentSubmissionFile(
        session,
        assignmentId: assignment.id,
        file: picked.files.first,
      );
      final url = (uploaded['file_url'] ?? '').trim();
      if (url.isNotEmpty) {
        attachmentUrls.add(url);
        scheduleDraftSave(setModalState);
      }
    } catch (error) {
      setModalState(() {
        generalError = error.toString();
      });
    } finally {
      setModalState(() => uploading = false);
    }
  }

  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (sheetContext) {
      return StatefulBuilder(
        builder: (modalContext, setModalState) {
          Future<void> hydrateDraftIfNeeded() async {
            if (draftInfo != null) return;
            final draft = await _loadSubmissionDraft(assignment.id);
            if (draft == null) {
              setModalState(() => draftInfo = '');
              return;
            }
            final shouldRestore = await showDialog<bool>(
                  context: sheetContext,
                  builder: (dialogContext) => AlertDialog(
                    title: Text(context.strings.isRu
                        ? 'Восстановить черновик?'
                        : 'Restore draft?'),
                    content: Text(context.strings.isRu
                        ? 'Найден несохранённый черновик ответа.'
                        : 'We found an unsent draft for this assignment.'),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.of(dialogContext).pop(false),
                        child: Text(context.strings.isRu ? 'Нет' : 'No'),
                      ),
                      FilledButton(
                        onPressed: () => Navigator.of(dialogContext).pop(true),
                        child: Text(context.strings.isRu ? 'Да' : 'Yes'),
                      ),
                    ],
                  ),
                ) ??
                false;
            if (!shouldRestore) {
              await _clearSubmissionDraft(assignment.id);
              setModalState(() => draftInfo = '');
              return;
            }
            answerController.text = draft.textAnswer;
            linkController.text = draft.linkAnswer;
            attachmentUrls
              ..clear()
              ..addAll(draft.fileUrls);
            setModalState(() {
              draftInfo = context.strings.isRu
                  ? 'Черновик восстановлен'
                  : 'Draft restored';
            });
          }

          if (draftInfo == null) {
            unawaited(hydrateDraftIfNeeded());
          }

          return Padding(
            padding: EdgeInsets.only(
              left: 16,
              right: 16,
              top: 16,
              bottom: MediaQuery.of(sheetContext).viewInsets.bottom + 16,
            ),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: answerController,
                    minLines: 5,
                    maxLines: 10,
                    onChanged: (_) => scheduleDraftSave(setModalState),
                    decoration: InputDecoration(
                      labelText: context.strings.isRu ? 'Ответ *' : 'Response *',
                      helperText: context.strings.isRu
                          ? 'Опишите решение, шаги и итог. Пример: "Сделал ... Проверил ... Вывод ..."'
                          : 'Describe your approach, execution steps, and result.',
                      errorText: answerError,
                      counterText: '${answerController.text.trim().length}/4000',
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: linkController,
                    onChanged: (_) => scheduleDraftSave(setModalState),
                    decoration: InputDecoration(
                      labelText: context.strings.isRu
                          ? 'Ссылка (опционально)'
                          : 'Link (optional)',
                      helperText: context.strings.isRu
                          ? 'Например: https://drive.google.com/...'
                          : 'For example: https://drive.google.com/...',
                      errorText: linkError,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      OutlinedButton.icon(
                        onPressed: uploading || busy
                            ? null
                            : () => tryUploadFile(setModalState),
                        icon: uploading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.attach_file),
                        label: Text(context.strings.isRu
                            ? 'Прикрепить файл'
                            : 'Attach file'),
                      ),
                      if (draftInfo != null && draftInfo!.isNotEmpty)
                        Chip(label: Text(draftInfo!)),
                    ],
                  ),
                  if (attachmentUrls.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    ...attachmentUrls.asMap().entries.map((entry) {
                      final index = entry.key;
                      final url = entry.value;
                      return ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text(url, maxLines: 1, overflow: TextOverflow.ellipsis),
                        trailing: IconButton(
                          onPressed: busy
                              ? null
                              : () {
                                  setModalState(() => attachmentUrls.removeAt(index));
                                  scheduleDraftSave(setModalState);
                                },
                          icon: const Icon(Icons.close),
                        ),
                      );
                    }),
                  ],
                  if (generalError != null) ...[
                    const SizedBox(height: 8),
                    Text(generalError!,
                        style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ],
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: busy
                              ? null
                              : () async {
                                  await _clearSubmissionDraft(assignment.id);
                                  if (sheetContext.mounted) {
                                    Navigator.of(sheetContext).pop();
                                  }
                                },
                          child: Text(context.strings.isRu ? 'Отмена' : 'Cancel'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: busy
                              ? null
                              : () async {
                                  final validation = validateSubmissionForm(
                                    isRu: context.strings.isRu,
                                    answer: answerController.text,
                                    link: linkController.text,
                                  );
                                  setModalState(() {
                                    answerError = validation.answerError;
                                    linkError = validation.linkError;
                                    generalError = validation.generalError;
                                  });
                                  if (validation.hasErrors) {
                                    return;
                                  }
                                  final confirm = await showDialog<bool>(
                                        context: sheetContext,
                                        builder: (dialogContext) => AlertDialog(
                                          title: Text(context.strings.isRu
                                              ? 'Подтвердить отправку'
                                              : 'Confirm submission'),
                                          content: Text(context.strings.isRu
                                              ? 'После отправки наставник увидит вашу работу для проверки.'
                                              : 'Your mentor will receive this submission for review.'),
                                          actions: [
                                            TextButton(
                                              onPressed: () =>
                                                  Navigator.of(dialogContext).pop(false),
                                              child: Text(
                                                  context.strings.isRu ? 'Назад' : 'Back'),
                                            ),
                                            FilledButton(
                                              onPressed: () =>
                                                  Navigator.of(dialogContext).pop(true),
                                              child: Text(context.strings.isRu
                                                  ? 'Отправить'
                                                  : 'Submit'),
                                            ),
                                          ],
                                        ),
                                      ) ??
                                      false;
                                  if (!confirm) return;
                                  setModalState(() => busy = true);
                                  _trackSubmissionAnalytics(
                                    'assignment_submit_started',
                                    {'assignment_id': assignment.id},
                                  );
                                  try {
                                    await onSubmit(
                                      assignment.id,
                                      answerController.text.trim(),
                                      linkController.text.trim().isEmpty
                                          ? null
                                          : linkController.text.trim(),
                                      attachmentUrls,
                                    );
                                    await _clearSubmissionDraft(assignment.id);
                                    _trackSubmissionAnalytics(
                                      'assignment_submit_succeeded',
                                      {'assignment_id': assignment.id},
                                    );
                                    if (!sheetContext.mounted) return;
                                    Navigator.of(sheetContext).pop();
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text(context.strings.isRu
                                            ? 'Работа отправлена на проверку.'
                                            : 'Submission sent for review.'),
                                      ),
                                    );
                                  } catch (error) {
                                    _trackSubmissionAnalytics(
                                      'assignment_submit_failed',
                                      {
                                        'assignment_id': assignment.id,
                                        'error': error.toString(),
                                      },
                                    );
                                    setModalState(() {
                                      generalError = error.toString();
                                      busy = false;
                                    });
                                  }
                                },
                          icon: busy
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.send),
                          label: Text(
                            context.strings.isRu
                                ? 'Отправить на проверку'
                                : 'Submit for review',
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      );
    },
  );
  autosaveDebounce?.cancel();
}

class CoursePlayerScreen extends StatefulWidget {
  const CoursePlayerScreen({
    super.key,
    required this.api,
    required this.session,
    required this.initialLessonId,
  });

  final ApiClient api;
  final SessionState session;
  final int initialLessonId;

  @override
  State<CoursePlayerScreen> createState() => _CoursePlayerScreenState();
}

class _CoursePlayerScreenState extends State<CoursePlayerScreen> {
  LessonPlayerPayload? payload;
  AssignmentInfo? lessonAssignment;
  AssignmentSubmissionInfo? lessonSubmission;
  bool loading = true;
  String error = '';
  int lessonId = 0;
  int currentPageIndex = 0;
  Set<String> completedPageIds = <String>{};
  int lastVideoPositionSeconds = 0;
  final Map<String, int> videoPositionsByUrl = <String, int>{};

  @override
  void initState() {
    super.initState();
    lessonId = widget.initialLessonId;
    loadLesson(lessonId);
  }

  Future<void> loadLesson(int targetLessonId) async {
    setState(() {
      loading = true;
      error = '';
    });
    try {
      final nextPayload =
          await widget.api.getLessonPlayer(targetLessonId, widget.session);
      List<AssignmentInfo> assignmentList = const [];
      try {
        assignmentList = await widget.api.getAssignments(
          widget.session,
          courseId: nextPayload.courseId,
          lessonId: targetLessonId,
        );
      } catch (_) {
        assignmentList = const [];
      }
      AssignmentInfo? linkedAssignment;
      for (final item in assignmentList) {
        if (item.isActive) {
          linkedAssignment = item;
          break;
        }
      }
      AssignmentSubmissionInfo? linkedSubmission;
      if (linkedAssignment != null) {
        try {
          final submissions = await widget.api
              .getAssignmentSubmissions(linkedAssignment.id, widget.session);
          if (submissions.isNotEmpty) {
            linkedSubmission = submissions.first;
          }
        } catch (_) {
          linkedSubmission = null;
        }
      }
      if (mounted) {
        setState(() {
          lessonId = targetLessonId;
          payload = nextPayload;
          lessonAssignment = linkedAssignment;
          lessonSubmission = linkedSubmission;
          currentPageIndex = nextPayload.pages.isEmpty
              ? 0
              : nextPayload.state.currentPageIndex
                  .clamp(0, nextPayload.pages.length - 1)
                  .toInt();
          completedPageIds = nextPayload.state.completedPageIds.toSet();
          lastVideoPositionSeconds = nextPayload.state.lastVideoPositionSeconds;
          videoPositionsByUrl.clear();
        });
      }
    } catch (exception) {
      if (mounted) {
        setState(
            () => error = exception.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  Future<void> submitLessonAssignment(
    int assignmentId,
    String textAnswer,
    String? linkAnswer,
    List<String> fileUrls,
  ) async {
    final submission = await widget.api.submitAssignment(
      assignmentId,
      widget.session,
      textAnswer: textAnswer,
      linkAnswer: linkAnswer,
      fileUrls: fileUrls,
    );
    if (!mounted) {
      return;
    }
    setState(() {
      lessonSubmission = submission;
    });
  }

  Future<void> persistState({
    int? pageIndex,
    Set<String>? completedIds,
    int? videoPositionSeconds,
    bool? isCompleted,
  }) async {
    final currentPayload = payload;
    if (currentPayload == null) {
      return;
    }
    try {
      await widget.api.saveLessonState(
        currentPayload.lessonId,
        widget.session,
        currentPageIndex: pageIndex ?? currentPageIndex,
        completedPageIds: (completedIds ?? completedPageIds).toList(),
        lastVideoPositionSeconds:
            videoPositionSeconds ?? lastVideoPositionSeconds,
        isCompleted: isCompleted,
      );
    } catch (_) {
      // Keep the player responsive; the next reload will recover the latest state.
    }
  }

  Set<String> markedCurrentPageComplete() {
    final currentPayload = payload;
    if (currentPayload == null || currentPayload.pages.isEmpty) {
      return completedPageIds;
    }
    return {...completedPageIds, currentPayload.pages[currentPageIndex].pageId};
  }

  void goToPage(int targetIndex) {
    final currentPayload = payload;
    if (currentPayload == null || currentPayload.pages.isEmpty) {
      return;
    }
    final safeIndex =
        targetIndex.clamp(0, currentPayload.pages.length - 1).toInt();
    final nextCompleted = targetIndex > currentPageIndex
        ? markedCurrentPageComplete()
        : completedPageIds;
    setState(() {
      completedPageIds = nextCompleted;
      currentPageIndex = safeIndex;
    });
    unawaited(persistState(pageIndex: safeIndex, completedIds: nextCompleted));
  }

  void goToPreviousPage() {
    if (currentPageIndex > 0) {
      goToPage(currentPageIndex - 1);
    }
  }

  void goToNextPage() {
    unawaited(_goToNextPageAsync());
  }

  Future<void> _goToNextPageAsync() async {
    final currentPayload = payload;
    if (currentPayload == null || currentPayload.pages.isEmpty) {
      return;
    }
    if (currentPageIndex >= currentPayload.pages.length - 1) {
      await markLessonComplete(openNextLessonAfterCompletion: true);
      return;
    }
    goToPage(currentPageIndex + 1);
  }

  int savedVideoPositionFor(String videoUrl) {
    final remembered = videoPositionsByUrl[videoUrl];
    if (remembered != null) {
      return remembered;
    }
    if (lastVideoPositionSeconds <= 0) {
      return 0;
    }
    if (videoPositionsByUrl.isEmpty) {
      videoPositionsByUrl[videoUrl] = lastVideoPositionSeconds;
      return lastVideoPositionSeconds;
    }
    return 0;
  }

  void onVideoPositionChanged(String videoUrl, int seconds) {
    if (seconds < 0 || videoUrl.trim().isEmpty) {
      return;
    }
    if (videoPositionsByUrl[videoUrl] == seconds) {
      return;
    }
    videoPositionsByUrl[videoUrl] = seconds;
    lastVideoPositionSeconds = seconds;
    unawaited(persistState(videoPositionSeconds: seconds));
  }

  Future<void> openLesson(int targetLessonId) async {
    await persistState();
    if (!mounted) {
      return;
    }
    await loadLesson(targetLessonId);
  }

  Future<void> markLessonComplete({
    bool openNextLessonAfterCompletion = false,
  }) async {
    return _markLessonCompleteInternal(
      openNextLessonAfterCompletion: openNextLessonAfterCompletion,
    );
  }

  Future<void> _markLessonCompleteInternal({
    bool openNextLessonAfterCompletion = false,
  }) async {
    final currentPayload = payload;
    if (currentPayload == null) {
      return;
    }
    final nextLessonId = currentPayload.nextLessonId;
    final allPageIds = currentPayload.pages.map((page) => page.pageId).toSet();
    setState(() => completedPageIds = allPageIds);
    await persistState(
      pageIndex:
          currentPayload.pages.isEmpty ? 0 : currentPayload.pages.length - 1,
      completedIds: allPageIds,
      isCompleted: true,
    );
    if (!mounted) {
      return;
    }
    if (openNextLessonAfterCompletion && nextLessonId != null) {
      await loadLesson(nextLessonId);
      return;
    }
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(context.strings.lessonCompleted)));
    await loadLesson(currentPayload.lessonId);
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final currentPayload = payload;
    return Scaffold(
      appBar: AppBar(
          title: Text(currentPayload?.courseTitle ?? strings.coursePlayer)),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error.isNotEmpty
              ? ErrorPanel(
                  text: strings.lessonPlayerLoadFailed(error),
                  onRetry: () => loadLesson(lessonId))
              : CoursePlayerBody(
                  session: widget.session,
                  payload: currentPayload!,
                  lessonAssignment: lessonAssignment,
                  lessonSubmission: lessonSubmission,
                  currentPageIndex: currentPageIndex,
                  completedPageIds: completedPageIds,
                  savedVideoPositionFor: savedVideoPositionFor,
                  onGoToPage: goToPage,
                  onGoToPreviousPage: goToPreviousPage,
                  onGoToNextPage: goToNextPage,
                  onOpenLesson: openLesson,
                  onMarkComplete: _markLessonCompleteInternal,
                  onSubmitAssignment: submitLessonAssignment,
                  onVideoPositionChanged: onVideoPositionChanged,
                ),
    );
  }
}

class CoursePlayerBody extends StatefulWidget {
  const CoursePlayerBody({
    super.key,
    required this.session,
    required this.payload,
    required this.lessonAssignment,
    required this.lessonSubmission,
    required this.currentPageIndex,
    required this.completedPageIds,
    required this.savedVideoPositionFor,
    required this.onGoToPage,
    required this.onGoToPreviousPage,
    required this.onGoToNextPage,
    required this.onOpenLesson,
    required this.onMarkComplete,
    required this.onSubmitAssignment,
    required this.onVideoPositionChanged,
    this.videoPreviewModes = const {},
  });

  final SessionState session;
  final LessonPlayerPayload payload;
  final AssignmentInfo? lessonAssignment;
  final AssignmentSubmissionInfo? lessonSubmission;
  final int currentPageIndex;
  final Set<String> completedPageIds;
  final int Function(String videoUrl) savedVideoPositionFor;
  final ValueChanged<int> onGoToPage;
  final VoidCallback onGoToPreviousPage;
  final VoidCallback onGoToNextPage;
  final ValueChanged<int> onOpenLesson;
  final Future<void> Function() onMarkComplete;
  final Future<void> Function(
    int assignmentId,
    String textAnswer,
    String? linkAnswer,
    List<String> fileUrls,
  ) onSubmitAssignment;
  final void Function(String videoUrl, int seconds) onVideoPositionChanged;
  final Map<String, InlineVideoPreviewMode> videoPreviewModes;

  @override
  State<CoursePlayerBody> createState() => _CoursePlayerBodyState();
}

class _CoursePlayerBodyState extends State<CoursePlayerBody> {
  bool _practiceExpanded = false;

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final pageCount = widget.payload.pages.length;
    final safePageIndex =
        pageCount == 0 ? 0 : widget.currentPageIndex.clamp(0, pageCount - 1).toInt();
    final currentPage = pageCount == 0 ? null : widget.payload.pages[safePageIndex];
    final progressValue =
        pageCount == 0 ? 0.0 : (safePageIndex + 1) / pageCount;
    final completedCount = widget.completedPageIds.length.clamp(0, pageCount);
    final isLastPage = pageCount > 0 && safePageIndex >= pageCount - 1;
    CourseOutlineLesson? nextLesson;
    if (widget.payload.nextLessonId != null) {
      for (final lesson in widget.payload.outline.lessons) {
        if (lesson.id == widget.payload.nextLessonId) {
          nextLesson = lesson;
          break;
        }
      }
    }

    Future<void> showContentsSheet() async {
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (sheetContext) => SafeArea(
          child: _ContentsSheet(
            payload: widget.payload,
            currentPageIndex: safePageIndex,
            completedPageIds: widget.completedPageIds,
            onOpenLesson: (lessonId) {
              Navigator.of(sheetContext).pop();
              widget.onOpenLesson(lessonId);
            },
            onOpenPage: (pageIndex) {
              Navigator.of(sheetContext).pop();
              widget.onGoToPage(pageIndex);
            },
          ),
        ),
      );
    }

    if (currentPage == null) {
      return ErrorPanel(text: strings.noPagesYet);
    }

    final assignment = widget.lessonAssignment;
    final submission = widget.lessonSubmission;
    String normalizeText(String value) =>
        value.trim().toLowerCase().replaceAll(RegExp(r'\s+'), ' ');
    final lessonTitleNorm = normalizeText(widget.payload.lessonTitle);
    final lessonSummaryNorm = normalizeText(widget.payload.summary);
    final assignmentTitleNorm = normalizeText(assignment?.title ?? '');
    final assignmentDescriptionNorm = normalizeText(assignment?.description ?? '');
    final showPracticeTitle = assignment != null && assignmentTitleNorm != lessonTitleNorm;
    final showPracticeDescription = assignment != null &&
        assignmentDescriptionNorm.isNotEmpty &&
        assignmentDescriptionNorm != lessonSummaryNorm;
    final rawStatus = (submission?.status ?? 'not_started').toLowerCase();
    final statusLabel = strings.assignmentStatusLabel(rawStatus);
    final practiceCta = rawStatus == 'not_started'
        ? (strings.isRu ? 'Отправить решение' : 'Submit solution')
        : (strings.isRu ? 'Обновить решение' : 'Update submission');
    final practicePageIndex = widget.payload.pages.indexWhere((page) => page.isPractice);
    final fallbackPracticePageIndex = widget.payload.pages.indexWhere((page) {
      final title = page.pageTitle.trim().toLowerCase();
      return title.contains('практик') || title.contains('practice');
    });
    final showPracticeOnCurrentPage = practicePageIndex >= 0
        ? safePageIndex == practicePageIndex
        : fallbackPracticePageIndex >= 0
            ? safePageIndex == fallbackPracticePageIndex
            : isLastPage;

    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(widget.payload.courseTitle,
                          style: Theme.of(context).textTheme.labelLarge),
                      const SizedBox(height: 4),
                      Text(widget.payload.lessonTitle,
                          style: Theme.of(context).textTheme.headlineSmall),
                      const SizedBox(height: 8),
                      Text(
                        '${currentPage.chapterTitle} / ${currentPage.pageTitle}',
                        key: const ValueKey('current-page-breadcrumb'),
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 14),
                      LinearProgressIndicator(value: progressValue),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          InfoPill(
                              label:
                                  strings.pageOf(safePageIndex + 1, pageCount)),
                          InfoPill(
                              label: strings.pagesCompleted(completedCount)),
                          InfoPill(label: formatDurationLabel(widget.payload.durationMinutes)),
                        ],
                      ),
                      if (widget.payload.summary.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: Theme.of(context)
                                .colorScheme
                                .secondaryContainer
                                .withValues(alpha: 0.45),
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: Text(widget.payload.summary),
                        ),
                      ],
                      const SizedBox(height: 16),
                      OutlinedButton.icon(
                        onPressed: showContentsSheet,
                        icon: const Icon(Icons.list_alt),
                        label: Text(strings.contents),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(currentPage.chapterTitle,
                          style: Theme.of(context).textTheme.labelLarge),
                      const SizedBox(height: 4),
                      Text(currentPage.pageTitle,
                          key: const ValueKey('current-page-title'),
                          style: Theme.of(context).textTheme.headlineSmall),
                      const SizedBox(height: 16),
                      ...currentPage.blocks.map(
                        (block) => Padding(
                          padding: const EdgeInsets.only(bottom: 16),
                          child: _LessonBlockView(
                            session: widget.session,
                            block: block,
                            savedVideoPositionFor: widget.savedVideoPositionFor,
                            onVideoPositionChanged: widget.onVideoPositionChanged,
                            previewMode: block.url == null
                                ? null
                                : widget.videoPreviewModes[block.url!],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (assignment != null && showPracticeOnCurrentPage) ...[
                const SizedBox(height: 12),
                Card(
                  child: ExpansionTile(
                    key: const ValueKey('lesson-practice-tile'),
                    initiallyExpanded: _practiceExpanded,
                    onExpansionChanged: (value) =>
                        setState(() => _practiceExpanded = value),
                    title: Text(
                      strings.isRu ? 'Практика: $statusLabel' : 'Practice: $statusLabel',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    subtitle: Text(
                      strings.isRu
                          ? 'Финальный шаг этого урока'
                          : 'Final step for this lesson',
                    ),
                    childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    children: [
                      if (showPracticeTitle) ...[
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            assignment.title,
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                        ),
                        const SizedBox(height: 6),
                      ],
                      if (showPracticeDescription) ...[
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(assignment.description),
                        ),
                        const SizedBox(height: 8),
                      ],
                      if ((submission?.reviewerComment ?? '').trim().isNotEmpty) ...[
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            strings.isRu
                                ? 'Комментарий куратора: ${submission!.reviewerComment!}'
                                : 'Curator comment: ${submission!.reviewerComment!}',
                          ),
                        ),
                        const SizedBox(height: 8),
                      ],
                      if (submission?.reviewerGrade != null) ...[
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            strings.isRu
                                ? 'Оценка: ${submission!.reviewerGrade}'
                                : 'Grade: ${submission!.reviewerGrade}',
                          ),
                        ),
                        const SizedBox(height: 8),
                      ],
                      Align(
                        alignment: Alignment.centerLeft,
                        child: OutlinedButton.icon(
                          onPressed: () => _openAssignmentSubmitSheet(
                            context,
                            api: ApiClient(baseUrl: widget.session.baseUrl),
                            session: widget.session,
                            assignment: assignment,
                            currentSubmission: submission,
                            onSubmit: widget.onSubmitAssignment,
                          ),
                          icon: const Icon(Icons.assignment_outlined),
                          label: Text(practiceCta),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        SafeArea(
          top: false,
          child: Container(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              border: Border(
                  top: BorderSide(color: Theme.of(context).dividerColor)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: isLastPage
                      ? [
                          Container(
                            key: const ValueKey('lesson-transition-card'),
                            width: double.infinity,
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: Theme.of(context)
                                  .colorScheme
                                  .secondaryContainer
                                  .withValues(alpha: 0.4),
                              borderRadius: BorderRadius.circular(18),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  strings.lastPageReached,
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  nextLesson == null
                                      ? strings.noMoreLessons
                                      : strings
                                          .openNextLesson(nextLesson.title),
                                ),
                                if (nextLesson != null) ...[
                                  const SizedBox(height: 4),
                                  Text(
                                    strings.nextLessonAvailable,
                                    style:
                                        Theme.of(context).textTheme.bodySmall,
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ]
                      : [],
                ),
                if (isLastPage) const SizedBox(height: 8),
                Row(
                  children: [
                    if (safePageIndex > 0) ...[
                      Expanded(
                        child: OutlinedButton.icon(
                          key: const ValueKey('previous-page-button'),
                          onPressed: widget.onGoToPreviousPage,
                          icon: const Icon(Icons.chevron_left),
                          label: Text(strings.previousPage),
                        ),
                      ),
                      const SizedBox(width: 12),
                    ],
                    Expanded(
                      child: FilledButton.icon(
                        key: const ValueKey('next-page-button'),
                        onPressed: widget.onGoToNextPage,
                        icon: Icon(isLastPage
                            ? (nextLesson == null
                                ? Icons.check_circle
                                : Icons.menu_book)
                            : Icons.chevron_right),
                        label: Text(
                          isLastPage
                              ? (nextLesson == null
                                  ? strings.completeLesson
                                  : strings.nextLesson)
                              : strings.nextPage,
                        ),
                      ),
                    ),
                  ],
                ),
                if (isLastPage && nextLesson == null) ...[
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      key: const ValueKey('mark-complete-button'),
                      onPressed: () => unawaited(widget.onMarkComplete()),
                      child: Text(strings.markLessonComplete),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class TestFlowScreen extends StatefulWidget {
  const TestFlowScreen({
    super.key,
    required this.api,
    required this.session,
    required this.testId,
  });

  final ApiClient api;
  final SessionState session;
  final int testId;

  @override
  State<TestFlowScreen> createState() => _TestFlowScreenState();
}

class _TestFlowScreenState extends State<TestFlowScreen> {
  Map<String, dynamic>? result;
  Map<String, dynamic>? question;
  Map<String, dynamic>? feedback;
  int? attemptId;
  int? selectedAnswerId;
  DateTime? questionShownAt;
  bool busy = false;
  String error = '';

  Future<void> start() async {
    setState(() {
      busy = true;
      error = '';
      result = null;
      question = null;
      feedback = null;
      selectedAnswerId = null;
    });
    try {
      final started =
          await widget.api.startAttempt(widget.testId, widget.session);
      attemptId = started['attempt_id'] as int;
      await loadNextQuestion();
    } catch (exception) {
      if (mounted) {
        setState(
            () => error = exception.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  Future<void> loadNextQuestion() async {
    if (attemptId == null) {
      return;
    }
    setState(() {
      busy = true;
      error = '';
      feedback = null;
    });
    try {
      final nextQuestion =
          await widget.api.getAttemptQuestion(attemptId!, widget.session);
      if (!mounted) {
        return;
      }
      if (nextQuestion == null) {
        await finishAttempt();
        return;
      }
      setState(() {
        question = nextQuestion;
        selectedAnswerId = null;
        questionShownAt = DateTime.now();
      });
    } catch (exception) {
      if (mounted) {
        setState(
            () => error = exception.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  int get responseSeconds {
    if (questionShownAt == null) {
      return 1;
    }
    return DateTime.now().difference(questionShownAt!).inSeconds.clamp(1, 3600);
  }

  Future<void> submitAnswer() async {
    if (attemptId == null || selectedAnswerId == null || question == null) {
      return;
    }
    setState(() {
      busy = true;
      error = '';
    });
    try {
      final submit = await widget.api.submitAttemptAnswer(
        attemptId!,
        widget.session,
        questionId: question!['id'] as int,
        answerOptionId: selectedAnswerId!,
        responseSeconds: responseSeconds,
      );
      if (mounted) {
        setState(() => feedback = submit);
      }
    } catch (exception) {
      if (mounted) {
        setState(
            () => error = exception.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  Future<void> continueAdaptiveFlow() async {
    if ((feedback?['remaining_questions'] as int? ?? 0) > 0) {
      await loadNextQuestion();
      return;
    }
    await finishAttempt();
  }

  Future<void> finishAttempt() async {
    if (attemptId == null) {
      return;
    }
    setState(() {
      busy = true;
      error = '';
    });
    try {
      final finished =
          await widget.api.finishAttempt(attemptId!, widget.session);
      if (mounted) {
        setState(() {
          result = finished;
          feedback = null;
        });
      }
    } catch (exception) {
      if (mounted) {
        setState(
            () => error = exception.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  Future<void> openRecommendation(RecommendationInfo item) async {
    if (item.lessonId != null) {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CoursePlayerScreen(
            api: widget.api,
            session: widget.session,
            initialLessonId: item.lessonId!,
          ),
        ),
      );
      return;
    }
    if (item.courseId != null) {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CourseOverviewScreen(
            api: widget.api,
            session: widget.session,
            course: CourseInfo(
              id: item.courseId!,
              title: item.courseTitle.trim().isNotEmpty
                  ? item.courseTitle
                  : context.strings.courseFallback,
              description: '',
              imageUrl: null,
            ),
          ),
        ),
      );
      return;
    }
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(recommendationUnavailableLabel(context.strings))),
    );
  }

  Future<void> openAttemptHistory() async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AttemptHistoryScreen(
          api: widget.api,
          session: widget.session,
        ),
      ),
    );
  }

  Widget buildAdaptiveResult(AppStrings strings) {
    final weakTopics =
        (result!['weak_topics'] as List<dynamic>? ?? const <dynamic>[])
            .map((item) => jsonMap(item))
            .toList();
    final recommendations =
        (result!['recommendations'] as List<dynamic>? ?? const <dynamic>[])
            .map((item) => RecommendationInfo.fromJson(jsonMap(item)))
            .toList();
    final difficultyPath =
        (result!['difficulty_path'] as List<dynamic>? ?? const <dynamic>[])
            .map((item) => item as int)
            .toList();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                    strings.scorePercent(result!['score_percent'] as int? ?? 0),
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 8),
                Text(strings.correctAnswersCount(
                  result!['correct_answers'] as int? ?? 0,
                  result!['total_questions'] as int? ?? 0,
                )),
                const SizedBox(height: 4),
                Text(strings.averageResponseTime(
                    result!['average_response_seconds'] as int? ?? 0)),
                const SizedBox(height: 4),
                Text(strings
                    .finalDifficulty(result!['final_difficulty'] as int? ?? 1)),
                if (difficultyPath.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(strings.difficultyPath(difficultyPath)),
                ],
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  key: const ValueKey('attempt-history-button'),
                  onPressed: () => unawaited(openAttemptHistory()),
                  icon: const Icon(Icons.history),
                  label: Text(viewAttemptHistoryLabel(strings)),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(strings.generatedRecommendations,
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                if (recommendations.isEmpty && weakTopics.isEmpty)
                  Text(strings.noWeakTopics)
                else ...[
                  if (recommendations.isEmpty && weakTopics.isNotEmpty)
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: weakTopics
                          .map(
                            (item) => Chip(
                              label: Text(
                                '${item['topic_title'] as String? ?? strings.questionFallback} • ${item['score'] as int? ?? 0}',
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  if (recommendations.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    ...recommendations.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _RecommendationCard(
                          item: item,
                          compact: true,
                          onOpen: () => unawaited(openRecommendation(item)),
                        ),
                      ),
                    ),
                  ],
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final bottomInset = MediaQuery.viewPaddingOf(context).bottom;
    final currentQuestion = question;
    final currentFeedback = feedback;
    final topicTitles = (currentQuestion?['topic_titles'] as List<dynamic>? ??
            const <dynamic>[])
        .cast<String>();
    final questionNumber = currentQuestion?['question_number'] as int? ?? 0;
    final totalQuestions = currentQuestion?['total_questions'] as int? ?? 0;
    final progressValue = totalQuestions > 0
        ? (questionNumber / totalQuestions).clamp(0.0, 1.0)
        : 0.0;
    final previousDifficulty =
        currentFeedback?['previous_difficulty'] as int? ?? 1;
    final currentDifficulty = currentFeedback?['current_difficulty'] as int? ?? 1;
    final feedbackMessage = currentFeedback == null
        ? ''
        : previousDifficulty == currentDifficulty
            ? (strings.isRu
                ? 'Сложность не изменилась, достигнут предел'
                : 'Difficulty did not change, limit reached')
            : currentFeedback['is_correct'] == true
                ? strings.correctAnswerDifficultyIncreased
                : strings.incorrectAnswerDifficultyDecreased;

    return Scaffold(
      appBar: AppBar(title: Text(strings.adaptiveTest)),
      body: result != null
          ? buildAdaptiveResult(strings)
          : ListView(
              padding: EdgeInsets.fromLTRB(16, 16, 16, 24 + bottomInset),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(strings.testIntro,
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 8),
                        Text(strings.adaptiveTestIntroDetail),
                        if (attemptId == null) ...[
                          const SizedBox(height: 16),
                          FilledButton(
                            onPressed: busy ? null : start,
                            child: Text(busy
                                ? strings.loadingQuestion
                                : strings.startTest),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                if (error.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  ErrorPanel(
                    text: error,
                    onRetry: busy
                        ? null
                        : () =>
                            attemptId == null ? start() : loadNextQuestion(),
                  ),
                ],
                if (attemptId != null && currentQuestion == null && busy) ...[
                  const SizedBox(height: 24),
                  const Center(child: CircularProgressIndicator()),
                ],
                if (currentQuestion != null) ...[
                  const SizedBox(height: 12),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(strings.questionProgress(
                              questionNumber, totalQuestions)),
                          const SizedBox(height: 10),
                          LinearProgressIndicator(value: progressValue),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              InfoPill(
                                label: strings.testLevelLabel(
                                    currentQuestion['target_difficulty']
                                            as int? ??
                                        1),
                              ),
                              InfoPill(
                                label: strings.currentQuestionLevelLabel(
                                    currentQuestion['difficulty'] as int? ?? 1),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Text(
                            strings.adaptiveDifficultyHint,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          if (topicTitles.isNotEmpty) ...[
                            const SizedBox(height: 12),
                            Text(
                              '${strings.topicsLabel}: ${topicTitles.join(", ")}',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                          const SizedBox(height: 16),
                          Text(
                            currentQuestion['text'] as String? ??
                                strings.questionFallback,
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  ...((currentQuestion['options'] as List<dynamic>? ??
                          const <dynamic>[])
                      .map((item) {
                    final option = jsonMap(item);
                    final optionId = option['id'] as int;
                    final selected = selectedAnswerId == optionId;
                    return Card(
                      color: selected
                          ? Theme.of(context).colorScheme.secondaryContainer
                          : null,
                      child: ListTile(
                        leading: Icon(
                          selected
                              ? Icons.check_circle
                              : Icons.radio_button_unchecked,
                        ),
                        title: Text(option['text'] as String? ??
                            strings.optionFallback),
                        onTap: currentFeedback != null || busy
                            ? null
                            : () => setState(() => selectedAnswerId = optionId),
                      ),
                    );
                  })),
                  if (currentFeedback == null) ...[
                    const SizedBox(height: 8),
                    Text(
                      strings.selectAnswerPrompt,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: busy || selectedAnswerId == null
                            ? null
                            : submitAnswer,
                        child: Text(strings.submitAnswer),
                      ),
                    ),
                  ],
                  if (currentFeedback != null) ...[
                    const SizedBox(height: 12),
                    Card(
                      color: currentFeedback['is_correct'] == true
                          ? Theme.of(context)
                              .colorScheme
                              .secondaryContainer
                              .withValues(alpha: 0.6)
                          : Theme.of(context)
                              .colorScheme
                              .errorContainer
                              .withValues(alpha: 0.7),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              currentFeedback['is_correct'] == true
                                  ? strings.answerWasCorrect
                                  : strings.answerWasIncorrect,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 8),
                            Text(feedbackMessage),
                            const SizedBox(height: 4),
                            Text(strings.difficultyShift(
                              previousDifficulty,
                              currentDifficulty,
                            )),
                            if ((currentFeedback['correct_option_text']
                                        as String?)
                                    ?.isNotEmpty ==
                                true) ...[
                              const SizedBox(height: 8),
                              Text(strings.correctAnswerLabel(
                                  currentFeedback['correct_option_text']
                                      as String)),
                            ],
                            if ((currentFeedback['explanation'] as String?)
                                    ?.isNotEmpty ==
                                true) ...[
                              const SizedBox(height: 12),
                              Text(strings.answerExplanation,
                                  style:
                                      Theme.of(context).textTheme.titleSmall),
                              const SizedBox(height: 4),
                              Text(currentFeedback['explanation'] as String),
                            ],
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    SafeArea(
                      top: false,
                      minimum: const EdgeInsets.only(bottom: 8),
                      child: SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: busy ? null : continueAdaptiveFlow,
                          child: Text(
                            (currentFeedback['remaining_questions'] as int? ??
                                        0) >
                                    0
                                ? strings.nextQuestion
                                : strings.finishTest,
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ],
            ),
    );
  }
}

class AttemptHistoryScreen extends StatefulWidget {
  const AttemptHistoryScreen({
    super.key,
    required this.api,
    required this.session,
    this.courseId,
    this.courseTitle,
  });

  final ApiClient api;
  final SessionState session;
  final int? courseId;
  final String? courseTitle;

  @override
  State<AttemptHistoryScreen> createState() => _AttemptHistoryScreenState();
}

class _AttemptHistoryScreenState extends State<AttemptHistoryScreen> {
  List<AttemptHistoryItem> items = const [];
  bool loading = true;
  String error = '';

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = '';
    });
    try {
      final payload = await widget.api.getAttemptHistory(
        widget.session,
        courseId: widget.courseId,
      );
      if (mounted) {
        setState(() => items = payload);
      }
    } catch (exception) {
      if (mounted) {
        setState(
          () => error = exception.toString().replaceFirst('Exception: ', ''),
        );
      }
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  Future<void> openAttemptReview(AttemptHistoryItem item) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AttemptReviewScreen(
          api: widget.api,
          session: widget.session,
          item: item,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          attemptHistoryTitle(strings, courseTitle: widget.courseTitle),
        ),
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error.isNotEmpty
              ? ErrorPanel(text: error, onRetry: load)
              : items.isEmpty
                  ? ErrorPanel(text: attemptHistoryEmptyLabel(strings))
                  : RefreshIndicator(
                      onRefresh: load,
                      child: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          Card(
                            color: Theme.of(context)
                                .colorScheme
                                .secondaryContainer
                                .withValues(alpha: 0.45),
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Text(attemptHistoryIntro(strings)),
                            ),
                          ),
                          const SizedBox(height: 12),
                          ...items.map(
                            (item) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: _AttemptHistoryCard(
                                item: item,
                                onOpen: () =>
                                    unawaited(openAttemptReview(item)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
    );
  }
}

class _AttemptHistoryCard extends StatelessWidget {
  const _AttemptHistoryCard({
    required this.item,
    required this.onOpen,
  });

  final AttemptHistoryItem item;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final theme = Theme.of(context);
    final weakTopicLabels = item.weakTopics
        .map((topic) => topic['topic_title'] as String? ?? '')
        .where((value) => value.trim().isNotEmpty)
        .toList();

    return Card(
      child: InkWell(
        key: ValueKey('attempt-history-card-${item.attemptId}'),
        borderRadius: BorderRadius.circular(12),
        onTap: onOpen,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                item.testTitle,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                item.courseTitle,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                completedAtLabel(strings, item.finishedAt),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  InfoPill(label: strings.scorePercent(item.scorePercent)),
                  InfoPill(
                    label: strings.correctAnswersCount(
                      item.correctAnswers,
                      item.totalQuestions,
                    ),
                  ),
                  InfoPill(
                    label: strings.averageResponseTime(
                      item.averageResponseSeconds,
                    ),
                  ),
                  InfoPill(
                    label: strings.finalDifficulty(item.finalDifficulty),
                  ),
                ],
              ),
              if (item.difficultyPath.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(strings.difficultyPath(item.difficultyPath)),
              ],
              if (weakTopicLabels.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: weakTopicLabels
                      .map((value) => Chip(label: Text(value)))
                      .toList(),
                ),
              ],
              if (item.recommendationCount > 0) ...[
                const SizedBox(height: 12),
                Text(
                  strings.recommendationsCount(item.recommendationCount),
                  style: theme.textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: onOpen,
                  icon: const Icon(Icons.article_outlined),
                  label: Text(openAttemptReviewLabel(strings)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class AttemptReviewScreen extends StatefulWidget {
  const AttemptReviewScreen({
    super.key,
    required this.api,
    required this.session,
    required this.item,
  });

  final ApiClient api;
  final SessionState session;
  final AttemptHistoryItem item;

  @override
  State<AttemptReviewScreen> createState() => _AttemptReviewScreenState();
}

class _AttemptReviewScreenState extends State<AttemptReviewScreen> {
  AttemptReviewPayload? payload;
  bool loading = true;
  String error = '';

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = '';
    });
    try {
      final nextPayload = await widget.api.getAttemptReview(
        widget.item.attemptId,
        widget.session,
      );
      if (mounted) {
        setState(() => payload = nextPayload);
      }
    } catch (exception) {
      if (mounted) {
        setState(
          () => error = exception.toString().replaceFirst('Exception: ', ''),
        );
      }
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          attemptReviewTitle(
            strings,
            testTitle: payload?.testTitle ?? widget.item.testTitle,
          ),
        ),
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error.isNotEmpty
              ? ErrorPanel(text: error, onRetry: load)
              : payload == null
                  ? ErrorPanel(text: attemptHistoryEmptyLabel(strings))
                  : RefreshIndicator(
                      onRefresh: load,
                      child: ListView(
                        key: const ValueKey('attempt-review-screen'),
                        padding: const EdgeInsets.all(16),
                        children: [
                          Card(
                            color: Theme.of(context)
                                .colorScheme
                                .secondaryContainer
                                .withValues(alpha: 0.45),
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Text(attemptReviewIntro(strings)),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    payload!.testTitle,
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleLarge
                                        ?.copyWith(
                                          fontWeight: FontWeight.w700,
                                        ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    payload!.courseTitle,
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodyMedium
                                        ?.copyWith(
                                          color: Theme.of(context)
                                              .colorScheme
                                              .onSurfaceVariant,
                                        ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    completedAtLabel(
                                        strings, payload!.finishedAt),
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodySmall
                                        ?.copyWith(
                                          color: Theme.of(context)
                                              .colorScheme
                                              .onSurfaceVariant,
                                        ),
                                  ),
                                  const SizedBox(height: 12),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: [
                                      InfoPill(
                                        label: strings.scorePercent(
                                          payload!.scorePercent,
                                        ),
                                      ),
                                      InfoPill(
                                        label: strings.correctAnswersCount(
                                          payload!.correctAnswers,
                                          payload!.totalQuestions,
                                        ),
                                      ),
                                      InfoPill(
                                        label: strings.averageResponseTime(
                                          payload!.averageResponseSeconds,
                                        ),
                                      ),
                                      InfoPill(
                                        label: strings.finalDifficulty(
                                          payload!.finalDifficulty,
                                        ),
                                      ),
                                      InfoPill(
                                        label: questionsInAttemptLabel(
                                          strings,
                                          payload!.questions.length,
                                        ),
                                      ),
                                    ],
                                  ),
                                  if (payload!.difficultyPath.isNotEmpty) ...[
                                    const SizedBox(height: 12),
                                    Text(
                                      strings.difficultyPath(
                                        payload!.difficultyPath,
                                      ),
                                    ),
                                  ],
                                  if (payload!.weakTopics.isNotEmpty) ...[
                                    const SizedBox(height: 12),
                                    Wrap(
                                      spacing: 8,
                                      runSpacing: 8,
                                      children: payload!.weakTopics
                                          .map(
                                            (item) => Chip(
                                              label: Text(
                                                item['topic_title']
                                                        as String? ??
                                                    strings.questionFallback,
                                              ),
                                            ),
                                          )
                                          .toList(),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          ...payload!.questions.map(
                            (item) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: _AttemptReviewQuestionCard(
                                item: item,
                                totalQuestions: payload!.questions.length,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
    );
  }
}

class _AttemptReviewQuestionCard extends StatelessWidget {
  const _AttemptReviewQuestionCard({
    required this.item,
    required this.totalQuestions,
  });

  final AttemptReviewQuestion item;
  final int totalQuestions;

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final theme = Theme.of(context);
    final selectedAnswer = item.selectedOptionText.trim().isEmpty
        ? noAnswerSelectedLabel(strings)
        : item.selectedOptionText;

    return Card(
      key: ValueKey('attempt-review-question-${item.questionNumber}'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    strings.questionProgress(
                        item.questionNumber, totalQuestions),
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: theme.colorScheme.primary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                Chip(
                  label: Text(
                    item.isCorrect
                        ? strings.answerWasCorrect
                        : strings.answerWasIncorrect,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              item.text,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                InfoPill(
                  label: strings.currentQuestionLevelLabel(item.difficulty),
                ),
                InfoPill(
                  label: responseTimeLabel(strings, item.responseSeconds),
                ),
                ...item.topicTitles.map((topic) => Chip(label: Text(topic))),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              yourAnswerLabel(strings, selectedAnswer),
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(strings.correctAnswerLabel(item.correctOptionText)),
            const SizedBox(height: 16),
            Text(
              answerOptionsLabel(strings),
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            ...item.options.map((option) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _AttemptReviewOptionRow(option: option),
                )),
            if (item.explanation.trim().isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                strings.answerExplanation,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Text(item.explanation),
            ],
          ],
        ),
      ),
    );
  }
}

class _AttemptReviewOptionRow extends StatelessWidget {
  const _AttemptReviewOptionRow({required this.option});

  final AttemptReviewOption option;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isSelectedWrong = option.isSelected && !option.isCorrect;
    final icon = option.isCorrect
        ? Icons.check_circle
        : option.isSelected
            ? Icons.cancel
            : Icons.radio_button_unchecked;
    final color = option.isCorrect
        ? theme.colorScheme.primary
        : option.isSelected
            ? theme.colorScheme.error
            : theme.colorScheme.onSurfaceVariant;
    final background = option.isCorrect
        ? theme.colorScheme.primaryContainer.withValues(alpha: 0.45)
        : isSelectedWrong
            ? theme.colorScheme.errorContainer.withValues(alpha: 0.45)
            : theme.colorScheme.surface;
    final borderColor = option.isCorrect
        ? theme.colorScheme.primary.withValues(alpha: 0.6)
        : isSelectedWrong
            ? theme.colorScheme.error.withValues(alpha: 0.6)
            : theme.dividerColor;

    return Container(
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderColor),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(icon, color: color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              option.text,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: option.isSelected || option.isCorrect
                    ? FontWeight.w600
                    : null,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class RecommendationsScreen extends StatefulWidget {
  const RecommendationsScreen({
    super.key,
    required this.api,
    required this.session,
  });

  final ApiClient api;
  final SessionState session;

  @override
  State<RecommendationsScreen> createState() => _RecommendationsScreenState();
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({
    required this.item,
    this.compact = false,
    this.onOpen,
  });

  final RecommendationInfo item;
  final bool compact;
  final VoidCallback? onOpen;

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final theme = Theme.of(context);
    final locationParts = <String>[
      if (item.lessonTitle.trim().isNotEmpty) item.lessonTitle.trim(),
      if (item.courseTitle.trim().isNotEmpty) item.courseTitle.trim(),
    ];

    final body = Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Chip(
                avatar: Icon(
                  item.priority <= 1
                      ? Icons.flag
                      : item.priority == 2
                          ? Icons.low_priority
                          : Icons.schedule,
                  size: 18,
                ),
                label: Text(
                  recommendationPriorityLabel(strings, item.priority),
                ),
              ),
              Chip(
                label:
                    Text(recommendationLevelLabel(strings, item.signalLevel)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            item.focusTitle,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          if (locationParts.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '${recommendationLocationLabel(strings)}: ${locationParts.join(' • ')}',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
          const SizedBox(height: 12),
          Text(
            recommendationWhyLabel(strings),
            style: theme.textTheme.labelLarge,
          ),
          const SizedBox(height: 4),
          Text(item.reason.isNotEmpty ? item.reason : item.text),
          if (!compact || item.text != item.focusTitle) ...[
            const SizedBox(height: 12),
            Text(
              recommendationActionLabel(strings),
              style: theme.textTheme.labelLarge,
            ),
            const SizedBox(height: 4),
            Text(item.text),
          ],
          if (onOpen != null) ...[
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onOpen,
              icon: const Icon(Icons.open_in_new),
              label: Text(
                item.lessonId != null
                    ? recommendationOpenLessonLabel(strings)
                    : recommendationOpenCourseLabel(strings),
              ),
            ),
          ],
        ],
      ),
    );

    return Card(
      clipBehavior: Clip.antiAlias,
      child: onOpen == null
          ? body
          : InkWell(
              onTap: onOpen,
              child: body,
            ),
    );
  }
}

class _RecommendationsScreenState extends State<RecommendationsScreen> {
  List<RecommendationInfo> items = const [];
  bool loading = true;
  String error = '';

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = '';
    });
    try {
      final payload = await widget.api.getRecommendations(widget.session);
      if (mounted) {
        setState(() => items = payload);
      }
    } catch (exception) {
      if (mounted) {
        setState(
            () => error = exception.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  Future<void> openRecommendation(RecommendationInfo item) async {
    if (item.lessonId != null) {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CoursePlayerScreen(
            api: widget.api,
            session: widget.session,
            initialLessonId: item.lessonId!,
          ),
        ),
      );
      if (mounted) {
        load();
      }
      return;
    }
    if (item.courseId != null) {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CourseOverviewScreen(
            api: widget.api,
            session: widget.session,
            course: CourseInfo(
              id: item.courseId!,
              title: item.courseTitle.trim().isNotEmpty
                  ? item.courseTitle
                  : context.strings.courseFallback,
              description: '',
              imageUrl: null,
            ),
          ),
        ),
      );
      if (mounted) {
        load();
      }
      return;
    }
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(recommendationUnavailableLabel(context.strings))),
    );
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    if (loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (error.isNotEmpty) {
      return ErrorPanel(
          text: strings.recommendationsLoadFailed(error), onRetry: load);
    }
    if (items.isEmpty) {
      return ErrorPanel(text: strings.noRecommendationsYet);
    }
    return RefreshIndicator(
      onRefresh: load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: Theme.of(context)
                .colorScheme
                .secondaryContainer
                .withValues(alpha: 0.55),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(recommendationIntro(strings)),
            ),
          ),
          const SizedBox(height: 12),
          ...items.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _RecommendationCard(
                item: item,
                onOpen: () => unawaited(openRecommendation(item)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({
    super.key,
    required this.api,
    required this.session,
    required this.onLogout,
  });

  final ApiClient api;
  final SessionState session;
  final VoidCallback onLogout;

  Future<void> openAttemptHistory(BuildContext context) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AttemptHistoryScreen(
          api: api,
          session: session,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    return FutureBuilder<List<Object>>(
      future: Future.wait<Object>([
        api.getProfile(session),
        api.getCurrentTenant(session),
      ]),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return ErrorPanel(text: snapshot.error.toString());
        }
        final profile = snapshot.data![0] as UserProfile;
        final tenant = snapshot.data![1] as TenantInfo;
        return Padding(
          padding: const EdgeInsets.all(16),
          child: ListView(
            children: [
              Text(profile.fullName,
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text(profile.email),
              const SizedBox(height: 8),
              Text(strings.tenantLabel(tenant.name)),
              const SizedBox(height: 4),
              Text(
                strings.tenantCodeValue(tenant.code),
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(strings.settings,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 12),
                      Text(strings.interfaceLanguage),
                      const SizedBox(height: 12),
                      SegmentedButton<AppLanguage>(
                        showSelectedIcon: false,
                        segments: const [
                          ButtonSegment<AppLanguage>(
                            value: AppLanguage.ru,
                            label: Text('Русский'),
                          ),
                          ButtonSegment<AppLanguage>(
                            value: AppLanguage.en,
                            label: Text('English'),
                          ),
                        ],
                        selected: {context.currentAppLanguage},
                        onSelectionChanged: (selection) =>
                            context.setAppLanguage(selection.first),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                key: const ValueKey('profile-attempt-history-button'),
                onPressed: () => openAttemptHistory(context),
                icon: const Icon(Icons.history),
                label: Text(viewAttemptHistoryLabel(strings)),
              ),
              const SizedBox(height: 24),
              FilledButton(onPressed: onLogout, child: Text(strings.logout)),
            ],
          ),
        );
      },
    );
  }
}

class InfoPill extends StatelessWidget {
  const InfoPill({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(label: Text(label));
  }
}

String _humanizeTenantCode(String code) {
  final trimmed = code.trim();
  if (trimmed.isEmpty) {
    return '';
  }
  final normalized = trimmed.replaceAll(RegExp(r'[_\-]+'), ' ');
  return normalized
      .split(' ')
      .where((part) => part.isNotEmpty)
      .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');
}

class _OrganizationMark extends StatelessWidget {
  const _OrganizationMark({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final trimmed = label.trim();
    final initial =
        trimmed.isEmpty ? '?' : String.fromCharCode(trimmed.runes.first);
    return CircleAvatar(
      radius: 16,
      backgroundColor:
          Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.9),
      child: Text(
        initial.toUpperCase(),
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Theme.of(context).colorScheme.onPrimaryContainer,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _CourseCoverFallback extends StatelessWidget {
  const _CourseCoverFallback({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Theme.of(context).colorScheme.primaryContainer,
            Theme.of(context).colorScheme.secondaryContainer,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      padding: const EdgeInsets.all(20),
      alignment: Alignment.bottomLeft,
      child: Text(
        title,
        maxLines: 3,
        overflow: TextOverflow.ellipsis,
        style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: Theme.of(context).colorScheme.onPrimaryContainer,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class ErrorPanel extends StatelessWidget {
  const ErrorPanel({
    super.key,
    required this.text,
    this.onRetry,
  });

  final String text;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(text, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              FilledButton(onPressed: onRetry, child: Text(strings.retry)),
            ],
          ],
        ),
      ),
    );
  }
}

class _ContentsSheet extends StatelessWidget {
  const _ContentsSheet({
    required this.payload,
    required this.currentPageIndex,
    required this.completedPageIds,
    required this.onOpenLesson,
    required this.onOpenPage,
  });

  final LessonPlayerPayload payload;
  final int currentPageIndex;
  final Set<String> completedPageIds;
  final ValueChanged<int> onOpenLesson;
  final ValueChanged<int> onOpenPage;

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    final sectionGroups = buildOutlineSectionGroups(payload.outline, strings);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 44,
                height: 5,
                decoration: BoxDecoration(
                  color: Theme.of(context)
                      .colorScheme
                      .outlineVariant
                      .withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            const SizedBox(height: 18),
            Text(strings.courseContents,
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 16),
            Text(strings.lessons,
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ...sectionGroups.map(
              (group) => Card(
                key: ValueKey('contents-section-${group.id ?? "general"}'),
                child: Padding(
                  padding: EdgeInsets.only(
                    top: group.hasSectionTitle ? 8 : 2,
                    bottom: 6,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (group.hasSectionTitle) ...[
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: Text(
                            group.title,
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                        ),
                        const SizedBox(height: 4),
                      ],
                      ...group.lessons.asMap().entries.map(
                            (entry) => Column(
                              children: [
                                if (entry.key > 0) const Divider(height: 1),
                                ListTile(
                                  key: ValueKey(
                                      'outline-lesson-${entry.value.id}'),
                                  title: Text(entry.value.title),
                                  subtitle: Text(strings.pagesWithDuration(
                                    entry.value.pageCount,
                                    formatDurationLabel(
                                        entry.value.durationMinutes),
                                  )),
                                  trailing: Wrap(
                                    spacing: 8,
                                    crossAxisAlignment:
                                        WrapCrossAlignment.center,
                                    children: [
                                      if (entry.value.isCompleted)
                                        const Icon(Icons.check_circle,
                                            size: 18),
                                      if (entry.value.id == payload.lessonId)
                                        Chip(
                                          label: Text(strings.currentLesson),
                                          visualDensity: VisualDensity.compact,
                                        ),
                                    ],
                                  ),
                                  onTap: () => onOpenLesson(entry.value.id),
                                ),
                              ],
                            ),
                          ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(strings.pagesInLesson,
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ...payload.chapters.map(
              (chapter) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text(chapter.chapterTitle,
                        style: Theme.of(context).textTheme.labelLarge),
                  ),
                  ...chapter.pages.map(
                    (page) => Card(
                      child: ListTile(
                        key: ValueKey('outline-page-${page.pageId}'),
                        title: Text(page.pageTitle),
                        trailing: Wrap(
                          spacing: 8,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            if (completedPageIds.contains(page.pageId))
                              const Icon(Icons.check, size: 18),
                            if (page.pageIndex == currentPageIndex)
                              Chip(
                                  label: Text(strings.currentPage),
                                  visualDensity: VisualDensity.compact),
                          ],
                        ),
                        onTap: () => onOpenPage(page.pageIndex),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LessonBlockView extends StatelessWidget {
  const _LessonBlockView({
    required this.session,
    required this.block,
    required this.savedVideoPositionFor,
    required this.onVideoPositionChanged,
    this.previewMode,
  });

  final SessionState session;
  final LessonBlockData block;
  final int Function(String videoUrl) savedVideoPositionFor;
  final void Function(String videoUrl, int seconds) onVideoPositionChanged;
  final InlineVideoPreviewMode? previewMode;

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    switch (block.type) {
      case 'html':
        return LessonHtmlBlock(
          html: block.html ?? block.text ?? '',
          resolveUrl: (rawUrl) => resolveMediaUrl(session, rawUrl),
          resolveHeaders: (mediaUrl) => resolveMediaHeaders(session, mediaUrl),
          savedVideoPositionFor: savedVideoPositionFor,
          onVideoPositionChanged: onVideoPositionChanged,
        );
      case 'image':
        final imageUrl = resolveMediaUrl(session, block.url);
        final imageHeaders = resolveMediaHeaders(session, imageUrl);
        return LessonMediaFrame(
          backgroundColor:
              Theme.of(context).colorScheme.surfaceContainerHighest,
          child: Image.network(
            imageUrl,
            fit: BoxFit.contain,
            headers: imageHeaders,
            loadingBuilder: (context, child, progress) {
              if (progress == null) {
                return child;
              }
              return const Center(child: CircularProgressIndicator());
            },
            errorBuilder: (_, __, ___) => Center(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child:
                    Text(strings.imageUnavailable, textAlign: TextAlign.center),
              ),
            ),
          ),
        );
      case 'video':
        final videoUrl = resolveMediaUrl(session, block.url);
        return InlineVideoPanel(
          key: ValueKey('video-${block.url}'),
          url: videoUrl,
          title: block.title ?? strings.lessonVideo,
          initialPositionSeconds: savedVideoPositionFor(videoUrl),
          onPositionChanged: (seconds) =>
              onVideoPositionChanged(videoUrl, seconds),
          previewMode: previewMode ??
              (block.status == 'invalid' ? InlineVideoPreviewMode.error : null),
          errorText: block.error,
        );
      case 'text':
      default:
        return _TextBlockCard(text: block.text ?? '');
    }
  }
}

class _TextBlockCard extends StatelessWidget {
  const _TextBlockCard({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final lines = text
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: lines.map((line) {
        if (line.startsWith('- ')) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Padding(
                  padding: EdgeInsets.only(top: 6, right: 8),
                  child: Icon(Icons.circle, size: 8),
                ),
                Expanded(child: Text(line.substring(2))),
              ],
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Text(line, style: Theme.of(context).textTheme.bodyLarge),
        );
      }).toList(),
    );
  }
}
