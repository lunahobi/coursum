import { ChangeEvent, createContext, FormEvent, ReactNode, Ref, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useSearchParams } from "react-router-dom";
import { apiDelete, apiPatch, apiPost, apiRequest, apiUpload, configureSessionLifecycle, login, resolveMediaUrl, SessionState } from "./api";
import websiteLogo from "./assets/brand/website_logo.svg";
import websiteLogoWhite from "./assets/brand/website_logo_white.svg";

type Language = "ru" | "en";

const LANGUAGE_STORAGE_KEY = "coursum-web-language";
const SESSION_STORAGE_KEY = "coursum-web-session";
const SAVED_ACCOUNTS_STORAGE_KEY = "coursum-web-saved-accounts";
const ENABLE_DEV_AUTH_PREFILL = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEV_AUTH_PREFILL === "true";
const DEV_PREFILL_EMAIL = import.meta.env.VITE_DEV_LOGIN_EMAIL ?? "";
const DEV_PREFILL_PASSWORD = import.meta.env.VITE_DEV_LOGIN_PASSWORD ?? "";
const DEV_PREFILL_TENANT = import.meta.env.VITE_DEV_TENANT_CODE ?? "";

type SavedAccount = {
  id: string;
  organizationCode: string;
  login: string;
  displayName?: string;
  lastUsedAt: string;
};

const MESSAGES = {
  ru: {
    noDocumentSelected: "Документ пока не выбран.",
    attachDocument: "Загрузить документ",
    insertDocument: "Вставить ссылку на документ",
    mediaDialogDocumentTitle: "Выбор документа",
    mediaDialogUploadHintDocument: "Загрузите PDF, DOCX, PPTX, XLSX или TXT. Ссылка будет вставлена в текст урока.",
    mediaDialogDocumentLinkText: "Текст ссылки",
    mediaDialogSearch: "Поиск в медиатеке",
    mediaDialogSearchPlaceholder: "Название, файл или путь",
    email: "Email",
    password: "Пароль",
    tenantCode: "Код организации",
    save: "Сохранить",
    cancel: "Отмена",
    loading: "Загрузка...",
    loadingData: "Загрузка данных...",
    noData: "Пока нет данных",
    settings: "Настройки",
    language: "Язык интерфейса",
    russian: "Русский",
    english: "English",
    tenant: "Организация",
    dashboard: "Дашборд",
    tenantSwitch: "Смена организации",
    users: "Пользователи",
    courses: "Курсы",
    lessons: "Уроки",
    tests: "Тесты",
    assignments: "Назначения",
    analytics: "Аналитика",
    logout: "Выйти",
    loginTitle: "Панель Coursum",
    loginSubtitle: "Панель администратора и преподавателя для управления курсами, уроками и прогрессом.",
    chooseAccount: "Выберите аккаунт",
    noSavedAccounts: "Сохраненных аккаунтов пока нет. Войдите и включите опцию запоминания.",
    useLastAccount: "Использовать последний аккаунт",
    rememberAccount: "Запомнить аккаунт",
    removeAccount: "Удалить",
    removeAllAccounts: "Удалить все аккаунты",
    removeAccountConfirm: "Удалить этот сохраненный аккаунт?",
    removeAllAccountsConfirm: "Удалить все сохраненные аккаунты?",
    signIn: "Войти",
    loginFailed: "Не удалось выполнить вход",
    fullName: "Полное имя",
    role: "Роль",
    usersPageTitle: "Пользователи",
    usersPageSubtitle: "Создавайте пользователей организации и управляйте их доступом.",
    createUser: "Создать пользователя",
    createUserAction: "Создать пользователя",
    userCreateIntro: "Создайте учетную запись, задайте роль и стартовый пароль для первого входа.",
    userPasswordHint: "Пароль задается сразу и понадобится пользователю для первого входа в систему.",
    userRoleHint: "Слушатель проходит курсы, преподаватель работает с обучением, администратор управляет пользователями и контентом.",
    roleLearner: "Слушатель",
    roleTeacher: "Преподаватель",
    roleOrgAdmin: "Администратор организации",
    roleSystemAdmin: "Системный администратор",
    userDirectory: "Список пользователей",
    userDirectorySubtitle: "Здесь видно, у кого доступ активен, а у кого вход временно отключен.",
    activate: "Активировать",
    deactivate: "Деактивировать",
    userAccessGuideTitle: "Что делает деактивация",
    userAccessGuideBody: "Деактивация временно отключает вход на платформу. История обучения, назначения и попытки тестов сохраняются. После повторной активации доступ вернется.",
    userStatusActive: "Активен",
    userStatusInactive: "Доступ отключен",
    coursesPageTitle: "Курсы",
    coursesPageSubtitle: "Настройки курса в духе Moodle: выберите курс из списка, обновите его метаданные и сразу посмотрите текущую структуру уроков.",
    courseCatalog: "Каталог курсов",
    curriculumContainers: "Контейнеры учебных программ",
    selectCourseToEdit: "Выберите курс, чтобы изменить настройки и посмотреть текущую структуру уроков.",
    newCourse: "Новый курс",
    noDescriptionYet: "Описание пока не добавлено.",
    loadingCourses: "Загрузка курсов...",
    courseSettings: "Настройки курса",
    createCourseLabel: "Создание курса",
    editSelectedCourse: "Редактирование выбранного курса",
    createCourseShell: "Создайте новый контейнер курса",
    openLessonBuilder: "Открыть редактор уроков",
    courseTitle: "Название курса",
    description: "Описание",
    courseCover: "Обложка курса",
    courseCoverHint: "Эта карточка используется в мобильном приложении и в каталоге назначений.",
    courseDescriptionPlaceholder: "Какого результата должен достичь слушатель после прохождения курса?",
    saveCourse: "Сохранить курс",
    createCourseAction: "Создать курс",
    createAnotherCourse: "Создать еще один курс",
    deleteCourse: "Удалить курс",
    curriculumPreview: "Предпросмотр программы",
    selectCourse: "Выберите курс",
    noLessonsYet: "В этом курсе пока нет уроков.",
    pickCoursePrompt: "Выберите курс слева или создайте новый, чтобы начать собирать программу.",
    lessonsCount: "уроков",
    lessonSummaryEmpty: "Краткое описание урока пока не заполнено.",
    lessonSettings: "Настройки урока",
    newLessonLabel: "Новый урок",
    createLessonInCourse: "Создайте урок внутри выбранного курса",
    lessonTitle: "Название урока",
    sortOrder: "Порядок сортировки",
    durationMinutes: "Длительность в минутах",
    lessonSummary: "Краткое описание урока",
    lessonSummaryPlaceholder: "Что слушатель должен вынести из этого урока?",
    saveLesson: "Сохранить урок",
    createLessonAction: "Создать урок",
    resetDraft: "Сбросить черновик",
    curriculum: "Программа",
    courseAndLessons: "Курс и уроки",
    pickCourseFirst: "Сначала выберите курс, затем редактируйте уроки по одному, как в Coursum-конструкторе.",
    courseLabel: "Курс",
    noCourseDescription: "Описание курса пока не заполнено.",
    editCourse: "Редактировать курс",
    newLessonAction: "Новый урок",
    loadingLessons: "Загрузка уроков...",
    pages: "Страницы",
    lessonOutline: "Структура урока",
    addPage: "Добавить страницу",
    outlineHint: "Держите структуру урока слева, а справа редактируйте только активную страницу.",
    activePage: "Активная страница",
    chapterTitle: "Название главы",
    pageTitle: "Название страницы",
    pageContent: "Содержимое страницы",
    htmlSource: "HTML-код",
    htmlPlaceholder: "Введите HTML страницы урока. Поддерживаются теги: h2, h3, p, ul, li, blockquote, pre, code, img, video, table...",
    preview: "Предпросмотр",
    noPreviewYet: "Предпросмотр пока пуст.",
    htmlHelp: "Используйте HTML для заголовков, списков, callout-блоков, примеров кода, таблиц, встроенных изображений и прямых тегов MP4/WebM видео. Ссылки на media ниже тоже работают как spotlight-блоки.",
    localMediaLibrary: "Локальная медиатека",
    useAsImage: "Использовать как изображение",
    useAsVideo: "Использовать как видео",
    insertTag: "Вставить тег",
    untitledPage: "Страница без названия",
    noChapterLabel: "Глава пока не названа",
    up: "Вверх",
    down: "Вниз",
    remove: "Удалить",
    spotlightImageUrl: "URL spotlight-изображения",
    spotlightVideoUrl: "URL spotlight-видео",
    optionalImageUrl: "Необязательный URL изображения",
    optionalVideoUrl: "Необязательный URL MP4/WebM видео",
    imageBlockPreview: "Превью изображения",
    videoBlockPreview: "Превью видео",
    learnerPreview: "Превью для слушателя",
    chapter: "Глава",
    page: "Страница",
    noPageContentYet: "Контент страницы пока пуст.",
    noImageSelected: "Изображение пока не выбрано.",
    noVideoSelected: "Видео пока не выбрано.",
    pageMediaTitle: "Медиа страницы",
    attachImage: "Добавить изображение",
    attachVideo: "Добавить видео",
    removeImage: "Убрать изображение",
    removeVideo: "Убрать видео",
    selectedAsset: "Текущий файл",
    noAssetSelected: "Файл пока не выбран.",
    advancedSettings: "Расширенные настройки",
    pageAdvancedHint: "Здесь скрыты HTML-код и прямые URL медиа для опытных редакторов.",
    lessonAdvancedHint: "Здесь живут fallback-медиа урока и legacy-контент.",
    mediaDialogImageTitle: "Выбор изображения",
    mediaDialogVideoTitle: "Выбор видео",
    mediaDialogUploadTab: "Загрузка",
    mediaDialogLibraryTab: "Медиатека",
    mediaDialogChooseFile: "Локальный файл",
    mediaDialogUploadHintImage: "Загрузите PNG, JPG, GIF или WebP с локального компьютера.",
    mediaDialogUploadHintVideo: "Загрузите MP4, WebM, MOV или M4V. Видео будет подготовлено для мобильного плеера.",
    mediaDialogUploadAction: "Загрузить и выбрать",
    mediaDialogSelect: "Выбрать",
    mediaDialogNoAssets: "В медиатеке пока нет файлов этого типа.",
    mediaDialogUploading: "Загружаем файл...",
    mediaDialogProcessing: "Сервер обрабатывает файл...",
    mediaDialogProcessingHint: "Файл уже отправлен. Ждём, пока сервер завершит сохранение и подготовку видео.",
    mediaDialogUploadProgress: "Прогресс загрузки",
    mediaPreviewError: "Не удалось показать превью этого файла.",
    modalClose: "Закрыть",
    selectFileFirst: "Сначала выберите файл.",
    sharedLessonSettings: "Общие настройки урока",
    lessonWideMediaFallback: "Общее медиа и fallback",
    lessonHeroImage: "Главное изображение урока",
    lessonHeroVideo: "Главное видео урока",
    imageUrl: "URL изображения",
    videoUrl: "URL видео",
    legacyFallbackContent: "Fallback-контент для старого рендера",
    legacyFallbackPlaceholder: "Необязательный fallback-контент для старого рендера. Оставьте пустым, чтобы он собрался автоматически из структурированных страниц выше.",
    testsPageTitle: "Тесты",
    testsPageSubtitle: "Создавайте оценки, связанные с курсами и параметрами адаптивности.",
    createTest: "Создать тест",
    testTitle: "Название теста",
    baselineDifficulty: "Базовая сложность",
    questionLimit: "Лимит вопросов",
    createTestAction: "Создать тест",
    testsLabel: "Тесты",
    testsSetupHint: "Сначала выберите курс, затем задайте стартовую сложность и длину попытки. Эти параметры влияют на то, с какого уровня начнётся адаптивный тест и сколько вопросов максимум увидит слушатель.",
    testsPresetLabel: "Готовые сценарии",
    testsPresetHint: "Пресеты быстро заполняют рекомендуемые значения, а ниже их можно донастроить вручную.",
    testsPresetQuick: "Быстрая проверка",
    testsPresetStandard: "Стандартный тест",
    testsPresetExam: "Итоговый тест",
    baselineDifficultyHint: "Определяет стартовую сложность первой группы вопросов. Дальше адаптивный движок всё равно подстроится по ответам слушателя.",
    baselineDifficultyLevel1: "1 - мягкий старт для вводной проверки",
    baselineDifficultyLevel2: "2 - лёгкий уровень для первых шагов",
    baselineDifficultyLevel3: "3 - сбалансированный старт для большинства курсов",
    baselineDifficultyLevel4: "4 - уверенный уровень для опытной аудитории",
    baselineDifficultyLevel5: "5 - высокий порог для итоговой оценки",
    questionLimitHint: "Лимит определяет, сколько вопросов максимум попадёт в одну попытку. Для короткой диагностики держите 5-7, для итоговой проверки - 10-15.",
    selectedCourseOverview: "Сводка по настройке",
    selectedCourseDescription: "Выбранный курс",
    selectedCourseTestsCount: "Уже создано тестов",
    selectedCourseQuestionPlan: "Максимум вопросов в попытке",
    selectedCourseDifficultyPlan: "Стартовая сложность",
    selectedCourseTitleSuggestion: "Подсказка по названию",
    selectedCourseEmptyDescription: "Описание курса пока не заполнено. Добавьте короткую цель курса, чтобы авторам и преподавателям было проще ориентироваться.",
    testsRecommendedTitle: "Например: \"{course} - итоговая проверка\"",
    questionBankLabel: "Вопросов в банке",
    testsBankEmpty: "Пока нет вопросов",
    testsLengthShort: "короткий формат",
    testsLengthBalanced: "сбалансированный формат",
    testsLengthExtended: "развёрнутый формат",
    testsAdaptiveBehavior: "Как это сработает",
    testsAdaptiveBehaviorHint: "Слушатель начнёт с уровня {difficulty}. Система покажет до {limit} вопросов и будет повышать или понижать сложность по ходу попытки.",
    questionEditorTitle: "Вопросы внутри теста",
    questionEditorHint: "После создания теста добавьте сами вопросы, варианты ответов и связанные темы. Один правильный вариант обязателен.",
    selectTestForQuestions: "Тест для наполнения",
    selectTestFirst: "Сначала создайте или выберите тест для выбранного курса.",
    questionText: "Текст вопроса",
    questionExplanation: "Пояснение после ответа",
    questionDifficulty: "Сложность вопроса",
    questionEstimatedSeconds: "Ожидаемое время ответа, сек",
    questionTopics: "Темы вопроса",
    questionOptions: "Варианты ответа",
    questionCorrectOption: "Правильный вариант",
    addAnswerOption: "Добавить вариант",
    removeAnswerOption: "Убрать вариант",
    createQuestionAction: "Добавить вопрос",
    saveQuestionAction: "Сохранить вопрос",
    editQuestionAction: "Редактировать",
    cancelQuestionEditing: "Сбросить правки",
    questionsInTest: "Вопросы теста",
    optionCount: "Вариантов",
    noTopicsAvailable: "Темы пока не заведены. Вопрос можно сохранить и без привязки темы.",
    noQuestionsInTest: "В этом тесте пока нет вопросов.",
    questionCreated: "Вопрос добавлен",
    questionUpdated: "Вопрос обновлён",
    failedSaveQuestion: "Не удалось сохранить вопрос",
    editingQuestionLabel: "Редактирование вопроса #{id}",
    answerOptionLabel: "Вариант {number}",
    assignmentsPageTitle: "Назначения",
    assignmentsPageSubtitle: "Назначайте курс конкретному слушателю.",
    assignCourse: "Назначить курс",
    assign: "Назначить",
    howToDemo: "Как демонстрировать",
    howToDemo1: "Выберите курс и слушателя.",
    howToDemo2: "Отправьте назначение, затем откройте mobile app или learner-аккаунт, чтобы увидеть курс.",
    howToDemo3: "Backend также фиксирует условную доставку уведомления о назначении.",
    analyticsPageTitle: "Аналитика",
    analyticsPageSubtitle: "Отслеживайте успеваемость по курсам и смотрите детали по конкретному слушателю.",
    overview: "Обзор",
    learnerDetail: "Детали слушателя",
    learnerId: "ID слушателя",
    load: "Загрузить",
    loadingAnalytics: "Загрузка аналитики...",
    settingsPageTitle: "Настройки и профиль",
    settingsPageSubtitle: "Данные текущего оператора и контекст организации.",
    profile: "Профиль",
    loadingProfile: "Загрузка профиля...",
    currentRole: "Текущая роль",
    name: "Имя",
    code: "Код",
    locale: "Локаль",
    currentTenant: "Текущая организация",
    availableTenants: "Доступные организации",
    loadingCurrentTenant: "Загрузка текущей организации...",
    switch: "Переключить",
    tenantSwitchTitle: "Смена организации",
    tenantSwitchSubtitle: "Переключайтесь между организациями, доступными текущей учетной записи.",
    dashboardTitle: "Дашборд",
    dashboardSubtitle: "Операционный обзор по текущей организации.",
    loadingMetrics: "Загрузка метрик...",
    courseProgress: "Прогресс по курсам",
    columnCourse: "Курс",
    averageProgress: "Средний прогресс",
    learners: "Слушатели",
    problemTopics: "Проблемные темы",
    topicId: "ID темы",
    recommendations: "Рекомендации",
    metricUsers: "Активные пользователи",
    metricCourses: "Курсы в организации",
    metricTests: "Тесты",
    metricActiveAttempts: "Активные попытки",
    metricEnrollments: "Назначения курсов",
    metricAverageProgress: "Средний прогресс",
    metricRecommendationsBacklog: "Активные рекомендации",
    dashboardCourseHealthTitle: "Состояние курсов",
    dashboardCourseHealthSubtitle: "По этим карточкам видно, где обучение уже двигается, а где слушатели застревают.",
    dashboardAttentionTitle: "Что требует внимания",
    dashboardAttentionSubtitle: "Темы ниже чаще всего попадают в рекомендации после адаптивных тестов.",
    dashboardNoCourseProgress: "Пока нет назначений или прогресса по курсам.",
    dashboardNoProblemTopics: "Пока нет тем, требующих внимания.",
    dashboardLearnersLabel: "слушателей",
    dashboardRecommendationsLabel: "рекомендаций",
    id: "ID",
    title: "Название",
    courseId: "ID курса",
    userCreated: "Пользователь создан",
    failedCreateUser: "Не удалось создать пользователя",
    failedUpdateUser: "Не удалось обновить пользователя",
    courseUpdated: "Курс сохранен",
    courseCreated: "Курс создан",
    courseDeleted: "Курс удален",
    failedSaveCourse: "Не удалось сохранить курс",
    failedDeleteCourse: "Не удалось удалить курс",
    deleteCourseConfirm: "Удалить курс и все связанные с ним уроки? Это действие нельзя отменить.",
    courseEditorRestrictedTitle: "Редактор курса недоступен",
    courseEditorRestrictedBody: "Эта учётная запись имеет роль слушателя. Создавать и редактировать курсы могут только преподаватель, администратор организации или системный администратор.",
    lessonUpdated: "Урок сохранен",
    lessonCreated: "Урок создан",
    failedSaveLesson: "Не удалось сохранить урок",
    draftingLesson: "Создаем черновик нового урока в выбранном курсе.",
    noLinkedLesson: "Связанный урок не найден",
    action: "Действие",
    priority: "Приоритет",
    noWeakTopics: "Слабые темы не обнаружены",
    emptyAttempt: "Попытки пока нет",
    loadingUsers: "Загрузка пользователей...",
    organizationWorkspace: "Рабочее пространство Coursum",
    learner: "Слушатель"
  },
  en: {
    email: "Email",
    password: "Password",
    tenantCode: "Tenant code",
    save: "Save",
    cancel: "Cancel",
    loading: "Loading...",
    loadingData: "Loading data...",
    noData: "No data yet",
    settings: "Settings",
    language: "Interface language",
    russian: "Русский",
    english: "English",
    tenant: "Tenant",
    dashboard: "Dashboard",
    tenantSwitch: "Tenant switch",
    users: "Users",
    courses: "Courses",
    lessons: "Lessons",
    tests: "Tests",
    assignments: "Assignments",
    analytics: "Analytics",
    logout: "Logout",
    loginTitle: "Coursum Panel",
    loginSubtitle: "Admin and teacher workspace for courses, lessons, and learning progress.",
    chooseAccount: "Choose account",
    noSavedAccounts: "No saved accounts yet. Sign in once and enable remember option.",
    useLastAccount: "Use last account",
    rememberAccount: "Remember account",
    removeAccount: "Remove",
    removeAllAccounts: "Remove all accounts",
    removeAccountConfirm: "Remove this saved account?",
    removeAllAccountsConfirm: "Remove all saved accounts?",
    signIn: "Sign in",
    loginFailed: "Login failed",
    fullName: "Full name",
    role: "Role",
    usersPageTitle: "Users",
    usersPageSubtitle: "Create tenant users and manage their access.",
    createUser: "Create user",
    createUserAction: "Create user",
    userCreateIntro: "Create an account, choose a role, and set the starter password for the first sign-in.",
    userPasswordHint: "The password is set at creation time and will be needed for the user's first sign-in.",
    userRoleHint: "Learners take courses, teachers oversee learning, and organization admins manage people and content.",
    roleLearner: "Learner",
    roleTeacher: "Teacher",
    roleOrgAdmin: "Organization admin",
    roleSystemAdmin: "System admin",
    userDirectory: "User directory",
    userDirectorySubtitle: "Use this list to see who still has access and whose sign-in is temporarily blocked.",
    activate: "Activate",
    deactivate: "Deactivate",
    userAccessGuideTitle: "What deactivation does",
    userAccessGuideBody: "Deactivation temporarily blocks sign-in to the platform. Learning history, assignments, and test attempts stay in place. Access can be restored later by activating the user again.",
    userStatusActive: "Active",
    userStatusInactive: "Access disabled",
    coursesPageTitle: "Courses",
    coursesPageSubtitle: "Moodle-like course settings: pick a course from the list, update its metadata, and inspect the current lesson structure in one place.",
    courseCatalog: "Course catalog",
    curriculumContainers: "Curriculum containers",
    selectCourseToEdit: "Select a course to edit settings and inspect the current lesson structure.",
    newCourse: "New course",
    noDescriptionYet: "No description yet.",
    loadingCourses: "Loading courses...",
    courseSettings: "Course settings",
    createCourseLabel: "Create course",
    editSelectedCourse: "Edit selected course",
    createCourseShell: "Create a new course shell",
    openLessonBuilder: "Open lesson builder",
    courseTitle: "Course title",
    description: "Description",
    courseCover: "Course cover",
    courseCoverHint: "This image is shown in the mobile learner app and in course assignment flows.",
    courseDescriptionPlaceholder: "What should this course achieve for the learner?",
    saveCourse: "Save course",
    createCourseAction: "Create course",
    createAnotherCourse: "Create another course",
    deleteCourse: "Delete course",
    curriculumPreview: "Curriculum preview",
    selectCourse: "Select a course",
    noLessonsYet: "No lessons in this course yet.",
    pickCoursePrompt: "Pick a course from the left or create a new one to start building curriculum.",
    lessonsCount: "lessons",
    lessonSummaryEmpty: "No lesson summary yet.",
    lessonSettings: "Lesson settings",
    newLessonLabel: "New lesson",
    createLessonInCourse: "Create a lesson inside the selected course",
    lessonTitle: "Lesson title",
    sortOrder: "Sort order",
    durationMinutes: "Duration in minutes",
    lessonSummary: "Lesson summary",
    lessonSummaryPlaceholder: "What should the learner take away from this lesson?",
    saveLesson: "Save lesson",
    createLessonAction: "Create lesson",
    resetDraft: "Reset draft",
    curriculum: "Curriculum",
    courseAndLessons: "Course and lessons",
    pickCourseFirst: "Pick a course first, then work through lessons one by one in the Coursum curriculum builder.",
    courseLabel: "Course",
    noCourseDescription: "No course description yet.",
    editCourse: "Edit course",
    newLessonAction: "New lesson",
    loadingLessons: "Loading lessons...",
    pages: "Pages",
    lessonOutline: "Lesson outline",
    addPage: "Add page",
    outlineHint: "Keep the lesson structure on the left and edit one active page on the right.",
    activePage: "Active page",
    chapterTitle: "Chapter title",
    pageTitle: "Page title",
    pageContent: "Page content",
    htmlSource: "HTML source",
    htmlPlaceholder: "Write lesson page HTML here. Supported tags: h2, h3, p, ul, li, blockquote, pre, code, img, video, table...",
    preview: "Preview",
    noPreviewYet: "No preview yet.",
    htmlHelp: "Use HTML for headings, lists, callouts, code examples, tables, inline images, and direct MP4/WebM video tags. Dedicated media URLs below still work as spotlight blocks.",
    localMediaLibrary: "Local media library",
    useAsImage: "Use as image",
    useAsVideo: "Use as video",
    insertTag: "Insert tag",
    untitledPage: "Untitled page",
    noChapterLabel: "No chapter label yet",
    up: "Up",
    down: "Down",
    remove: "Remove",
    spotlightImageUrl: "Spotlight image URL",
    spotlightVideoUrl: "Spotlight video URL",
    optionalImageUrl: "Optional image URL",
    optionalVideoUrl: "Optional MP4/WebM video URL",
    imageBlockPreview: "Image block preview",
    videoBlockPreview: "Video block preview",
    learnerPreview: "Learner preview",
    chapter: "Chapter",
    page: "Page",
    noPageContentYet: "No page content yet.",
    noImageSelected: "No image selected yet.",
    noVideoSelected: "No video selected yet.",
    noDocumentSelected: "No document selected yet.",
    pageMediaTitle: "Page media",
    attachImage: "Attach image",
    attachVideo: "Attach video",
    attachDocument: "Upload document",
    insertDocument: "Insert document link",
    removeImage: "Remove image",
    removeVideo: "Remove video",
    selectedAsset: "Current asset",
    noAssetSelected: "No file selected yet.",
    advancedSettings: "Advanced settings",
    pageAdvancedHint: "Raw HTML and direct media URLs live here for advanced editors.",
    lessonAdvancedHint: "Lesson-wide fallback media and legacy content are kept here.",
    mediaDialogImageTitle: "Image picker",
    mediaDialogVideoTitle: "Video picker",
    mediaDialogDocumentTitle: "Document picker",
    mediaDialogUploadTab: "Upload",
    mediaDialogLibraryTab: "Library",
    mediaDialogChooseFile: "Local file",
    mediaDialogUploadHintImage: "Upload a PNG, JPG, GIF, or WebP file from your computer.",
    mediaDialogUploadHintVideo: "Upload an MP4, WebM, MOV, or M4V file. The server will prepare it for the mobile player.",
    mediaDialogUploadHintDocument: "Upload PDF, DOCX, PPTX, XLSX, or TXT files. The link will be inserted into the lesson text.",
    mediaDialogDocumentLinkText: "Link text",
    mediaDialogSearch: "Search library",
    mediaDialogSearchPlaceholder: "Name, file, or path",
    mediaDialogUploadAction: "Upload and select",
    mediaDialogSelect: "Select",
    mediaDialogNoAssets: "No assets of this type in the library yet.",
    mediaDialogUploading: "Uploading file...",
    mediaDialogProcessing: "Server is processing the file...",
    mediaDialogProcessingHint: "The file is already uploaded. Waiting for the server to finish saving it and preparing the video.",
    mediaDialogUploadProgress: "Upload progress",
    mediaPreviewError: "Could not preview this file.",
    modalClose: "Close",
    selectFileFirst: "Select a file first.",
    sharedLessonSettings: "Shared lesson settings",
    lessonWideMediaFallback: "Lesson-wide media and fallback",
    lessonHeroImage: "Lesson hero image",
    lessonHeroVideo: "Lesson hero video",
    imageUrl: "Image URL",
    videoUrl: "Video URL",
    legacyFallbackContent: "Legacy fallback content",
    legacyFallbackPlaceholder: "Optional legacy fallback content. Leave empty to auto-generate from the structured pages above.",
    testsPageTitle: "Tests",
    testsPageSubtitle: "Create assessments linked to courses and adaptive parameters.",
    createTest: "Create test",
    testTitle: "Test title",
    baselineDifficulty: "Baseline difficulty",
    questionLimit: "Question limit",
    createTestAction: "Create test",
    testsLabel: "Tests",
    testsSetupHint: "Pick a course, then set the starting difficulty and attempt length. These values decide where the adaptive test begins and how many questions a learner can see at most.",
    testsPresetLabel: "Recommended presets",
    testsPresetHint: "Presets fill in sensible defaults first, and you can fine-tune everything below.",
    testsPresetQuick: "Quick check",
    testsPresetStandard: "Standard test",
    testsPresetExam: "Final assessment",
    baselineDifficultyHint: "Sets the starting difficulty for the first questions. The adaptive engine will still adjust up or down based on the learner's answers.",
    baselineDifficultyLevel1: "1 - gentle start for an introductory check",
    baselineDifficultyLevel2: "2 - light difficulty for early practice",
    baselineDifficultyLevel3: "3 - balanced starting point for most courses",
    baselineDifficultyLevel4: "4 - confident level for experienced learners",
    baselineDifficultyLevel5: "5 - high bar for final evaluation",
    questionLimitHint: "This caps how many questions can appear in one attempt. Keep it around 5-7 for diagnostics and 10-15 for a fuller assessment.",
    selectedCourseOverview: "Setup summary",
    selectedCourseDescription: "Selected course",
    selectedCourseTestsCount: "Existing tests",
    selectedCourseQuestionPlan: "Max questions per attempt",
    selectedCourseDifficultyPlan: "Starting difficulty",
    selectedCourseTitleSuggestion: "Title suggestion",
    selectedCourseEmptyDescription: "This course does not have a description yet. Add a short goal later so authors and teachers can identify it faster.",
    testsRecommendedTitle: "Example: \"{course} - final assessment\"",
    questionBankLabel: "Questions in bank",
    testsBankEmpty: "No questions yet",
    testsLengthShort: "short format",
    testsLengthBalanced: "balanced format",
    testsLengthExtended: "extended format",
    testsAdaptiveBehavior: "How this behaves",
    testsAdaptiveBehaviorHint: "The learner will start at level {difficulty}. The system will ask up to {limit} questions and move the difficulty up or down as the attempt progresses.",
    questionEditorTitle: "Questions inside the test",
    questionEditorHint: "Once the test shell exists, add the actual questions, answer options, and topic links here. One correct answer is required.",
    selectTestForQuestions: "Test to populate",
    selectTestFirst: "Create or choose a test for the selected course first.",
    questionText: "Question text",
    questionExplanation: "Post-answer explanation",
    questionDifficulty: "Question difficulty",
    questionEstimatedSeconds: "Expected answer time, sec",
    questionTopics: "Question topics",
    questionOptions: "Answer options",
    questionCorrectOption: "Correct option",
    addAnswerOption: "Add option",
    removeAnswerOption: "Remove option",
    createQuestionAction: "Add question",
    saveQuestionAction: "Save question",
    editQuestionAction: "Edit",
    cancelQuestionEditing: "Reset edits",
    questionsInTest: "Questions in test",
    optionCount: "Options",
    noTopicsAvailable: "No topics available yet. You can still save the question without topic links.",
    noQuestionsInTest: "No questions in this test yet.",
    questionCreated: "Question added",
    questionUpdated: "Question updated",
    failedSaveQuestion: "Failed to save question",
    editingQuestionLabel: "Editing question #{id}",
    answerOptionLabel: "Option {number}",
    assignmentsPageTitle: "Assignments",
    assignmentsPageSubtitle: "Assign a course to an individual learner.",
    assignCourse: "Assign course",
    assign: "Assign",
    howToDemo: "How to demo",
    howToDemo1: "Select a course and learner.",
    howToDemo2: "Submit the assignment, then open the mobile learner app or learner account to see the course.",
    howToDemo3: "The backend also records a mock notification delivery for the assignment event.",
    analyticsPageTitle: "Analytics",
    analyticsPageSubtitle: "Track course performance and inspect an individual learner.",
    overview: "Overview",
    learnerDetail: "Learner detail",
    learnerId: "Learner ID",
    load: "Load",
    loadingAnalytics: "Loading analytics...",
    settingsPageTitle: "Settings & Profile",
    settingsPageSubtitle: "Current operator details and tenant context.",
    profile: "Profile",
    loadingProfile: "Loading profile...",
    currentRole: "Current role",
    name: "Name",
    code: "Code",
    locale: "Locale",
    currentTenant: "Current tenant",
    availableTenants: "Available tenants",
    loadingCurrentTenant: "Loading current tenant...",
    switch: "Switch",
    tenantSwitchTitle: "Tenant switching",
    tenantSwitchSubtitle: "Move between organizations available to the current account.",
    dashboardTitle: "Dashboard",
    dashboardSubtitle: "Operational overview for the current organization.",
    loadingMetrics: "Loading metrics...",
    courseProgress: "Course progress",
    columnCourse: "Course",
    averageProgress: "Average progress",
    learners: "Learners",
    problemTopics: "Problem topics",
    topicId: "Topic ID",
    recommendations: "Recommendations",
    metricUsers: "Active users",
    metricCourses: "Courses",
    metricTests: "Tests",
    metricActiveAttempts: "Active attempts",
    metricEnrollments: "Course assignments",
    metricAverageProgress: "Average progress",
    metricRecommendationsBacklog: "Active recommendations",
    dashboardCourseHealthTitle: "Course health",
    dashboardCourseHealthSubtitle: "These cards show which courses are progressing well and which ones are stalling.",
    dashboardAttentionTitle: "Needs attention",
    dashboardAttentionSubtitle: "The topics below appear most often in adaptive-test recommendations.",
    dashboardNoCourseProgress: "No course assignments or progress yet.",
    dashboardNoProblemTopics: "No priority topics yet.",
    dashboardLearnersLabel: "learners",
    dashboardRecommendationsLabel: "recommendations",
    id: "ID",
    title: "Title",
    courseId: "Course ID",
    userCreated: "User created",
    failedCreateUser: "Failed to create user",
    failedUpdateUser: "Failed to update user",
    courseUpdated: "Course updated",
    courseCreated: "Course created",
    courseDeleted: "Course deleted",
    failedSaveCourse: "Failed to save course",
    failedDeleteCourse: "Failed to delete course",
    deleteCourseConfirm: "Delete this course and all of its lessons? This action cannot be undone.",
    courseEditorRestrictedTitle: "Course editor unavailable",
    courseEditorRestrictedBody: "This account is a learner. Only teachers, organization admins, and system admins can create or edit courses.",
    lessonUpdated: "Lesson updated",
    lessonCreated: "Lesson created",
    failedSaveLesson: "Failed to save lesson",
    draftingLesson: "Drafting a new lesson in the selected course.",
    noLinkedLesson: "No linked lesson",
    action: "Action",
    priority: "Priority",
    noWeakTopics: "No weak topics",
    emptyAttempt: "No attempt yet",
    loadingUsers: "Loading users...",
    organizationWorkspace: "Coursum workspace",
    learner: "Learner"
  }
} as const;

type UiMessages = Record<keyof (typeof MESSAGES)["en"], string>;

function getMessages(language: Language): UiMessages {
  return { ...MESSAGES.en, ...MESSAGES[language] };
}

const LanguageContext = createContext<{
  language: Language;
  setLanguage: (value: Language) => void;
  t: UiMessages;
}>({
  language: "ru",
  setLanguage: () => undefined,
  t: getMessages("ru")
});

function getInitialLanguage(): Language {
  if (typeof window === "undefined") return "ru";
  const saved = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return saved === "en" ? "en" : "ru";
}

function normalizeTenantCode(value: string) {
  return value.trim().toLowerCase();
}

function normalizeLogin(value: string) {
  return value.trim().toLowerCase();
}

function buildSavedAccountId(organizationCode: string, login: string) {
  return `${normalizeTenantCode(organizationCode)}::${normalizeLogin(login)}`;
}

function normalizeSession(nextSession: SessionState): SessionState {
  return {
    ...nextSession,
    tenantCode: normalizeTenantCode(nextSession.tenantCode),
    refreshToken: nextSession.refreshToken?.trim() || undefined,
  };
}

function readStoredSession(): SessionState | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<SessionState>;
    if (typeof parsed.accessToken !== "string" || !parsed.accessToken.trim()) {
      return null;
    }
    if (typeof parsed.tenantCode !== "string" || !parsed.tenantCode.trim()) {
      return null;
    }
    return normalizeSession({
      accessToken: parsed.accessToken,
      tenantCode: parsed.tenantCode,
      refreshToken: typeof parsed.refreshToken === "string" && parsed.refreshToken.trim() ? parsed.refreshToken : undefined,
    });
  } catch {
    return null;
  }
}

function writeStoredSession(session: SessionState | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (!session) {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(
    SESSION_STORAGE_KEY,
    JSON.stringify({
      accessToken: session.accessToken,
      refreshToken: session.refreshToken ?? "",
      tenantCode: normalizeTenantCode(session.tenantCode),
    }),
  );
}

function readSavedAccounts(): SavedAccount[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(SAVED_ACCOUNTS_STORAGE_KEY);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .map((item) => {
        if (!item || typeof item !== "object") {
          return null;
        }
        const row = item as Partial<SavedAccount>;
        if (typeof row.organizationCode !== "string" || !row.organizationCode.trim()) {
          return null;
        }
        if (typeof row.login !== "string" || !row.login.trim()) {
          return null;
        }
        const organizationCode = normalizeTenantCode(row.organizationCode);
        const login = normalizeLogin(row.login);
        const id = typeof row.id === "string" && row.id.trim()
          ? row.id
          : buildSavedAccountId(organizationCode, login);
        const lastUsedAt = typeof row.lastUsedAt === "string" && row.lastUsedAt.trim()
          ? row.lastUsedAt
          : new Date(0).toISOString();
        const displayName =
          typeof row.displayName === "string" && row.displayName.trim() ? row.displayName.trim() : undefined;
        return {
          id,
          organizationCode,
          login,
          displayName,
          lastUsedAt,
        } as SavedAccount;
      })
      .filter((item): item is SavedAccount => Boolean(item))
      .sort((a, b) => Date.parse(b.lastUsedAt) - Date.parse(a.lastUsedAt));
  } catch {
    return [];
  }
}

function writeSavedAccounts(accounts: SavedAccount[]) {
  if (typeof window === "undefined") {
    return;
  }
  if (!accounts.length) {
    window.localStorage.removeItem(SAVED_ACCOUNTS_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(SAVED_ACCOUNTS_STORAGE_KEY, JSON.stringify(accounts));
}

function upsertSavedAccount(accounts: SavedAccount[], incoming: SavedAccount): SavedAccount[] {
  const normalizedIncoming: SavedAccount = {
    ...incoming,
    id: buildSavedAccountId(incoming.organizationCode, incoming.login),
    organizationCode: normalizeTenantCode(incoming.organizationCode),
    login: normalizeLogin(incoming.login),
    lastUsedAt: incoming.lastUsedAt,
    displayName: incoming.displayName?.trim() || undefined,
  };
  const filtered = accounts.filter((item) => item.id !== normalizedIncoming.id);
  const next = [normalizedIncoming, ...filtered];
  next.sort((a, b) => Date.parse(b.lastUsedAt) - Date.parse(a.lastUsedAt));
  return next;
}

function useUi() {
  return useContext(LanguageContext);
}

export function AppTestProviders({ children, language = "ru" }: { children: ReactNode; language?: Language }) {
  return (
    <LanguageContext.Provider value={{ language, setLanguage: () => undefined, t: getMessages(language) }}>
      {children}
    </LanguageContext.Provider>
  );
}

function formatDashboardMetricLabel(key: string, t: UiMessages) {
  const labels: Record<string, string> = {
    users: t.metricUsers,
    courses: t.metricCourses,
    tests: t.metricTests,
    active_attempts: t.metricActiveAttempts,
    enrollments: t.metricEnrollments,
    avg_progress: t.metricAverageProgress,
    recommendations: t.metricRecommendationsBacklog,
  };
  return labels[key] ?? key.replace(/_/g, " ");
}

type TenantInfo = { id: number; name: string; code: string; locale: string };
type UserInfo = { id: number; email: string; full_name: string; is_active: boolean };
type UserProfileInfo = { id: number; email: string; full_name: string; tenant_role?: string | null };
type CourseInfo = {
  id: number;
  title: string;
  description: string;
  is_published: boolean;
  status?: "draft" | "published" | "archived" | string;
  image_url?: string | null;
  category?: string | null;
  access_settings?: Record<string, unknown>;
  available_from?: string | null;
  available_to?: string | null;
};
type SectionInfo = { id: number; course_id: number; title: string; sort_order: number; is_visible: boolean };
type LessonInfo = {
  id: number;
  course_id: number;
  section_id?: number | null;
  title: string;
  summary: string;
  content: string;
  content_pages?: Array<{
    page_id?: string;
    chapter_title: string;
    page_title: string;
    blocks: Array<{ type: string; text?: string; html?: string; url?: string; alt?: string; title?: string }>;
  }> | null;
  duration_minutes: number;
  image_url?: string | null;
  video_url?: string | null;
  is_visible?: boolean;
  is_published?: boolean;
  sort_order: number;
};
type CourseStaffInfo = {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  role_name: string;
};
type CoursePreviewInfo = {
  course: CourseInfo;
  sections: SectionInfo[];
  lessons: Array<{
    id: number;
    section_id?: number | null;
    title: string;
    summary: string;
    duration_minutes: number;
  }>;
};
type EditorRecommendationInfo = {
  id: number;
  tenant_id: number;
  course_id?: number | null;
  lesson_id?: number | null;
  title: string;
  text: string;
  is_active: boolean;
  sort_order: number;
};
type TestInfo = { id: number; title: string; course_id: number; baseline_difficulty?: number; question_limit: number; question_count?: number };
type TopicInfo = { id: number; title: string; description?: string };
type TestQuestionOptionInfo = { id?: number; text: string; is_correct: boolean };
type TestQuestionInfo = {
  id: number;
  test_id: number;
  text: string;
  explanation: string;
  difficulty: number;
  estimated_seconds: number;
  option_count: number;
  options?: TestQuestionOptionInfo[];
  topic_ids?: number[];
  topic_titles: string[];
};
type AssignmentInfo = {
  id: number;
  course_id: number;
  lesson_id?: number | null;
  title: string;
  description: string;
  is_active: boolean;
  due_at?: string | null;
  created_at: string;
};
type AssignmentSubmissionInfo = {
  id: number;
  assignment_id: number;
  student_user_id: number;
  status: string;
  text_answer: string;
  link_answer?: string | null;
  submitted_at?: string | null;
  updated_at: string;
  latest_review?: { status: string; comment: string; reviewer_user_id: number; created_at: string } | null;
};
type MediaKind = "image" | "video" | "document";
type MediaAssetInfo = { path: string; label: string; kind: MediaKind; size_bytes: number; filename: string; mime_type: string };
type LessonPageDraft = {
  id: string;
  chapterTitle: string;
  pageTitle: string;
  html: string;
  imageUrl: string;
  videoUrl: string;
};
type MediaPickerTarget = {
  scope: "page" | "lesson" | "html";
  kind: MediaKind;
  pageId?: string;
  htmlSelection?: TextSelection;
};
type TextSelection = {
  start: number;
  end: number;
};
type PendingHtmlSnippet = {
  pageId: string;
  snippet: string;
  nonce: number;
  selection?: TextSelection;
};

function formatRoleLabel(roleName: string | null | undefined, t: UiMessages) {
  switch (roleName) {
    case "learner":
      return t.roleLearner;
    case "teacher":
      return t.roleTeacher;
    case "org_admin":
      return t.roleOrgAdmin;
    case "system_admin":
      return t.roleSystemAdmin;
    default:
      return roleName ?? "-";
  }
}

function canManageCourses(roleName: string | null | undefined) {
  return roleName === "teacher" || roleName === "org_admin" || roleName === "system_admin";
}

function canAccessWebPanel(roleName: string | null | undefined) {
  return canManageCourses(roleName);
}

function parseCourseIdParam(value: string | null) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function normalizeCourseStatus(value: unknown): "draft" | "published" | "archived" {
  if (value === "published" || value === "archived") {
    return value;
  }
  return "draft";
}

function getCourseStatusLabel(status: "draft" | "published" | "archived", language: Language) {
  if (status === "published") {
    return language === "ru" ? "Опубликован" : "Published";
  }
  if (status === "archived") {
    return language === "ru" ? "Архив" : "Archived";
  }
  return language === "ru" ? "Черновик" : "Draft";
}

function formatDateTimeLocalValue(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

type CourseEditorFormState = {
  title: string;
  description: string;
  imageUrl: string;
  status: "draft" | "published" | "archived";
  category: string;
  selfEnrollment: boolean;
  contentLanguage: string;
  availableFrom: string;
  availableTo: string;
};

function getDefaultCourseForm(language: Language): CourseEditorFormState {
  return {
    title: "",
    description: "",
    imageUrl: "",
    status: "draft",
    category: "",
    selfEnrollment: false,
    contentLanguage: language,
    availableFrom: "",
    availableTo: "",
  };
}

function buildCourseFormFromCourse(course: CourseInfo, language: Language): CourseEditorFormState {
  const accessSettings = course.access_settings ?? {};
  const languageValue = typeof accessSettings.language === "string" && accessSettings.language.trim()
    ? accessSettings.language
    : language;
  return {
    title: course.title,
    description: course.description,
    imageUrl: course.image_url ?? "",
    status: normalizeCourseStatus(course.status),
    category: course.category ?? "",
    selfEnrollment: Boolean(accessSettings.self_enrollment ?? accessSettings.open_enrollment ?? false),
    contentLanguage: languageValue,
    availableFrom: formatDateTimeLocalValue(course.available_from),
    availableTo: formatDateTimeLocalValue(course.available_to),
  };
}

function toIsoDateOrNull(value: string) {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString();
}

function createLessonPageDraft(index = 1, language: Language = "ru"): LessonPageDraft {
  const ru = language === "ru";
  return {
    id: `page-${Date.now()}-${Math.round(Math.random() * 100000)}-${index}`,
    chapterTitle: index === 1 ? (ru ? "Контекст" : "Context") : ru ? "Практика" : "Practice",
    pageTitle: index === 1 ? (ru ? "Введение" : "Introduction") : ru ? `Страница ${index}` : `Page ${index}`,
    html: "",
    imageUrl: "",
    videoUrl: ""
  };
}

function buildLessonPagesPayload(pages: LessonPageDraft[]) {
  return pages.map((page, index) => ({
    page_id: page.id || `page-${index + 1}`,
    chapter_title: page.chapterTitle.trim() || `Chapter ${index + 1}`,
    page_title: page.pageTitle.trim() || `Page ${index + 1}`,
    blocks: [
      ...(page.html.trim() ? [{ type: "html", html: page.html.trim() }] : []),
      ...(page.imageUrl.trim() ? [{ type: "image", url: page.imageUrl.trim(), alt: page.pageTitle.trim() || `Page ${index + 1}` }] : []),
      ...(page.videoUrl.trim() ? [{ type: "video", url: page.videoUrl.trim(), title: page.pageTitle.trim() || `Page ${index + 1}` }] : [])
    ]
  }));
}

function htmlToPlainText(html: string) {
  if (!html.trim()) return "";
  if (typeof window === "undefined" || typeof DOMParser === "undefined") {
    return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  }
  const parser = new DOMParser();
  const doc = parser.parseFromString(`<div>${html}</div>`, "text/html");
  return doc.body.textContent?.replace(/\s+/g, " ").trim() ?? "";
}

function buildLegacyLessonContent(summary: string, pages: LessonPageDraft[]) {
  const normalizedPages = pages.filter((page) => page.html.trim() || page.chapterTitle.trim() || page.pageTitle.trim());
  const sections = normalizedPages.map(
    (page) => `## ${page.pageTitle.trim() || "Lesson page"}\n${htmlToPlainText(page.html) || summary.trim() || "Structured page content"}`
  );
  return sections.join("\n\n");
}

function buildLessonUpdatePayloadFromLesson(lesson: LessonInfo, patch: Partial<{
  course_id: number;
  section_id: number | null;
  title: string;
  summary: string;
  content: string;
  content_pages: LessonInfo["content_pages"];
  duration_minutes: number;
  image_url: string | null;
  video_url: string | null;
  sort_order: number;
  is_visible: boolean;
  is_published: boolean;
}>) {
  return {
    course_id: patch.course_id ?? lesson.course_id,
    section_id: patch.section_id ?? lesson.section_id ?? null,
    title: patch.title ?? lesson.title,
    summary: patch.summary ?? lesson.summary,
    content: patch.content ?? lesson.content,
    content_pages: patch.content_pages ?? lesson.content_pages ?? [],
    duration_minutes: patch.duration_minutes ?? lesson.duration_minutes,
    image_url: patch.image_url ?? lesson.image_url ?? null,
    video_url: patch.video_url ?? lesson.video_url ?? null,
    sort_order: patch.sort_order ?? lesson.sort_order,
    is_visible: patch.is_visible ?? lesson.is_visible ?? true,
    is_published: patch.is_published ?? lesson.is_published ?? true,
  };
}

function escapeHtml(value: string) {
  return value
    .split("&")
    .join("&amp;")
    .split("<")
    .join("&lt;")
    .split(">")
    .join("&gt;")
    .split('"')
    .join("&quot;");
}

function buildDraftPagesFromLesson(lesson: LessonInfo): LessonPageDraft[] {
  const pages = lesson.content_pages ?? [];
  if (!pages.length) {
    return [
      {
        id: `page-${lesson.id}-1`,
        chapterTitle: lesson.title,
        pageTitle: lesson.title,
        html: `<p>${escapeHtml(lesson.summary || lesson.content)}</p>`,
        imageUrl: lesson.image_url ?? "",
        videoUrl: lesson.video_url ?? ""
      }
    ];
  }
  return pages.map((page, index) => {
    const html = page.blocks
      .map((block) => {
        if (block.type === "html") return block.html?.trim() || "";
        if (block.type === "text" && block.text?.trim()) {
          return `<p>${escapeHtml(block.text.trim()).split("\n").join("<br />")}</p>`;
        }
        return "";
      })
      .filter(Boolean)
      .join("\n\n");
    const imageBlock = page.blocks.find((block) => block.type === "image");
    const videoBlock = page.blocks.find((block) => block.type === "video");
    return {
      id: page.page_id || `page-${lesson.id}-${index + 1}`,
      chapterTitle: page.chapter_title,
      pageTitle: page.page_title,
      html,
      imageUrl: imageBlock?.url || "",
      videoUrl: videoBlock?.url || ""
    };
  });
}

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function getMediaKindLabel(kind: MediaKind, t: UiMessages) {
  if (kind === "image") return t.attachImage;
  if (kind === "video") return t.attachVideo;
  return t.attachDocument;
}

function getMediaDialogTitle(kind: MediaKind, t: UiMessages) {
  if (kind === "image") return t.mediaDialogImageTitle;
  if (kind === "video") return t.mediaDialogVideoTitle;
  return t.mediaDialogDocumentTitle;
}

function getMediaUploadHint(kind: MediaKind, t: UiMessages) {
  if (kind === "image") return t.mediaDialogUploadHintImage;
  if (kind === "video") return t.mediaDialogUploadHintVideo;
  return t.mediaDialogUploadHintDocument;
}

function buildDocumentLinkSnippet(asset: MediaAssetInfo) {
  const rawLabel = (asset.label || asset.filename || "Document").replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ").trim();
  const label = escapeHtml(rawLabel || "Document");
  return `<a href="${asset.path}" target="_blank" rel="noopener noreferrer">${label}</a>`;
}

function buildMediaHtmlSnippet(asset: MediaAssetInfo) {
  if (asset.kind === "image") {
    const rawAlt = (asset.label || asset.filename || "Image").replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ").trim();
    return `<img src="${asset.path}" alt="${escapeHtml(rawAlt || "Image")}" />`;
  }
  if (asset.kind === "video") {
    return `<video controls preload="metadata" playsinline src="${asset.path}"></video>`;
  }
  return buildDocumentLinkSnippet(asset);
}

function getHtmlMediaInsertLabel(kind: MediaKind, language: Language) {
  if (kind === "image") {
    return language === "ru" ? "Вставить изображение" : "Insert image";
  }
  if (kind === "video") {
    return language === "ru" ? "Вставить видео" : "Insert video";
  }
  return language === "ru" ? "Вставить документ" : "Insert document";
}

const HTML_PREVIEW_TAGS = new Set([
  "p",
  "br",
  "div",
  "span",
  "strong",
  "em",
  "b",
  "i",
  "u",
  "mark",
  "small",
  "code",
  "pre",
  "blockquote",
  "hr",
  "ul",
  "ol",
  "li",
  "h1",
  "h2",
  "h3",
  "h4",
  "table",
  "thead",
  "tbody",
  "tr",
  "th",
  "td",
  "a",
  "img",
  "video",
  "source"
]);
const HTML_PREVIEW_ATTRS: Record<string, string[]> = {
  a: ["href", "title", "target", "rel"],
  img: ["src", "alt", "title"],
  video: ["src", "poster", "controls", "preload", "playsinline"],
  source: ["src", "type"]
};
function getHtmlSnippets(language: Language) {
  const ru = language === "ru";
  return [
    { label: "H2", snippet: ru ? "<h2>Заголовок раздела</h2>\n<p>Опишите основную мысль этого блока.</p>" : "<h2>Section title</h2>\n<p>Write the core explanation here.</p>" },
    { label: "H3", snippet: ru ? "<h3>Подраздел</h3>\n<p>Добавьте следующий важный факт или пояснение.</p>" : "<h3>Subsection</h3>\n<p>Add the next detail here.</p>" },
    { label: ru ? "Список" : "List", snippet: ru ? "<ul>\n  <li>Первый пункт</li>\n  <li>Второй пункт</li>\n</ul>" : "<ul>\n  <li>First point</li>\n  <li>Second point</li>\n</ul>" },
    { label: ru ? "Цитата" : "Quote", snippet: ru ? "<blockquote>Используйте блок для политики, напоминания или важной цитаты.</blockquote>" : "<blockquote>Use this for policy notes, client quotes, or reminders.</blockquote>" },
    { label: ru ? "Код" : "Code", snippet: ru ? "<pre><code>Тема: Обновление запроса\nКонтекст: ...\nДействие: ...</code></pre>" : "<pre><code>Subject: Request update\nContext: ...\nAction needed: ...</code></pre>" },
    {
      label: ru ? "Таблица" : "Table",
      snippet: ru
        ? "<table><thead><tr><th>Шаг</th><th>Ответственный</th></tr></thead><tbody><tr><td>Подтвердить запрос</td><td>Поддержка</td></tr><tr><td>Обновить слушателя</td><td>Менеджер</td></tr></tbody></table>"
        : "<table><thead><tr><th>Step</th><th>Owner</th></tr></thead><tbody><tr><td>Confirm request</td><td>Support</td></tr><tr><td>Update learner</td><td>Manager</td></tr></tbody></table>"
    }
  ];
}

function sanitizePreviewHtml(html: string) {
  if (!html.trim() || typeof window === "undefined" || typeof DOMParser === "undefined") {
    return html;
  }
  const parser = new DOMParser();
  const doc = parser.parseFromString(`<div>${html}</div>`, "text/html");
  const nodes = Array.from(doc.body.querySelectorAll("*"));
  for (const node of nodes) {
    const tag = node.tagName.toLowerCase();
    if (!HTML_PREVIEW_TAGS.has(tag)) {
      node.replaceWith(...Array.from(node.childNodes));
      continue;
    }
    for (const attr of Array.from(node.attributes)) {
      const allowedAttrs = HTML_PREVIEW_ATTRS[tag] ?? [];
      const attrName = attr.name.toLowerCase();
      const attrValue = attr.value.trim();
      const isUnsafeUrl =
        ["href", "src", "poster"].includes(attrName) &&
        /^(javascript:|data:text\/html)/i.test(attrValue);
      if (attrName.startsWith("on") || isUnsafeUrl || (!allowedAttrs.includes(attrName) && attrName !== "class")) {
        node.removeAttribute(attr.name);
        continue;
      }
      if (["href", "src", "poster"].includes(attrName) && attrValue.startsWith("/")) {
        node.setAttribute(attr.name, resolveMediaUrl(attrValue));
      }
    }
  }
  return doc.body.innerHTML;
}

function getMediaAccept(kind: MediaKind) {
  if (kind === "image") return ".png,.jpg,.jpeg,.gif,.webp";
  if (kind === "video") return ".mp4,.webm,.mov,.m4v";
  return ".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt";
}

function normalizeTextSelection(selection: TextSelection | null | undefined, fallback: TextSelection, valueLength: number) {
  const rawStart = selection?.start ?? fallback.start;
  const rawEnd = selection?.end ?? fallback.end;
  const start = Math.min(valueLength, Math.max(0, rawStart));
  const end = Math.min(valueLength, Math.max(start, rawEnd));
  return { start, end };
}

function insertIntoValue(value: string, snippet: string, selection: TextSelection) {
  const { start, end } = normalizeTextSelection(selection, selection, value.length);
  const nextValue = `${value.slice(0, start)}${snippet}${value.slice(end)}`;
  const nextCaret = start + snippet.length;
  return { nextValue, nextCaret };
}

function insertIntoTextArea(textarea: HTMLTextAreaElement, snippet: string, selection?: TextSelection) {
  const fallback = {
    start: textarea.selectionStart ?? textarea.value.length,
    end: textarea.selectionEnd ?? textarea.selectionStart ?? textarea.value.length
  };
  return insertIntoValue(textarea.value, snippet, normalizeTextSelection(selection, fallback, textarea.value.length));
}

function HtmlSourceEditor({
  value,
  onChange,
  label,
  onUploadImage,
  onUploadVideo,
  onUploadDocument,
  pendingSnippet,
  onPendingSnippetApplied,
  onSelectionChange
}: {
  value: string;
  onChange: (value: string) => void;
  label: string;
  onUploadImage?: (selection?: TextSelection) => void;
  onUploadVideo?: (selection?: TextSelection) => void;
  onUploadDocument?: (selection?: TextSelection) => void;
  pendingSnippet?: PendingHtmlSnippet | null;
  onPendingSnippetApplied?: () => void;
  onSelectionChange?: (selection: TextSelection) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const lastSelectionRef = useRef<TextSelection>({ start: value.length, end: value.length });
  const previewHtml = useMemo(() => sanitizePreviewHtml(value), [value]);
  const { language, t } = useUi();
  const snippets = useMemo(() => getHtmlSnippets(language), [language]);

  function rememberSelection(selection: TextSelection, valueLength = value.length) {
    const normalized = normalizeTextSelection(selection, selection, valueLength);
    lastSelectionRef.current = normalized;
    onSelectionChange?.(normalized);
    return normalized;
  }

  function captureSelection() {
    const textarea = textareaRef.current;
    if (!textarea) {
      return rememberSelection(lastSelectionRef.current);
    }
    return rememberSelection({
      start: textarea.selectionStart ?? lastSelectionRef.current.start,
      end: textarea.selectionEnd ?? textarea.selectionStart ?? lastSelectionRef.current.end
    });
  }

  function applySnippet(snippet: string, selection?: TextSelection) {
    const textarea = textareaRef.current;
    if (!textarea) {
      const fallback = { start: value.length, end: value.length };
      const { nextValue, nextCaret } = insertIntoValue(value, snippet, normalizeTextSelection(selection, fallback, value.length));
      onChange(nextValue);
      rememberSelection({ start: nextCaret, end: nextCaret }, nextValue.length);
      return;
    }
    const { nextValue, nextCaret } = insertIntoTextArea(textarea, snippet, selection);
    onChange(nextValue);
    rememberSelection({ start: nextCaret, end: nextCaret }, nextValue.length);
    queueMicrotask(() => {
      textarea.focus();
      textarea.selectionStart = nextCaret;
      textarea.selectionEnd = nextCaret;
    });
  }

  useEffect(() => {
    if (pendingSnippet?.snippet) {
      applySnippet(pendingSnippet.snippet, pendingSnippet.selection);
      onPendingSnippetApplied?.();
    }
  }, [pendingSnippet?.nonce]);

  return (
    <div className="html-editor">
      <div className="html-toolbar">
        <strong>{label}</strong>
        <div className="html-toolbar-actions">
          {snippets.map((item) => (
            <button key={item.label} type="button" className="secondary page-action" onClick={() => applySnippet(item.snippet)}>
              {item.label}
            </button>
          ))}
          {onUploadImage && (
            <button type="button" className="secondary page-action" onClick={() => onUploadImage(captureSelection())}>
              {getHtmlMediaInsertLabel("image", language)}
            </button>
          )}
          {onUploadVideo && (
            <button type="button" className="secondary page-action" onClick={() => onUploadVideo(captureSelection())}>
              {getHtmlMediaInsertLabel("video", language)}
            </button>
          )}
          {onUploadDocument && (
            <button type="button" className="secondary page-action" onClick={() => onUploadDocument(captureSelection())}>
              {getHtmlMediaInsertLabel("document", language)}
            </button>
          )}
        </div>
      </div>
      <div className="html-editor-grid">
        <label className="html-panel">
          <span>{t.htmlSource}</span>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => {
              onChange(event.target.value);
              rememberSelection({
                start: event.target.selectionStart ?? event.target.value.length,
                end: event.target.selectionEnd ?? event.target.selectionStart ?? event.target.value.length
              }, event.target.value.length);
            }}
            onClick={captureSelection}
            onFocus={captureSelection}
            onKeyUp={captureSelection}
            onSelect={captureSelection}
            placeholder={t.htmlPlaceholder}
            rows={12}
          />
        </label>
        <div className="html-panel">
          <span>{t.preview}</span>
          <div className="html-preview" dangerouslySetInnerHTML={{ __html: previewHtml || `<p>${t.noPreviewYet}</p>` }} />
        </div>
      </div>
      <p className="sidebar-text">{t.htmlHelp}</p>
    </div>
  );
}

function MediaSnippetLibrary({
  assets,
  onInsertHtml,
  onAssignImage,
  onAssignVideo
}: {
  assets: MediaAssetInfo[];
  onInsertHtml: (snippet: string) => void;
  onAssignImage: (path: string) => void;
  onAssignVideo: (path: string) => void;
}) {
  const { t } = useUi();
  if (!assets.length) {
    return null;
  }
  return (
    <details className="media-library">
      <summary>{t.localMediaLibrary}</summary>
      <div className="media-library-list">
        {assets.map((asset) => (
          <article className="media-library-item" key={asset.path}>
            <div>
              <strong>{asset.label}</strong>
              <span>
                {asset.kind} • {formatBytes(asset.size_bytes)}
              </span>
              <code>{asset.path}</code>
            </div>
            <div className="media-library-actions">
              {asset.kind === "image" ? (
                <>
                  <button type="button" className="secondary page-action" onClick={() => onAssignImage(asset.path)}>
                    {t.useAsImage}
                  </button>
                  <button
                    type="button"
                    className="secondary page-action"
                    onClick={() => onInsertHtml(`<img src="${asset.path}" alt="${asset.label}" />`)}
                  >
                    {t.insertTag}
                  </button>
                </>
              ) : asset.kind === "video" ? (
                <>
                  <button type="button" className="secondary page-action" onClick={() => onAssignVideo(asset.path)}>
                    {t.useAsVideo}
                  </button>
                  <button
                    type="button"
                    className="secondary page-action"
                    onClick={() => onInsertHtml(`<video controls preload="metadata" src="${asset.path}"></video>`)}
                  >
                    {t.insertTag}
                  </button>
                </>
              ) : (
                <button type="button" className="secondary page-action" onClick={() => onInsertHtml(buildDocumentLinkSnippet(asset))}>
                  {t.insertDocument}
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </details>
  );
}

function PageOutline({
  pages,
  activePageId,
  onSelect
}: {
  pages: LessonPageDraft[];
  activePageId: string;
  onSelect: (pageId: string) => void;
}) {
  const { t } = useUi();
  return (
    <div className="page-outline">
      {pages.map((page, index) => (
        <button
          key={page.id}
          type="button"
          className={`page-chip ${page.id === activePageId ? "active" : ""}`}
          onClick={() => onSelect(page.id)}
        >
          <strong>{index + 1}</strong>
          <span>{page.pageTitle || `${t.page} ${index + 1}`}</span>
        </button>
      ))}
    </div>
  );
}

function MediaFieldPreview({ url, kind, pending = false }: { url: string; kind: MediaKind; pending?: boolean }) {
  const { t } = useUi();
  const [hasError, setHasError] = useState(false);
  const resolvedUrl = useMemo(() => resolveMediaUrl(url.trim()), [url]);

  useEffect(() => {
    setHasError(false);
  }, [resolvedUrl, kind]);

  if (pending) {
    return <div className="media-preview-empty">{t.mediaDialogUploading}</div>;
  }
  if (!url.trim()) {
    return (
      <div className="media-preview-empty">
        {kind === "image" ? t.noImageSelected : kind === "video" ? t.noVideoSelected : t.noDocumentSelected}
      </div>
    );
  }
  if (kind === "document") {
    return (
      <div className="media-preview-empty document-preview">
        <strong>{t.attachDocument}</strong>
        <span>{url.trim().split("/").pop() || url.trim()}</span>
      </div>
    );
  }
  if (hasError) {
    return <div className="media-preview-empty">{t.mediaPreviewError}</div>;
  }
  return (
    <div className="media-preview-frame">
      {kind === "image" ? (
        <img src={resolvedUrl} alt="Media preview" onError={() => setHasError(true)} />
      ) : (
        <video src={resolvedUrl} controls preload="metadata" onError={() => setHasError(true)} />
      )}
    </div>
  );
}

export function MediaAttachmentCard({
  scope,
  kind,
  url,
  onAttach,
  onRemove,
  title,
  attachLabel,
  removeLabel
}: {
  scope: "page" | "lesson";
  kind: MediaKind;
  url: string;
  onAttach: () => void;
  onRemove: () => void;
  title?: string;
  attachLabel?: string;
  removeLabel?: string;
}) {
  const { t } = useUi();
  const resolvedTitle = title ?? (kind === "image" ? t.imageBlockPreview : t.videoBlockPreview);
  const resolvedAttachLabel = attachLabel ?? (kind === "image" ? t.attachImage : t.attachVideo);
  const resolvedRemoveLabel = removeLabel ?? (kind === "image" ? t.removeImage : t.removeVideo);
  return (
    <div className="media-attachment-card" data-testid={`media-attachment-${scope}-${kind}`}>
      <div className="media-attachment-head">
        <strong>{resolvedTitle}</strong>
        <div className="media-attachment-actions">
          <button type="button" className="page-action secondary" onClick={onAttach}>
            {resolvedAttachLabel}
          </button>
          <button type="button" className="page-action secondary" onClick={onRemove} disabled={!url.trim()}>
            {resolvedRemoveLabel}
          </button>
        </div>
      </div>
      <MediaFieldPreview url={url} kind={kind} />
      <span className="sidebar-text">{t.selectedAsset}</span>
      <code className="media-asset-path">{url.trim() || t.noAssetSelected}</code>
    </div>
  );
}

export function MediaPickerDialog({
  open,
  kind,
  assets,
  onClose,
  onSelect,
  onUpload
}: {
  open: boolean;
  kind: MediaKind;
  assets: MediaAssetInfo[];
  onClose: () => void;
  onSelect: (asset: MediaAssetInfo) => void;
  onUpload: (file: File, kind: MediaKind, onProgress?: (progress: number) => void) => Promise<MediaAssetInfo>;
}) {
  const { t } = useUi();
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const [activeTab, setActiveTab] = useState<"upload" | "library">("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [draftPreviewUrl, setDraftPreviewUrl] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [documentLinkText, setDocumentLinkText] = useState("");
  const [libraryQuery, setLibraryQuery] = useState("");

  useEffect(() => {
    if (!open) {
      setActiveTab("upload");
      setSelectedFile(null);
      setDraftPreviewUrl("");
      setError("");
      setUploading(false);
      setUploadProgress(0);
      setDocumentLinkText("");
      setLibraryQuery("");
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    queueMicrotask(() => closeButtonRef.current?.focus());

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) {
        return;
      }
      const focusables = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
        )
      ).filter((element) => !element.hasAttribute("hidden"));
      if (!focusables.length) {
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  useEffect(() => {
    return () => {
      if (draftPreviewUrl) {
        URL.revokeObjectURL(draftPreviewUrl);
      }
    };
  }, [draftPreviewUrl]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setSelectedFile(nextFile);
    setError("");
    setUploadProgress(0);
    if (draftPreviewUrl) {
      URL.revokeObjectURL(draftPreviewUrl);
      setDraftPreviewUrl("");
    }
    if (nextFile) {
      setDraftPreviewUrl(URL.createObjectURL(nextFile));
      if (kind === "document") {
        setDocumentLinkText(nextFile.name.replace(/\.[^.]+$/, ""));
      }
    }
  }

  function assetWithDocumentLabel(asset: MediaAssetInfo): MediaAssetInfo {
    if (kind !== "document") {
      return asset;
    }
    const label = documentLinkText.trim() || asset.label || asset.filename;
    return { ...asset, label };
  }

  async function submitUpload() {
    if (!selectedFile) {
      setError(t.selectFileFirst);
      return;
    }
    setUploading(true);
    setUploadProgress(0);
    setError("");
    try {
      const uploaded = await onUpload(selectedFile, kind, setUploadProgress);
      onSelect(assetWithDocumentLabel(uploaded));
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveLesson);
    } finally {
      setUploading(false);
    }
  }

  if (!open) {
    return null;
  }

  const normalizedLibraryQuery = libraryQuery.trim().toLowerCase();
  const filteredAssets = assets.filter((asset) => {
    if (asset.kind !== kind) {
      return false;
    }
    if (!normalizedLibraryQuery) {
      return true;
    }
    return [asset.label, asset.filename, asset.path, asset.mime_type, asset.kind]
      .join(" ")
      .toLowerCase()
      .includes(normalizedLibraryQuery);
  });
  const title = getMediaDialogTitle(kind, t);
  const isServerProcessing = kind === "video" && uploading && uploadProgress >= 100;
  const visibleUploadProgress = isServerProcessing ? 99 : uploadProgress;

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div
        ref={dialogRef}
        className="modal-dialog media-dialog"
        data-testid="media-picker-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={`media-dialog-title-${kind}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <strong className="studio-eyebrow">{getMediaKindLabel(kind, t)}</strong>
            <h3 id={`media-dialog-title-${kind}`}>{title}</h3>
          </div>
          <button ref={closeButtonRef} type="button" className="page-action secondary" onClick={onClose}>
            {t.modalClose}
          </button>
        </div>

        <div className="modal-tabs" role="tablist" aria-label={title}>
          <button type="button" className={`modal-tab ${activeTab === "upload" ? "active" : ""}`} onClick={() => setActiveTab("upload")}>
            {t.mediaDialogUploadTab}
          </button>
          <button type="button" className={`modal-tab ${activeTab === "library" ? "active" : ""}`} onClick={() => setActiveTab("library")}>
            {t.mediaDialogLibraryTab}
          </button>
        </div>

        {error && <Notice text={error} tone="error" />}

        {activeTab === "upload" ? (
          <div className="modal-section stack">
            <label className="form-card compact">
              <span>{t.mediaDialogChooseFile}</span>
              <input type="file" accept={getMediaAccept(kind)} onChange={handleFileChange} />
              <span className="form-helper">{getMediaUploadHint(kind, t)}</span>
            </label>
            {kind === "document" && (
              <label className="form-card compact">
                <span>{t.mediaDialogDocumentLinkText}</span>
                <input value={documentLinkText} onChange={(event) => setDocumentLinkText(event.target.value)} placeholder={selectedFile?.name.replace(/\.[^.]+$/, "") || t.mediaDialogDocumentLinkText} />
              </label>
            )}
            <div className="media-dialog-preview">
              <MediaFieldPreview url={draftPreviewUrl} kind={kind} pending={uploading} />
              <code className="media-asset-path">{selectedFile?.name ?? t.noAssetSelected}</code>
            </div>
            {uploading && (
              <div className="media-upload-progress" aria-live="polite">
                <div className="media-upload-progress-meta">
                  <strong>{t.mediaDialogUploadProgress}</strong>
                  <span>{visibleUploadProgress}%</span>
                </div>
                <div
                  className="media-upload-progress-track"
                  role="progressbar"
                  aria-label={t.mediaDialogUploadProgress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={visibleUploadProgress}
                >
                  <div className="media-upload-progress-value" style={{ width: `${Math.min(100, Math.max(0, visibleUploadProgress))}%` }} />
                </div>
                {isServerProcessing && <span className="form-helper">{t.mediaDialogProcessingHint}</span>}
              </div>
            )}
            <div className="modal-actions">
              <button type="button" onClick={() => void submitUpload()} disabled={!selectedFile || uploading}>
                {isServerProcessing ? t.mediaDialogProcessing : uploading ? t.mediaDialogUploading : t.mediaDialogUploadAction}
              </button>
            </div>
          </div>
        ) : (
          <div className="modal-section media-library-list">
            <label className="media-library-search">
              <span>{t.mediaDialogSearch}</span>
              <input
                value={libraryQuery}
                onChange={(event) => setLibraryQuery(event.target.value)}
                placeholder={t.mediaDialogSearchPlaceholder}
                autoComplete="off"
              />
            </label>
            {kind === "document" && (
              <label className="form-card compact">
                <span>{t.mediaDialogDocumentLinkText}</span>
                <input value={documentLinkText} onChange={(event) => setDocumentLinkText(event.target.value)} placeholder={t.mediaDialogDocumentLinkText} />
              </label>
            )}
            {filteredAssets.length ? (
              filteredAssets.map((asset) => (
                <article className="media-library-item" key={asset.path}>
                  <div className="media-library-body">
                    <MediaFieldPreview url={asset.path} kind={kind} />
                    <div className="stack compact">
                      <strong>{asset.label}</strong>
                      <span>
                        {asset.filename} • {formatBytes(asset.size_bytes)}
                      </span>
                      <code>{asset.path}</code>
                    </div>
                  </div>
                  <div className="media-library-actions">
                    <button type="button" className="page-action secondary" onClick={() => onSelect(assetWithDocumentLabel(asset))}>
                      {t.mediaDialogSelect}
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title={t.mediaDialogNoAssets} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function LessonPagePreviewCard({ page }: { page: LessonPageDraft }) {
  const previewHtml = useMemo(() => sanitizePreviewHtml(page.html), [page.html]);
  const { t } = useUi();
  return (
    <div className="lesson-preview">
      <div className="lesson-preview-head">
        <strong>{t.learnerPreview}</strong>
        <span>
          {page.chapterTitle || t.chapter} / {page.pageTitle || t.page}
        </span>
      </div>
      <div className="html-preview" dangerouslySetInnerHTML={{ __html: previewHtml || `<p>${t.noPageContentYet}</p>` }} />
      {(page.imageUrl.trim() || page.videoUrl.trim()) && (
        <div className="lesson-preview-media">
          {page.imageUrl.trim() && <MediaFieldPreview url={page.imageUrl} kind="image" />}
          {page.videoUrl.trim() && <MediaFieldPreview url={page.videoUrl} kind="video" />}
        </div>
      )}
    </div>
  );
}

function useRemote<T>(path: string | null, session: SessionState | null, refreshKey = 0) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path && session));
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      if (!path || !session) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError("");
      try {
        const payload = (await apiRequest(path, session)) as T;
        if (active) {
          setData(payload);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Request failed");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [path, refreshKey, session]);

  return { data, loading, error, setData };
}

export function LoginPage({
  onLogin,
}: {
  onLogin: (
    value: SessionState,
    options: { login: string; organizationCode: string }
  ) => void;
}) {
  const { language, t } = useUi();
  const [email, setEmail] = useState(() =>
    ENABLE_DEV_AUTH_PREFILL ? DEV_PREFILL_EMAIL : "",
  );
  const [password, setPassword] = useState(() => (ENABLE_DEV_AUTH_PREFILL ? DEV_PREFILL_PASSWORD : ""));
  const [tenantCode, setTenantCode] = useState(() =>
    ENABLE_DEV_AUTH_PREFILL ? DEV_PREFILL_TENANT : "",
  );
  const [error, setError] = useState("");

  async function submit() {
    try {
      const normalizedTenantCode = normalizeTenantCode(tenantCode);
      if (!normalizedTenantCode) {
        setError(language === "ru" ? "Введите код организации" : "Enter tenant code");
        return;
      }
      const tokens = await login(email, password);
      onLogin({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        tenantCode: normalizedTenantCode,
      }, {
        login: normalizeLogin(email),
        organizationCode: normalizedTenantCode,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : t.loginFailed);
    }
  }

  return (
    <section className="login-card">
      <div className="login-brand">
        <img src={websiteLogo} alt="Coursum" />
      </div>
      <h1>{t.loginTitle}</h1>
      <p>{t.loginSubtitle}</p>
      <input
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder={t.email}
      />
      <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder={t.password} />
      <input
        value={tenantCode}
        onChange={(e) => setTenantCode(e.target.value)}
        placeholder={t.tenantCode}
      />
      <button onClick={submit}>{t.signIn}</button>
      {error && <small className="error-text">{error}</small>}
    </section>
  );
}

function Shell({ session, onLogout, onSessionChange }: { session: SessionState; onLogout: () => void; onSessionChange: (value: SessionState) => void }) {
  const { language, t } = useUi();
  const location = useLocation();
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const profile = useRemote<UserProfileInfo>("/auth/me", session, session.tenantCode.length);
  const links = useMemo(
    () => [
      ["/", t.dashboard],
      ["/tenants", t.tenantSwitch],
      ["/users", t.users],
      ["/courses", t.courses],
      ["/lessons", t.lessons],
      ["/tests", t.tests],
      ["/assignments", t.assignments],
      ["/homework-reviews", language === "ru" ? "Проверка ДЗ" : "Homework review"],
      ["/analytics", t.analytics],
      ["/settings", t.settings]
    ],
    [language, t]
  );

  useEffect(() => {
    setIsMobileNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 1100) {
        setIsMobileNavOpen(false);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (!isMobileNavOpen) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isMobileNavOpen]);

  if (profile.loading && !profile.data) {
    return (
      <section className="login-card">
        <h1>{t.loading}</h1>
      </section>
    );
  }

  if (profile.error && !profile.data) {
    return (
      <section className="login-card">
        <h1>{t.loginTitle}</h1>
        <p>{profile.error}</p>
        <button onClick={onLogout}>{t.logout}</button>
      </section>
    );
  }

  if (!canAccessWebPanel(profile.data?.tenant_role)) {
    return (
      <section className="login-card">
        <h1>{language === "ru" ? "Нет доступа" : "Access denied"}</h1>
        <p>
          {language === "ru"
            ? "Эта веб-панель доступна только администраторам и преподавателям."
            : "This web panel is available only for admins and teachers."}
        </p>
        <button onClick={onLogout}>{t.logout}</button>
      </section>
    );
  }

  return (
    <div className={`layout ${isMobileNavOpen ? "layout-mobile-nav-open" : ""}`}>
      <button
        type="button"
        className="mobile-nav-toggle"
        aria-controls="admin-sidebar"
        aria-expanded={isMobileNavOpen}
        aria-label={language === "ru" ? "Открыть навигацию" : "Open navigation"}
        onClick={() => setIsMobileNavOpen((current) => !current)}
      >
        <span />
        <span />
        <span />
      </button>
      {isMobileNavOpen ? (
        <button
          type="button"
          className="mobile-nav-backdrop"
          aria-label={language === "ru" ? "Закрыть навигацию" : "Close navigation"}
          onClick={() => setIsMobileNavOpen(false)}
        />
      ) : null}
      <aside id="admin-sidebar" className={`sidebar ${isMobileNavOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-brand">
          <img src={websiteLogoWhite} alt="Coursum" />
          <button
            type="button"
            className="sidebar-close"
            aria-label={language === "ru" ? "Закрыть меню" : "Close menu"}
            onClick={() => setIsMobileNavOpen(false)}
          >
            ×
          </button>
        </div>
        <h2>{t.tenant}: {session.tenantCode}</h2>
        <p className="sidebar-text">{t.organizationWorkspace}</p>
        <nav>
          {links.map(([href, label]) => (
            <Link
              key={href}
              className={location.pathname === href ? "active" : ""}
              to={href}
              onClick={() => setIsMobileNavOpen(false)}
            >
              {label}
            </Link>
          ))}
        </nav>
        <button className="secondary" onClick={onLogout}>
          {t.logout}
        </button>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<DashboardPage session={session} />} />
          <Route path="/tenants" element={<TenantPage session={session} onSessionChange={onSessionChange} />} />
          <Route path="/users" element={<UsersPage session={session} />} />
          <Route path="/courses" element={<CoursesPage session={session} />} />
          <Route path="/lessons" element={<LessonsPage session={session} />} />
          <Route path="/tests" element={<TestsPage session={session} />} />
          <Route path="/assignments" element={<AssignmentsPage session={session} />} />
          <Route path="/homework-reviews" element={<HomeworkReviewsPage session={session} />} />
          <Route path="/analytics" element={<AnalyticsPage session={session} />} />
          <Route path="/settings" element={<SettingsPage session={session} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function DashboardPage({ session }: { session: SessionState }) {
  const { t } = useUi();
  const stats = useRemote<Record<string, number>>("/analytics/dashboard", session);
  const progress = useRemote<Array<{ course_title: string; avg_progress: number; learners: number }>>("/analytics/course-progress", session);
  const problems = useRemote<Array<{ topic_title: string; recommendations: number }>>("/analytics/problem-topics", session);

  const metricOrder = ["users", "enrollments", "avg_progress", "courses", "tests", "active_attempts", "recommendations"] as const;
  const statsData = stats.data ?? {};

  return (
    <section className="page-stack">
      <PageHeader title={t.dashboardTitle} subtitle={t.dashboardSubtitle} />
      <section className="stats-grid">
        {stats.loading && <EmptyState title={t.loadingMetrics} />}
        {stats.data &&
          metricOrder.filter((key) => key in statsData).map((key) => (
            <article className="metric-card" key={key}>
              <span>{formatDashboardMetricLabel(key, t)}</span>
              <strong>{key === "avg_progress" ? `${statsData[key]}%` : statsData[key]}</strong>
            </article>
          ))}
      </section>
      <section className="grid two-columns">
        <article className="card dashboard-panel">
          <div className="card-head dashboard-panel-head">
            <div>
              <h3>{t.dashboardCourseHealthTitle}</h3>
              <p className="sidebar-text">{t.dashboardCourseHealthSubtitle}</p>
            </div>
          </div>
          {progress.error && <Notice text={progress.error} tone="error" />}
          {progress.loading ? (
            <EmptyState title={t.loading} />
          ) : (progress.data ?? []).length ? (
            <div className="dashboard-course-list">
              {(progress.data ?? []).map((item) => (
                <article className="dashboard-course-card" key={item.course_title}>
                  <div className="dashboard-course-head">
                    <strong>{item.course_title}</strong>
                    <span>{item.avg_progress}%</span>
                  </div>
                  <div className="dashboard-progress-track" aria-hidden="true">
                    <div className="dashboard-progress-value" style={{ width: `${Math.min(100, Math.max(0, item.avg_progress))}%` }} />
                  </div>
                  <div className="dashboard-course-meta">
                    <span>{item.learners} {t.dashboardLearnersLabel}</span>
                    <span>{t.averageProgress}: {item.avg_progress}%</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title={t.dashboardNoCourseProgress} />
          )}
        </article>

        <article className="card dashboard-panel">
          <div className="card-head dashboard-panel-head">
            <div>
              <h3>{t.dashboardAttentionTitle}</h3>
              <p className="sidebar-text">{t.dashboardAttentionSubtitle}</p>
            </div>
          </div>
          {problems.error && <Notice text={problems.error} tone="error" />}
          {problems.loading ? (
            <EmptyState title={t.loading} />
          ) : (problems.data ?? []).length ? (
            <div className="dashboard-topic-list">
              {(problems.data ?? []).map((item) => (
                <article className="dashboard-topic-card" key={`${item.topic_title}-${item.recommendations}`}>
                  <strong>{item.topic_title}</strong>
                  <span>{item.recommendations} {t.dashboardRecommendationsLabel}</span>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title={t.dashboardNoProblemTopics} />
          )}
        </article>
      </section>
    </section>
  );
}

function TenantPage({ session, onSessionChange }: { session: SessionState; onSessionChange: (value: SessionState) => void }) {
  const { language, t } = useUi();
  const tenants = useRemote<TenantInfo[]>("/tenants", session);
  const current = useRemote<TenantInfo>("/tenants/current", session, session.tenantCode.length);
  const [status, setStatus] = useState("");

  async function switchTenant(code: string) {
    await apiPost("/tenants/select", session, { code });
    onSessionChange({ ...session, tenantCode: code });
    setStatus(language === "ru" ? `Переключено на организацию ${code}` : `Switched to tenant ${code}`);
  }

  return (
    <section className="page-stack">
      <PageHeader title={t.tenantSwitchTitle} subtitle={t.tenantSwitchSubtitle} />
      {status && <Notice text={status} />}
      <section className="grid two-columns">
        <article className="card">
          <h3>{t.currentTenant}</h3>
          {current.data ? <KeyValueList items={[[t.name, current.data.name], [t.code, current.data.code], [t.locale, current.data.locale]]} /> : <EmptyState title={t.loadingCurrentTenant} />}
        </article>
        <article className="card">
          <h3>{t.availableTenants}</h3>
          <div className="stack">
            {(tenants.data ?? []).map((tenant) => (
              <div className="list-row" key={tenant.id}>
                <div>
                  <strong>{tenant.name}</strong>
                  <span>{tenant.code}</span>
                </div>
                <button onClick={() => void switchTenant(tenant.code)}>{t.switch}</button>
              </div>
            ))}
          </div>
        </article>
      </section>
    </section>
  );
}

function UsersPage({ session }: { session: SessionState }) {
  const { language, t } = useUi();
  const [refreshKey, setRefreshKey] = useState(0);
  const users = useRemote<UserInfo[]>("/users", session, refreshKey);
  const [form, setForm] = useState({ email: "", fullName: "", password: "", roleName: "learner" });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await apiPost("/users", session, {
        email: form.email,
        full_name: form.fullName,
        password: form.password,
        role_name: form.roleName
      });
      setForm({ email: "", fullName: "", password: "", roleName: "learner" });
      setRefreshKey((value) => value + 1);
      setStatus(t.userCreated);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedCreateUser);
    }
  }

  async function toggleUser(user: UserInfo) {
    setError("");
    try {
      await apiPatch(`/users/${user.id}`, session, { is_active: !user.is_active });
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? `Пользователь ${user.email} обновлен` : `User ${user.email} updated`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedUpdateUser);
    }
  }

  return (
    <section className="page-stack">
      <PageHeader title={t.usersPageTitle} subtitle={t.usersPageSubtitle} />
      {status && <Notice text={status} />}
      {error && <Notice text={error} tone="error" />}
      <section className="grid two-columns users-layout">
        <FormCard title={t.createUser} onSubmit={submit} className="user-create-card">
          <p className="form-helper form-helper-intro">{t.userCreateIntro}</p>
          <div className="user-form-grid">
            <label>
              {t.email}
              <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder={t.email} required />
            </label>
            <label>
              {t.fullName}
              <input value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} placeholder={t.fullName} required />
            </label>
            <label>
              {t.password}
              <input value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={t.password} required />
              <span className="form-helper">{t.userPasswordHint}</span>
            </label>
            <label>
              {t.role}
              <select value={form.roleName} onChange={(e) => setForm({ ...form, roleName: e.target.value })}>
                <option value="learner">{t.roleLearner}</option>
                <option value="teacher">{t.roleTeacher}</option>
                <option value="org_admin">{t.roleOrgAdmin}</option>
              </select>
              <span className="form-helper">{t.userRoleHint}</span>
            </label>
          </div>
          <div className="user-access-note">
            <strong>{t.userAccessGuideTitle}</strong>
            <p>{t.userAccessGuideBody}</p>
          </div>
          <div className="user-form-actions">
            <button type="submit">{t.createUserAction}</button>
          </div>
        </FormCard>
        <article className="card user-directory-card">
          <div className="user-directory-head">
            <h3>{t.userDirectory}</h3>
            <p className="sidebar-text">{t.userDirectorySubtitle}</p>
          </div>
          <div className="stack user-directory-list">
            {(users.data ?? []).map((user) => (
              <div className="list-row user-row" key={user.id}>
                <div className="user-meta">
                  <strong>{user.full_name}</strong>
                  <span>{user.email}</span>
                  <div className="user-subline">
                    <span className={`status-pill ${user.is_active ? "active" : "inactive"}`}>
                      {user.is_active ? t.userStatusActive : t.userStatusInactive}
                    </span>
                  </div>
                </div>
                <div className="user-actions">
                  <button
                    type="button"
                    className={user.is_active ? undefined : "page-action secondary"}
                    onClick={() => void toggleUser(user)}
                  >
                    {user.is_active ? t.deactivate : t.activate}
                  </button>
                </div>
              </div>
            ))}
            {users.loading && <EmptyState title={t.loadingUsers} />}
          </div>
        </article>
      </section>
    </section>
  );
}

export function CoursesPage({ session }: { session: SessionState }) {
  const { language, t } = useUi();
  const [searchParams, setSearchParams] = useSearchParams();
  const [refreshKey, setRefreshKey] = useState(0);
  const courses = useRemote<CourseInfo[]>("/courses", session, refreshKey);
  const profile = useRemote<UserProfileInfo>("/auth/me", session, refreshKey);
  const [mediaRefreshKey, setMediaRefreshKey] = useState(0);
  const mediaAssets = useRemote<MediaAssetInfo[]>("/media/library", session, mediaRefreshKey);
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [isCreatingCourse, setIsCreatingCourse] = useState(false);
  const [coverPickerOpen, setCoverPickerOpen] = useState(false);
  const lessons = useRemote<LessonInfo[]>(
    selectedCourseId ? `/lessons?course_id=${selectedCourseId}` : null,
    session,
    refreshKey + (selectedCourseId ?? 0)
  );
  const sections = useRemote<SectionInfo[]>(
    selectedCourseId ? `/courses/${selectedCourseId}/sections` : null,
    session,
    refreshKey + (selectedCourseId ?? 0)
  );
  const [editingCourseId, setEditingCourseId] = useState<number | null>(null);
  const [form, setForm] = useState<CourseEditorFormState>(() => getDefaultCourseForm(language));
  const [preview, setPreview] = useState<CoursePreviewInfo | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const requestedCourseId = parseCourseIdParam(searchParams.get("courseId"));

  function updateCourseSearchParam(courseId: number | null) {
    const currentValue = searchParams.get("courseId");
    const nextValue = courseId === null ? null : String(courseId);
    if (currentValue === nextValue) {
      return;
    }
    const nextParams = new URLSearchParams(searchParams);
    if (nextValue === null) {
      nextParams.delete("courseId");
    } else {
      nextParams.set("courseId", nextValue);
    }
    setSearchParams(nextParams, { replace: true });
  }

  useEffect(() => {
    if (isCreatingCourse || !courses.data?.length) {
      return;
    }
    const requestedCourse = requestedCourseId ? courses.data.find((course) => course.id === requestedCourseId) ?? null : null;
    if (requestedCourse) {
      if (selectedCourseId !== requestedCourse.id || editingCourseId !== requestedCourse.id) {
        setSelectedCourseId(requestedCourse.id);
        setEditingCourseId(requestedCourse.id);
        setForm(buildCourseFormFromCourse(requestedCourse, language));
      }
      return;
    }
    if (!selectedCourseId) {
      const firstCourse = courses.data[0];
      setSelectedCourseId(firstCourse.id);
      setEditingCourseId(firstCourse.id);
      setForm(buildCourseFormFromCourse(firstCourse, language));
      updateCourseSearchParam(firstCourse.id);
    }
  }, [courses.data, editingCourseId, isCreatingCourse, language, requestedCourseId, selectedCourseId]);

  useEffect(() => {
    if (!selectedCourseId || isCreatingCourse) {
      setPreview(null);
      setPreviewError("");
      return;
    }
    let active = true;
    async function loadPreview() {
      setPreviewLoading(true);
      setPreviewError("");
      try {
        const payload = (await apiRequest(`/courses/${selectedCourseId}/preview`, session)) as CoursePreviewInfo;
        if (active) {
          setPreview(payload);
        }
      } catch (err) {
        if (active) {
          setPreview(null);
          setPreviewError(err instanceof Error ? err.message : language === "ru" ? "Не удалось загрузить предпросмотр курса" : "Failed to load course preview");
        }
      } finally {
        if (active) {
          setPreviewLoading(false);
        }
      }
    }
    void loadPreview();
    return () => {
      active = false;
    };
  }, [isCreatingCourse, language, selectedCourseId, session]);


  function selectCourse(course: CourseInfo) {
    setIsCreatingCourse(false);
    setSelectedCourseId(course.id);
    setEditingCourseId(course.id);
    updateCourseSearchParam(course.id);
    setError("");
    setStatus("");
    setForm(buildCourseFormFromCourse(course, language));
  }

  function startNewCourse() {
    setIsCreatingCourse(true);
    setSelectedCourseId(null);
    setEditingCourseId(null);
    updateCourseSearchParam(null);
    setError("");
    setStatus("");
    setForm(getDefaultCourseForm(language));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const payload = {
        title: form.title,
        description: form.description,
        image_url: form.imageUrl || null,
        status: form.status,
        category: form.category.trim() || null,
        access_settings: {
          self_enrollment: form.selfEnrollment,
          language: form.contentLanguage.trim() || language,
        },
        available_from: toIsoDateOrNull(form.availableFrom),
        available_to: toIsoDateOrNull(form.availableTo),
      };
      const savedCourse = (editingCourseId
        ? await apiPatch(`/courses/${editingCourseId}`, session, payload)
        : await apiPost("/courses", session, payload)) as CourseInfo;
      setIsCreatingCourse(false);
      setSelectedCourseId(savedCourse.id);
      setEditingCourseId(savedCourse.id);
      updateCourseSearchParam(savedCourse.id);
      setForm(buildCourseFormFromCourse(savedCourse, language));
      setRefreshKey((value) => value + 1);
      setStatus(editingCourseId ? t.courseUpdated : t.courseCreated);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveCourse);
    }
  }

  function applySelectedCourseCover(asset: MediaAssetInfo) {
    setForm((current) => ({ ...current, imageUrl: asset.path }));
    setCoverPickerOpen(false);
  }

  async function uploadCourseCover(file: File, kind: MediaKind, onProgress?: (progress: number) => void) {
    const payload = new FormData();
    payload.set("target_kind", kind);
    payload.set("file", file);
    const uploaded = (await apiUpload("/media/upload", session, payload, onProgress)) as MediaAssetInfo;
    setMediaRefreshKey((value) => value + 1);
    return uploaded;
  }

  async function removeCourse() {
    const courseToDelete = (courses.data ?? []).find((course) => course.id === editingCourseId) ?? null;
    if (!editingCourseId || !courseToDelete) {
      return;
    }
    const confirmText = language === "ru"
      ? `Курс будет архивирован, а не удалён безвозвратно.\n\nБудут отключены назначения и доступ учеников к курсу.\n\n${courseToDelete.title}`
      : `The course will be archived instead of permanently deleted.\n\nLearner access and course assignments will be disabled.\n\n${courseToDelete.title}`;
    if (typeof window !== "undefined" && !window.confirm(confirmText)) {
      return;
    }
    setError("");
    setStatus("");
    try {
      await apiDelete(`/courses/${editingCourseId}`, session);
      const nextCourses = (courses.data ?? []).filter((course) => course.id !== editingCourseId);
      courses.setData(nextCourses);
      lessons.setData([]);
      setRefreshKey((value) => value + 1);
      if (nextCourses.length) {
        const nextCourse = nextCourses[0];
        setIsCreatingCourse(false);
        setSelectedCourseId(nextCourse.id);
        setEditingCourseId(nextCourse.id);
        updateCourseSearchParam(nextCourse.id);
        setForm(buildCourseFormFromCourse(nextCourse, language));
      } else {
        startNewCourse();
      }
      setStatus(language === "ru" ? "Курс архивирован" : "Course archived");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedDeleteCourse);
    }
  }

  async function setCourseStatus(nextStatus: "draft" | "published" | "archived") {
    if (!editingCourseId) {
      return;
    }
    setError("");
    setStatus("");
    try {
      const saved = (await apiPatch(`/courses/${editingCourseId}/status`, session, { status: nextStatus })) as CourseInfo;
      setForm(buildCourseFormFromCourse(saved, language));
      setRefreshKey((value) => value + 1);
      setStatus(
        nextStatus === "published"
          ? language === "ru"
            ? "Курс опубликован"
            : "Course published"
          : nextStatus === "archived"
            ? language === "ru"
              ? "Курс отправлен в архив"
              : "Course archived"
            : language === "ru"
              ? "Курс переведён в черновик"
              : "Course moved to draft"
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось обновить статус курса" : "Failed to update course status");
    }
  }


  const selectedCourse = (courses.data ?? []).find((course) => course.id === selectedCourseId) ?? null;
  const canEditCourses = profile.data ? canManageCourses(profile.data.tenant_role) : true;
  const courseEditorLocked = profile.data?.tenant_role === "learner";
  const selectedCourseStatus = normalizeCourseStatus(selectedCourse?.status ?? form.status);
  const previewSectionTitles = new Map((preview?.sections ?? []).map((section) => [section.id, section.title]));

  return (
    <section className="page-stack">
      <PageHeader
        title={t.coursesPageTitle}
        subtitle={t.coursesPageSubtitle}
      />
      {status && <Notice text={status} />}
      {error && <Notice text={error} tone="error" />}
      <section className="lessons-builder">
        <aside className="card studio-sidebar lessons-sidebar">
          <div className="studio-sidebar-head">
            <div>
              <strong className="studio-eyebrow">{t.courseCatalog}</strong>
              <h3>{t.curriculumContainers}</h3>
              <p className="sidebar-text">{t.selectCourseToEdit}</p>
            </div>
            <button type="button" className="page-action secondary" onClick={startNewCourse} disabled={!canEditCourses}>
              {t.newCourse}
            </button>
          </div>
          <div className="studio-list">
            {(courses.data ?? []).map((course) => (
              <button
                key={course.id}
                type="button"
                className={`studio-list-item ${course.id === selectedCourseId ? "active" : ""}`}
                onClick={() => selectCourse(course)}
              >
                <div className="studio-list-main">
                  <strong>{course.title}</strong>
                  <span>{course.description || t.noDescriptionYet}</span>
                </div>
                <span className="studio-list-meta">#{course.id}</span>
              </button>
            ))}
            {courses.loading && <EmptyState title={t.loadingCourses} />}
            {courses.error && <EmptyState title={courses.error} />}
          </div>
        </aside>

        <div className="studio-workspace">
          {courseEditorLocked ? (
            <section className="card studio-panel form-card">
              <div className="studio-panel-head">
                <div>
                  <strong className="studio-eyebrow">{t.courseSettings}</strong>
                  <h3>{t.courseEditorRestrictedTitle}</h3>
                </div>
              </div>
              <Notice text={t.courseEditorRestrictedBody} tone="error" />
              <div className="user-access-note">
                <strong>{t.currentRole}</strong>
                <p>{formatRoleLabel(profile.data?.tenant_role, t)}</p>
              </div>
            </section>
          ) : (
            <form className="card studio-panel form-card" onSubmit={submit}>
              <div className="studio-panel-head">
                <div>
                  <strong className="studio-eyebrow">{editingCourseId ? t.courseSettings : t.createCourseLabel}</strong>
                  <h3>{editingCourseId ? t.editSelectedCourse : t.createCourseShell}</h3>
                </div>
                <div className="studio-actions compact">
                  {editingCourseId && <span className="status-pill active">{getCourseStatusLabel(selectedCourseStatus, language)}</span>}
                  {selectedCourse && (
                    <Link className="page-action secondary" to={`/lessons?courseId=${selectedCourse.id}`}>
                      {t.openLessonBuilder}
                    </Link>
                  )}
                </div>
              </div>
              <div className="studio-form-grid">
                <label>
                  {t.courseTitle}
                  <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder={t.courseTitle} required />
                </label>
                <label>
                  {language === "ru" ? "Статус курса" : "Course status"}
                  <select value={form.status} onChange={(e) => setForm({ ...form, status: normalizeCourseStatus(e.target.value) })}>
                    <option value="draft">{language === "ru" ? "Черновик" : "Draft"}</option>
                    <option value="published">{language === "ru" ? "Опубликован" : "Published"}</option>
                    <option value="archived">{language === "ru" ? "Архив" : "Archived"}</option>
                  </select>
                </label>
                <label>
                  {language === "ru" ? "Категория" : "Category"}
                  <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder={language === "ru" ? "Например, Soft Skills" : "For example, Soft Skills"} />
                </label>
                <label>
                  {language === "ru" ? "Язык контента" : "Content language"}
                  <input value={form.contentLanguage} onChange={(e) => setForm({ ...form, contentLanguage: e.target.value })} placeholder="ru / en" />
                </label>
                <label>
                  {language === "ru" ? "Доступен с" : "Available from"}
                  <input type="datetime-local" value={form.availableFrom} onChange={(e) => setForm({ ...form, availableFrom: e.target.value })} />
                </label>
                <label>
                  {language === "ru" ? "Доступен до" : "Available to"}
                  <input type="datetime-local" value={form.availableTo} onChange={(e) => setForm({ ...form, availableTo: e.target.value })} />
                </label>
                <label className="studio-form-span">
                  {t.description}
                  <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder={t.courseDescriptionPlaceholder} rows={5} />
                </label>
                <label className="studio-form-span">
                  <span>{language === "ru" ? "Настройки доступа" : "Access settings"}</span>
                  <div className="course-access-checkbox">
                    <input id="course-self-enrollment" type="checkbox" checked={form.selfEnrollment} onChange={(e) => setForm({ ...form, selfEnrollment: e.target.checked })} />
                    <label htmlFor="course-self-enrollment">{language === "ru" ? "Разрешить само-запись слушателя" : "Allow learner self-enrollment"}</label>
                  </div>
                </label>
                <div className="studio-form-span stack compact">
                  <span>{t.courseCover}</span>
                  <span className="form-helper">{t.courseCoverHint}</span>
                  <MediaAttachmentCard
                    scope="lesson"
                    kind="image"
                    url={form.imageUrl}
                    title={t.courseCover}
                    onAttach={() => setCoverPickerOpen(true)}
                    onRemove={() => setForm((current) => ({ ...current, imageUrl: "" }))}
                  />
                  {mediaAssets.error && <span className="form-helper">{mediaAssets.error}</span>}
                </div>
              </div>
              <div className="studio-actions">
                <button type="submit">{editingCourseId ? t.saveCourse : t.createCourseAction}</button>
                {editingCourseId && (
                  <button type="button" className="page-action secondary" onClick={startNewCourse}>
                    {t.createAnotherCourse}
                  </button>
                )}
                {editingCourseId && selectedCourseStatus !== "published" && (
                  <button type="button" className="page-action secondary" onClick={() => void setCourseStatus("published")}>
                    {language === "ru" ? "Опубликовать" : "Publish"}
                  </button>
                )}
                {editingCourseId && selectedCourseStatus === "published" && (
                  <button type="button" className="page-action secondary" onClick={() => void setCourseStatus("draft")}>
                    {language === "ru" ? "Снять с публикации" : "Unpublish"}
                  </button>
                )}
                {editingCourseId && selectedCourseStatus !== "archived" && (
                  <button type="button" className="page-action secondary" onClick={() => void setCourseStatus("archived")}>
                    {language === "ru" ? "В архив" : "Archive"}
                  </button>
                )}
                {editingCourseId && selectedCourseStatus === "archived" && (
                  <button type="button" className="page-action secondary" onClick={() => void setCourseStatus("draft")}>
                    {language === "ru" ? "Восстановить из архива" : "Restore from archive"}
                  </button>
                )}
                {editingCourseId && (
                  <button type="button" className="page-action secondary" onClick={() => void removeCourse()}>
                    {t.deleteCourse}
                  </button>
                )}
              </div>
            </form>
          )}

          <section className="card studio-panel">
            <div className="studio-panel-head">
              <div>
                <strong className="studio-eyebrow">{t.curriculumPreview}</strong>
                <h3>{selectedCourse ? selectedCourse.title : t.selectCourse}</h3>
              </div>
              <span className="studio-list-meta">{lessons.data?.length ?? 0} {t.lessonsCount}</span>
            </div>
            {selectedCourse ? (
              <div className="stack">
                <article className="course-preview-block">
                  <div className="course-preview-head">
                    <strong>{language === "ru" ? "Предпросмотр как ученик" : "Preview as learner"}</strong>
                    {previewLoading && <span className="studio-list-meta">{t.loading}</span>}
                  </div>
                  {previewError && <span className="form-helper">{previewError}</span>}
                  <div className="course-preview-list">
                    {(preview?.lessons ?? []).map((lesson) => (
                      <div className="course-preview-item" key={`preview-${lesson.id}`}>
                        <div>
                          <strong>{lesson.title}</strong>
                          <span>{previewSectionTitles.get(lesson.section_id ?? -1) ?? (language === "ru" ? "Без секции" : "No section")}</span>
                        </div>
                        <span>{lesson.duration_minutes} {language === "ru" ? "мин" : "min"}</span>
                      </div>
                    ))}
                    {!previewLoading && !(preview?.lessons ?? []).length && <EmptyState title={language === "ru" ? "Нет доступных уроков для ученика" : "No learner-visible lessons"} />}
                  </div>
                </article>

                <div className="course-preview-grid">
                  <article className="course-preview-block">
                    <strong>{language === "ru" ? "Секции курса" : "Course sections"}</strong>
                    <div className="course-preview-list">
                      {(sections.data ?? []).map((section) => (
                        <div key={section.id} className="course-preview-item">
                          <div>
                            <strong>{section.title}</strong>
                            <span>#{section.sort_order}</span>
                          </div>
                          <span>{section.is_visible ? (language === "ru" ? "Видна" : "Visible") : (language === "ru" ? "Скрыта" : "Hidden")}</span>
                        </div>
                      ))}
                      {!sections.loading && !(sections.data ?? []).length && <EmptyState title={language === "ru" ? "Секций пока нет" : "No sections yet"} />}
                    </div>
                  </article>
                </div>

                <div className="studio-outline-list">
                  {(lessons.data ?? []).map((lesson, index) => (
                    <article className="studio-outline-item" key={lesson.id}>
                      <div className="studio-outline-index">{index + 1}</div>
                      <div className="studio-outline-body">
                        <strong>{lesson.title}</strong>
                        <span>{lesson.summary || t.lessonSummaryEmpty}</span>
                      </div>
                      <div className="studio-outline-meta">
                        <span>{lesson.content_pages?.length ?? 1} {t.pages.toLowerCase()}</span>
                        <span>{lesson.duration_minutes} {language === "ru" ? "мин" : "min"}</span>
                      </div>
                    </article>
                  ))}
                  {!lessons.loading && !(lessons.data ?? []).length && <EmptyState title={t.noLessonsYet} />}
                </div>
              </div>
            ) : (
              <EmptyState title={t.pickCoursePrompt} />
            )}
          </section>
        </div>
      </section>
      <MediaPickerDialog
        open={coverPickerOpen}
        kind="image"
        assets={mediaAssets.data ?? []}
        onClose={() => setCoverPickerOpen(false)}
        onSelect={applySelectedCourseCover}
        onUpload={uploadCourseCover}
      />
    </section>
  );
}

export function LessonsPage({ session }: { session: SessionState }) {
  const { language, t } = useUi();
  const [searchParams, setSearchParams] = useSearchParams();
  const courses = useRemote<CourseInfo[]>("/courses", session);
  const [mediaRefreshKey, setMediaRefreshKey] = useState(0);
  const mediaAssets = useRemote<MediaAssetInfo[]>("/media/library", session, mediaRefreshKey);
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const lessons = useRemote<LessonInfo[]>(
    selectedCourseId ? `/lessons?course_id=${selectedCourseId}` : null,
    session,
    refreshKey + (selectedCourseId ?? 0)
  );
  const sections = useRemote<SectionInfo[]>(
    selectedCourseId ? `/courses/${selectedCourseId}/sections` : null,
    session,
    refreshKey + (selectedCourseId ?? 0)
  );
  const recommendations = useRemote<EditorRecommendationInfo[]>(
    selectedCourseId ? `/recommendations/editor?course_id=${selectedCourseId}` : null,
    session,
    refreshKey + (selectedCourseId ?? 0)
  );
  const assignments = useRemote<AssignmentInfo[]>(
    selectedCourseId ? `/assignments?course_id=${selectedCourseId}` : null,
    session,
    refreshKey + (selectedCourseId ?? 0)
  );
  const [editingLessonId, setEditingLessonId] = useState<number | null>(null);
  const lessonIdToKeepAfterRefresh = useRef<number | null>(null);
  const [activePageId, setActivePageId] = useState<string | null>(null);
  const [mediaTarget, setMediaTarget] = useState<MediaPickerTarget | null>(null);
  const [pendingHtmlSnippet, setPendingHtmlSnippet] = useState<PendingHtmlSnippet | null>(null);
  const htmlSelectionByPageRef = useRef<Record<string, TextSelection>>({});
  const [saveState, setSaveState] = useState<"saved" | "dirty" | "saving" | "error">("saved");
  const [lastSavedSnapshot, setLastSavedSnapshot] = useState("");
  const [sectionDraftTitle, setSectionDraftTitle] = useState("");
  const [renamingSectionId, setRenamingSectionId] = useState<number | null>(null);
  const [renamingSectionTitle, setRenamingSectionTitle] = useState("");
  const [renamingLessonId, setRenamingLessonId] = useState<number | null>(null);
  const [renamingLessonTitle, setRenamingLessonTitle] = useState("");
  const [pendingDeleteLesson, setPendingDeleteLesson] = useState<LessonInfo | null>(null);
  const pendingDeleteTimerRef = useRef<number | null>(null);
  const [lastOrderSnapshot, setLastOrderSnapshot] = useState<{
    lessonIds: number[];
    sectionIds: number[];
  } | null>(null);
  const [recommendationDraft, setRecommendationDraft] = useState({ title: "", text: "", lessonId: "" });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [practiceDraft, setPracticeDraft] = useState({
    enabled: false,
  });
  const [form, setForm] = useState({
    title: "",
    summary: "",
    content: "",
    durationMinutes: 8,
    imageUrl: "",
    videoUrl: "",
    sectionId: null as number | null,
    isVisible: true,
    isPublished: true,
    sortOrder: 1,
    pages: [createLessonPageDraft(1, language)]
  });
  const requestedCourseId = parseCourseIdParam(searchParams.get("courseId"));

  const contentPagesPayload = useMemo(() => buildLessonPagesPayload(form.pages), [form.pages]);
  const lessonSnapshot = useMemo(
    () =>
      JSON.stringify({
        title: form.title,
        summary: form.summary,
        content: form.content,
        durationMinutes: form.durationMinutes,
        imageUrl: form.imageUrl,
        videoUrl: form.videoUrl,
        sectionId: form.sectionId,
        isVisible: form.isVisible,
        isPublished: form.isPublished,
        sortOrder: form.sortOrder,
        pages: form.pages,
      }),
    [form]
  );

  function updateCourseSearchParam(courseId: number | null) {
    const currentValue = searchParams.get("courseId");
    const nextValue = courseId === null ? null : String(courseId);
    if (currentValue === nextValue) {
      return;
    }
    const nextParams = new URLSearchParams(searchParams);
    if (nextValue === null) {
      nextParams.delete("courseId");
    } else {
      nextParams.set("courseId", nextValue);
    }
    setSearchParams(nextParams, { replace: true });
  }

  function selectCourseId(courseId: number) {
    lessonIdToKeepAfterRefresh.current = null;
    if (pendingDeleteTimerRef.current !== null) {
      window.clearTimeout(pendingDeleteTimerRef.current);
      pendingDeleteTimerRef.current = null;
    }
    setPendingDeleteLesson(null);
    setLastOrderSnapshot(null);
    setSelectedCourseId(courseId);
    updateCourseSearchParam(courseId);
  }

  useEffect(() => {
    if (!courses.data?.length) {
      return;
    }
    const requestedCourse = requestedCourseId ? courses.data.find((course) => course.id === requestedCourseId) ?? null : null;
    if (requestedCourse) {
      if (selectedCourseId !== requestedCourse.id) {
        setSelectedCourseId(requestedCourse.id);
      }
      return;
    }
    if (!selectedCourseId) {
      const firstCourseId = courses.data[0].id;
      setSelectedCourseId(firstCourseId);
      updateCourseSearchParam(firstCourseId);
    }
  }, [courses.data, requestedCourseId, selectedCourseId]);

  useEffect(() => {
    if (!form.pages.length) {
      setActivePageId(null);
      return;
    }
    if (!activePageId || !form.pages.some((page) => page.id === activePageId)) {
      setActivePageId(form.pages[0].id);
    }
  }, [activePageId, form.pages]);

  useEffect(() => {
    if (!lastSavedSnapshot || saveState === "saving") {
      return;
    }
    setSaveState(lessonSnapshot === lastSavedSnapshot ? "saved" : "dirty");
  }, [lastSavedSnapshot, lessonSnapshot, saveState]);

  useEffect(() => {
    return () => {
      if (pendingDeleteTimerRef.current !== null) {
        window.clearTimeout(pendingDeleteTimerRef.current);
      }
    };
  }, []);

  function loadLessonIntoForm(lesson: LessonInfo, nextStatus = "", preferredActivePageId: string | null = null, preferredActivePageIndex: number | null = null) {
    const draftPages = buildDraftPagesFromLesson(lesson);
    const nextActivePage =
      draftPages.find((page) => page.id === preferredActivePageId) ??
      (preferredActivePageIndex !== null ? draftPages[preferredActivePageIndex] : undefined) ??
      draftPages[0] ??
      null;
    const nextDraft = {
      title: lesson.title,
      summary: lesson.summary,
      content: lesson.content,
      durationMinutes: lesson.duration_minutes,
      imageUrl: lesson.image_url ?? "",
      videoUrl: lesson.video_url ?? "",
      sectionId: lesson.section_id ?? null,
      isVisible: lesson.is_visible ?? true,
      isPublished: lesson.is_published ?? true,
      sortOrder: lesson.sort_order,
      pages: draftPages
    };
    setEditingLessonId(lesson.id);
    setError("");
    setStatus(nextStatus);
    setForm(nextDraft);
    setActivePageId(nextActivePage?.id ?? null);
    setLastSavedSnapshot(JSON.stringify(nextDraft));
    setSaveState("saved");
    setRenamingLessonId(null);
  }

  function startNewLesson() {
    lessonIdToKeepAfterRefresh.current = null;
    setEditingLessonId(null);
    setError("");
    setStatus(selectedCourseId ? t.draftingLesson : "");
    const nextPage = createLessonPageDraft(1, language);
    const nextDraft = {
      title: "",
      summary: "",
      content: "",
      durationMinutes: 8,
      imageUrl: "",
      videoUrl: "",
      sectionId: null as number | null,
      isVisible: true,
      isPublished: true,
      sortOrder: (lessons.data?.length ?? 0) + 1,
      pages: [nextPage]
    };
    setForm(nextDraft);
    setActivePageId(nextPage.id);
    setLastSavedSnapshot(JSON.stringify(nextDraft));
    setSaveState("saved");
    setRenamingLessonId(null);
    setPracticeDraft({ enabled: false });
  }

  useEffect(() => {
    if (!editingLessonId) {
      setPracticeDraft({ enabled: false });
      return;
    }
    const linkedAssignment = (assignments.data ?? []).find((item) => item.lesson_id === editingLessonId) ?? null;
    if (!linkedAssignment) {
      setPracticeDraft({ enabled: false });
      return;
    }
    setPracticeDraft({
      enabled: linkedAssignment.is_active,
    });
  }, [assignments.data, editingLessonId]);

  function discardDraftChanges() {
    const prompt = language === "ru" ? "Отменить несохранённые изменения?" : "Discard unsaved changes?";
    if (typeof window !== "undefined" && !window.confirm(prompt)) {
      return;
    }
    if (editingLessonId) {
      const source = (lessons.data ?? []).find((lesson) => lesson.id === editingLessonId);
      if (source) {
        loadLessonIntoForm(source, language === "ru" ? "Изменения отменены" : "Changes reverted");
        return;
      }
    }
    startNewLesson();
  }

  useEffect(() => {
    if (!selectedCourseId || lessons.loading) {
      return;
    }
    if (!(lessons.data ?? []).length) {
      if (editingLessonId !== null) {
        startNewLesson();
      }
      return;
    }
    const currentLesson = (lessons.data ?? []).find((lesson) => lesson.id === editingLessonId);
    const lessonToKeep = lessonIdToKeepAfterRefresh.current;
    if (lessonToKeep !== null) {
      const savedLessonInList = (lessons.data ?? []).find((lesson) => lesson.id === lessonToKeep);
      if (savedLessonInList) {
        lessonIdToKeepAfterRefresh.current = null;
        if (editingLessonId !== savedLessonInList.id) {
          setEditingLessonId(savedLessonInList.id);
        }
        return;
      }
    }
    if (!currentLesson) {
      lessonIdToKeepAfterRefresh.current = null;
      loadLessonIntoForm((lessons.data ?? [])[0]);
    }
  }, [selectedCourseId, lessons.data, lessons.loading]);

  function updatePage(pageId: string, patch: Partial<LessonPageDraft>) {
    setForm((current) => ({
      ...current,
      pages: current.pages.map((page) => (page.id === pageId ? { ...page, ...patch } : page))
    }));
  }

  function addPage() {
    const nextPage = createLessonPageDraft(form.pages.length + 1, language);
    setForm((current) => ({
      ...current,
      pages: [...current.pages, nextPage]
    }));
    setActivePageId(nextPage.id);
  }

  function removePage(pageId: string) {
    setForm((current) => ({
      ...current,
      pages: current.pages.length === 1 ? current.pages : current.pages.filter((page) => page.id !== pageId)
    }));
  }

  function movePage(pageId: string, direction: -1 | 1) {
    setForm((current) => {
      const index = current.pages.findIndex((page) => page.id === pageId);
      const nextIndex = index + direction;
      if (index === -1 || nextIndex < 0 || nextIndex >= current.pages.length) {
        return current;
      }
      const nextPages = [...current.pages];
      const [page] = nextPages.splice(index, 1);
      nextPages.splice(nextIndex, 0, page);
      return { ...current, pages: nextPages };
    });
  }

  function startEditing(lesson: LessonInfo) {
    lessonIdToKeepAfterRefresh.current = null;
    selectCourseId(lesson.course_id);
    loadLessonIntoForm(lesson, language === "ru" ? `Редактирование урока «${lesson.title}»` : `Editing lesson "${lesson.title}"`);
  }

  function openMediaDialog(target: MediaPickerTarget) {
    setMediaTarget(target);
  }

  function rememberHtmlSelection(pageId: string, selection: TextSelection) {
    htmlSelectionByPageRef.current[pageId] = selection;
  }

  function openHtmlMediaDialog(kind: MediaKind, pageId: string, selection?: TextSelection) {
    const htmlSelection = selection ?? htmlSelectionByPageRef.current[pageId];
    openMediaDialog({ scope: "html", kind, pageId, htmlSelection });
  }

  function applySelectedMedia(asset: MediaAssetInfo) {
    if (!mediaTarget) {
      return;
    }
    if (mediaTarget.scope === "html" || mediaTarget.kind === "document") {
      const targetPageId = mediaTarget.pageId ?? activePage?.id;
      if (targetPageId) {
        setActivePageId(targetPageId);
        setPendingHtmlSnippet({
          pageId: targetPageId,
          snippet: buildMediaHtmlSnippet(asset),
          nonce: Date.now(),
          selection: mediaTarget.htmlSelection ?? htmlSelectionByPageRef.current[targetPageId]
        });
      }
      setMediaTarget(null);
      return;
    }
    const field = mediaTarget.kind === "image" ? "imageUrl" : "videoUrl";
    if (mediaTarget.scope === "page" && mediaTarget.pageId) {
      updatePage(mediaTarget.pageId, { [field]: asset.path } as Partial<LessonPageDraft>);
    } else {
      setForm((current) => ({ ...current, [field]: asset.path }));
    }
    setMediaTarget(null);
  }

  async function uploadMediaFile(file: File, kind: MediaKind, onProgress?: (progress: number) => void) {
    const payload = new FormData();
    payload.set("target_kind", kind);
    payload.set("file", file);
    const uploaded = (await apiUpload("/media/upload", session, payload, onProgress)) as MediaAssetInfo;
    setMediaRefreshKey((value) => value + 1);
    return uploaded;
  }

  function rememberOrderSnapshot() {
    setLastOrderSnapshot({
      lessonIds: (lessons.data ?? []).map((lesson) => lesson.id),
      sectionIds: (sections.data ?? []).map((section) => section.id),
    });
  }

  async function undoLastReorder() {
    if (!selectedCourseId || !lastOrderSnapshot) {
      return;
    }
    setError("");
    try {
      await apiPost(`/courses/${selectedCourseId}/lessons/reorder`, session, { lesson_ids: lastOrderSnapshot.lessonIds });
      await apiPost(`/courses/${selectedCourseId}/sections/reorder`, session, { section_ids: lastOrderSnapshot.sectionIds });
      setRefreshKey((value) => value + 1);
      setLastOrderSnapshot(null);
      setStatus(language === "ru" ? "Порядок восстановлен" : "Order restored");
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось отменить изменение порядка" : "Failed to undo reorder");
    }
  }

  async function createSection(event: FormEvent) {
    event.preventDefault();
    if (!selectedCourseId || !sectionDraftTitle.trim()) {
      return;
    }
    setError("");
    try {
      await apiPost(`/courses/${selectedCourseId}/sections`, session, {
        title: sectionDraftTitle.trim(),
        sort_order: (sections.data?.length ?? 0) + 1,
        is_visible: true,
      });
      setSectionDraftTitle("");
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Секция добавлена" : "Section created");
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось добавить секцию" : "Failed to create section");
    }
  }

  async function saveSectionTitle(section: SectionInfo) {
    const nextTitle = renamingSectionTitle.trim();
    if (!selectedCourseId || !nextTitle) {
      return;
    }
    setError("");
    try {
      await apiPatch(`/courses/${selectedCourseId}/sections/${section.id}`, session, {
        title: nextTitle,
        sort_order: section.sort_order,
        is_visible: section.is_visible,
      });
      setRenamingSectionId(null);
      setRenamingSectionTitle("");
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Название секции обновлено" : "Section renamed");
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось переименовать секцию" : "Failed to rename section");
    }
  }

  async function moveSection(sectionId: number, direction: -1 | 1) {
    if (!selectedCourseId || !(sections.data ?? []).length) {
      return;
    }
    const current = [...(sections.data ?? [])];
    const index = current.findIndex((item) => item.id === sectionId);
    const targetIndex = index + direction;
    if (index < 0 || targetIndex < 0 || targetIndex >= current.length) {
      return;
    }
    rememberOrderSnapshot();
    const next = [...current];
    const [moved] = next.splice(index, 1);
    next.splice(targetIndex, 0, moved);
    sections.setData(next.map((item, orderIndex) => ({ ...item, sort_order: orderIndex + 1 })));
    try {
      await apiPost(`/courses/${selectedCourseId}/sections/reorder`, session, { section_ids: next.map((item) => item.id) });
      setStatus(language === "ru" ? "Порядок секций обновлён" : "Section order updated");
    } catch (err) {
      sections.setData(current);
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось изменить порядок секций" : "Failed to reorder sections");
    }
  }

  async function toggleSectionVisibility(section: SectionInfo) {
    if (!selectedCourseId) {
      return;
    }
    setError("");
    try {
      await apiPatch(`/courses/${selectedCourseId}/sections/${section.id}`, session, {
        title: section.title,
        sort_order: section.sort_order,
        is_visible: !section.is_visible,
      });
      setRefreshKey((value) => value + 1);
      setStatus(
        !section.is_visible
          ? language === "ru"
            ? "Секция отображается"
            : "Section visible"
          : language === "ru"
            ? "Секция скрыта"
            : "Section hidden"
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось изменить видимость секции" : "Failed to update section visibility");
    }
  }

  async function removeSection(section: SectionInfo) {
    if (!selectedCourseId) {
      return;
    }
    if (typeof window !== "undefined" && !window.confirm(language === "ru" ? `Удалить секцию «${section.title}»?` : `Delete section "${section.title}"?`)) {
      return;
    }
    setError("");
    try {
      await apiDelete(`/courses/${selectedCourseId}/sections/${section.id}`, session);
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Секция удалена" : "Section deleted");
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось удалить секцию" : "Failed to delete section");
    }
  }

  async function moveLesson(lessonId: number, direction: -1 | 1) {
    if (!selectedCourseId || !(lessons.data ?? []).length) {
      return;
    }
    const current = [...(lessons.data ?? [])];
    const index = current.findIndex((item) => item.id === lessonId);
    const targetIndex = index + direction;
    if (index < 0 || targetIndex < 0 || targetIndex >= current.length) {
      return;
    }
    rememberOrderSnapshot();
    const next = [...current];
    const [moved] = next.splice(index, 1);
    next.splice(targetIndex, 0, moved);
    const withSort = next.map((item, orderIndex) => ({ ...item, sort_order: orderIndex + 1 }));
    lessons.setData(withSort);
    if (editingLessonId === lessonId) {
      setForm((currentForm) => ({ ...currentForm, sortOrder: targetIndex + 1 }));
    }
    try {
      await apiPost(`/courses/${selectedCourseId}/lessons/reorder`, session, { lesson_ids: withSort.map((item) => item.id) });
      setStatus(language === "ru" ? "Порядок уроков обновлён" : "Lesson order updated");
    } catch (err) {
      lessons.setData(current);
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось изменить порядок уроков" : "Failed to reorder lessons");
    }
  }

  async function setLessonSection(lesson: LessonInfo, sectionId: number | null) {
    setError("");
    try {
      await apiPatch(`/lessons/${lesson.id}`, session, buildLessonUpdatePayloadFromLesson(lesson, { section_id: sectionId }));
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Урок перемещён" : "Lesson moved");
      if (editingLessonId === lesson.id) {
        setForm((current) => ({ ...current, sectionId }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось переместить урок" : "Failed to move lesson");
    }
  }

  async function duplicateLesson(lessonId: number) {
    setError("");
    try {
      await apiPost(`/lessons/${lessonId}/duplicate`, session, {});
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Урок дублирован" : "Lesson duplicated");
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось дублировать урок" : "Failed to duplicate lesson");
    }
  }

  async function toggleLessonVisibility(lesson: LessonInfo) {
    setError("");
    try {
      await apiPatch(`/lessons/${lesson.id}/visibility`, session, { value: !(lesson.is_visible ?? true) });
      setRefreshKey((value) => value + 1);
      setStatus(!(lesson.is_visible ?? true) ? (language === "ru" ? "Урок показан" : "Lesson visible") : language === "ru" ? "Урок скрыт" : "Lesson hidden");
      if (editingLessonId === lesson.id) {
        setForm((current) => ({ ...current, isVisible: !(lesson.is_visible ?? true) }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось изменить видимость урока" : "Failed to update lesson visibility");
    }
  }

  async function toggleLessonPublication(lesson: LessonInfo) {
    setError("");
    try {
      await apiPatch(`/lessons/${lesson.id}/publication`, session, { value: !(lesson.is_published ?? true) });
      setRefreshKey((value) => value + 1);
      setStatus(!(lesson.is_published ?? true) ? (language === "ru" ? "Урок опубликован" : "Lesson published") : language === "ru" ? "Урок снят с публикации" : "Lesson unpublished");
      if (editingLessonId === lesson.id) {
        setForm((current) => ({ ...current, isPublished: !(lesson.is_published ?? true) }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось изменить публикацию урока" : "Failed to update lesson publication");
    }
  }

  async function saveLessonTitle(lesson: LessonInfo) {
    const nextTitle = renamingLessonTitle.trim();
    if (!nextTitle) {
      return;
    }
    setError("");
    try {
      await apiPatch(`/lessons/${lesson.id}`, session, buildLessonUpdatePayloadFromLesson(lesson, { title: nextTitle }));
      setRenamingLessonId(null);
      setRenamingLessonTitle("");
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Название урока обновлено" : "Lesson title updated");
      if (editingLessonId === lesson.id) {
        setForm((current) => ({ ...current, title: nextTitle }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось переименовать урок" : "Failed to rename lesson");
    }
  }

  async function finalizeLessonDeletion(lesson: LessonInfo) {
    try {
      await apiDelete(`/lessons/${lesson.id}`, session);
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Урок удалён" : "Lesson deleted");
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось удалить урок" : "Failed to delete lesson");
      lessons.setData((current) => ([...(current ?? []), lesson].sort((a, b) => (a.sort_order - b.sort_order) || (a.id - b.id))));
    } finally {
      setPendingDeleteLesson(null);
      pendingDeleteTimerRef.current = null;
    }
  }

  function requestDeleteLesson(lesson: LessonInfo) {
    if (pendingDeleteTimerRef.current !== null) {
      window.clearTimeout(pendingDeleteTimerRef.current);
      pendingDeleteTimerRef.current = null;
    }
    const nextList = (lessons.data ?? []).filter((item) => item.id !== lesson.id);
    lessons.setData(nextList);
    setPendingDeleteLesson(lesson);
    if (editingLessonId === lesson.id) {
      if (nextList.length) {
        loadLessonIntoForm(nextList[0], language === "ru" ? "Урок удалён. Можно отменить действие." : "Lesson deleted. You can undo the action.");
      } else {
        startNewLesson();
      }
    } else {
      setStatus(language === "ru" ? "Урок удалён. Можно отменить действие." : "Lesson deleted. You can undo the action.");
    }
    pendingDeleteTimerRef.current = window.setTimeout(() => {
      void finalizeLessonDeletion(lesson);
    }, 7000);
  }

  function undoDeleteLesson() {
    if (!pendingDeleteLesson) {
      return;
    }
    if (pendingDeleteTimerRef.current !== null) {
      window.clearTimeout(pendingDeleteTimerRef.current);
      pendingDeleteTimerRef.current = null;
    }
    lessons.setData((current) => ([...(current ?? []), pendingDeleteLesson].sort((a, b) => (a.sort_order - b.sort_order) || (a.id - b.id))));
    setStatus(language === "ru" ? "Удаление отменено" : "Delete cancelled");
    setPendingDeleteLesson(null);
  }

  async function createRecommendation() {
    if (!selectedCourseId || !recommendationDraft.title.trim() || !recommendationDraft.text.trim()) {
      return;
    }
    setError("");
    try {
      await apiPost("/recommendations/editor", session, {
        title: recommendationDraft.title.trim(),
        text: recommendationDraft.text.trim(),
        course_id: selectedCourseId,
        lesson_id: recommendationDraft.lessonId ? Number(recommendationDraft.lessonId) : null,
        sort_order: (recommendations.data?.length ?? 0) + 1,
        is_active: true,
      });
      setRecommendationDraft({ title: "", text: "", lessonId: "" });
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Рекомендация добавлена" : "Recommendation created");
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось добавить рекомендацию" : "Failed to create recommendation");
    }
  }

  async function removeRecommendation(recommendationId: number) {
    setError("");
    try {
      await apiDelete(`/recommendations/editor/${recommendationId}`, session);
      setRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Рекомендация удалена" : "Recommendation deleted");
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось удалить рекомендацию" : "Failed to delete recommendation");
    }
  }

  const activePage = form.pages.find((page) => page.id === activePageId) ?? form.pages[0];
  const selectedCourse = (courses.data ?? []).find((course) => course.id === selectedCourseId) ?? null;
  const sectionGroups = useMemo(
    () =>
      (sections.data ?? []).map((section) => ({
        section,
        lessons: (lessons.data ?? []).filter((lesson) => (lesson.section_id ?? null) === section.id),
      })),
    [lessons.data, sections.data]
  );
  const unsectionedLessons = useMemo(
    () => (lessons.data ?? []).filter((lesson) => lesson.section_id == null),
    [lessons.data]
  );
  const saveStateLabel =
    saveState === "saved"
      ? language === "ru"
        ? "Сохранено"
        : "Saved"
      : saveState === "saving"
        ? language === "ru"
          ? "Сохранение..."
          : "Saving..."
        : saveState === "error"
          ? language === "ru"
            ? "Ошибка сохранения"
            : "Save error"
          : language === "ru"
            ? "Есть несохранённые изменения"
            : "Unsaved changes";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedCourseId) return;
    setError("");
    setSaveState("saving");
    const activePageIdBeforeSave = activePageId;
    const activePageIndexBeforeSave = form.pages.findIndex((page) => page.id === activePageIdBeforeSave);
    const payload = {
      course_id: selectedCourseId,
      section_id: form.sectionId,
      title: form.title,
      summary: form.summary,
      content: form.content.trim() || buildLegacyLessonContent(form.summary, form.pages),
      content_pages: contentPagesPayload,
      duration_minutes: form.durationMinutes,
      image_url: form.imageUrl || null,
      video_url: form.videoUrl || null,
      is_visible: form.isVisible,
      is_published: form.isPublished,
      sort_order: form.sortOrder
    };
    try {
      let practiceSyncWarning = "";
      const savedLesson = (editingLessonId
        ? await apiPatch(`/lessons/${editingLessonId}`, session, payload)
        : await apiPost("/lessons", session, payload)) as LessonInfo;
      try {
        const linkedAssignment = (assignments.data ?? []).find((item) => item.lesson_id === savedLesson.id) ?? null;
        const autoPracticeTitle = form.title.trim() || savedLesson.title;
        const autoPracticeDescription = (form.summary || "").trim();
        if (practiceDraft.enabled && autoPracticeTitle) {
          if (linkedAssignment) {
            try {
              await apiPatch(`/assignments/${linkedAssignment.id}`, session, {
                title: autoPracticeTitle,
                description: autoPracticeDescription,
                is_active: true,
                due_at: linkedAssignment.due_at ?? null,
              });
            } catch {
              await apiPost("/assignments", session, {
                course_id: selectedCourseId,
                lesson_id: savedLesson.id,
                title: autoPracticeTitle,
                description: autoPracticeDescription,
                is_active: true,
              });
            }
          } else {
            await apiPost("/assignments", session, {
              course_id: selectedCourseId,
              lesson_id: savedLesson.id,
              title: autoPracticeTitle,
              description: autoPracticeDescription,
              is_active: true,
            });
          }
        } else if (linkedAssignment && linkedAssignment.is_active) {
          try {
            await apiPatch(`/assignments/${linkedAssignment.id}`, session, {
              title: linkedAssignment.title,
              description: linkedAssignment.description,
              is_active: false,
              due_at: linkedAssignment.due_at ?? null,
            });
          } catch {
            // Assignment might already be deleted; no action required when disabling practice.
          }
        }
      } catch {
        practiceSyncWarning = language === "ru"
          ? "Урок сохранён, но практику не удалось синхронизировать (на сервере недоступен endpoint assignments)."
          : "Lesson saved, but practice sync failed (assignments endpoint is unavailable on server).";
      }
      lessonIdToKeepAfterRefresh.current = savedLesson.id;
      loadLessonIntoForm(
        savedLesson,
        practiceSyncWarning || (editingLessonId ? t.lessonUpdated : t.lessonCreated),
        activePageIdBeforeSave,
        activePageIndexBeforeSave >= 0 ? activePageIndexBeforeSave : null
      );
      setLastSavedSnapshot(
        JSON.stringify({
          title: savedLesson.title,
          summary: savedLesson.summary,
          content: savedLesson.content,
          durationMinutes: savedLesson.duration_minutes,
          imageUrl: savedLesson.image_url ?? "",
          videoUrl: savedLesson.video_url ?? "",
          sectionId: savedLesson.section_id ?? null,
          isVisible: savedLesson.is_visible ?? true,
          isPublished: savedLesson.is_published ?? true,
          sortOrder: savedLesson.sort_order,
          pages: buildDraftPagesFromLesson(savedLesson),
        })
      );
      setSaveState("saved");
      setRefreshKey((value) => value + 1);
    } catch (err) {
      setSaveState("error");
      setError(err instanceof Error ? err.message : t.failedSaveLesson);
    }
  }

  return (
    <section className="page-stack">
      <PageHeader
        title={t.lessons}
        subtitle={
          language === "ru"
            ? "Рабочее место конструктора уроков в духе Moodle и Canvas: выберите курс, откройте один урок и редактируйте по одной странице."
            : "Course-builder workspace inspired by Moodle and Canvas: choose a course, pick one lesson, then edit one page at a time."
        }
      />
      {status && <Notice text={status} />}
      {error && <Notice text={error} tone="error" />}
      <section className="lessons-builder">
        <aside className="card studio-sidebar lessons-sidebar">
          <div className="studio-sidebar-head">
            <div>
              <strong className="studio-eyebrow">{t.curriculum}</strong>
              <h3>{t.courseAndLessons}</h3>
              <p className="sidebar-text">{t.pickCourseFirst}</p>
            </div>
          </div>
          <label className="studio-select lessons-course-select">
            {t.courseLabel}
            <select value={selectedCourseId ?? ""} onChange={(e) => selectCourseId(Number(e.target.value))}>
              {(courses.data ?? []).map((course) => (
                <option key={course.id} value={course.id}>
                  {course.title}
                </option>
              ))}
            </select>
          </label>
          {selectedCourse && (
            <div className="studio-course-summary lessons-course-summary">
              <strong>{selectedCourse.title}</strong>
              <span>{selectedCourse.description || t.noCourseDescription}</span>
            </div>
          )}
          <div className="studio-sidebar-toolbar lessons-sidebar-toolbar">
            <button type="button" className="page-action secondary" onClick={startNewLesson} disabled={!selectedCourseId}>
              {t.newLessonAction}
            </button>
            <Link className="page-action secondary" to={selectedCourse ? `/courses?courseId=${selectedCourse.id}` : "/courses"}>
              {t.editCourse}
            </Link>
          </div>
          <form className="lesson-section-create" onSubmit={createSection}>
            <label>
              {language === "ru" ? "Новая секция" : "New section"}
              <input
                value={sectionDraftTitle}
                onChange={(e) => setSectionDraftTitle(e.target.value)}
                placeholder={language === "ru" ? "Название секции" : "Section title"}
              />
            </label>
            <button type="submit" className="page-action secondary" disabled={!selectedCourseId || !sectionDraftTitle.trim()}>
              {language === "ru" ? "Добавить секцию" : "Add section"}
            </button>
          </form>
          <div className="lessons-sidebar-list" data-testid="lessons-sidebar-list">
            {sectionGroups.map(({ section, lessons: sectionLessons }, sectionIndex) => (
              <div key={section.id} className="lesson-section-group">
                <div className="lesson-section-head">
                  {renamingSectionId === section.id ? (
                    <div className="lesson-section-rename">
                      <input
                        value={renamingSectionTitle}
                        onChange={(e) => setRenamingSectionTitle(e.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            void saveSectionTitle(section);
                          }
                          if (event.key === "Escape") {
                            setRenamingSectionId(null);
                            setRenamingSectionTitle("");
                          }
                        }}
                      />
                      <button type="button" className="page-action secondary" onClick={() => void saveSectionTitle(section)}>
                        {t.save}
                      </button>
                    </div>
                  ) : (
                    <strong>{section.title}</strong>
                  )}
                  <div className="lesson-section-actions">
                    <button type="button" className="page-action secondary" onClick={() => { setRenamingSectionId(section.id); setRenamingSectionTitle(section.title); }}>
                      {language === "ru" ? "Переименовать" : "Rename"}
                    </button>
                    <button type="button" className="page-action secondary" onClick={() => void moveSection(section.id, -1)} disabled={sectionIndex === 0}>
                      {t.up}
                    </button>
                    <button type="button" className="page-action secondary" onClick={() => void moveSection(section.id, 1)} disabled={sectionIndex === sectionGroups.length - 1}>
                      {t.down}
                    </button>
                    <button type="button" className="page-action secondary" onClick={() => void toggleSectionVisibility(section)}>
                      {section.is_visible ? (language === "ru" ? "Скрыть" : "Hide") : (language === "ru" ? "Показать" : "Show")}
                    </button>
                    <button type="button" className="page-action secondary" onClick={() => void removeSection(section)}>
                      {t.remove}
                    </button>
                  </div>
                </div>
                <div className="lesson-section-lessons">
                  {sectionLessons.map((lesson) => (
                    <article
                      key={lesson.id}
                      className={`studio-list-item lessons-lesson-card ${lesson.id === editingLessonId ? "active" : ""}`}
                    >
                      <button type="button" className="lesson-card-open" onClick={() => startEditing(lesson)}>
                        <div className="studio-list-main lessons-lesson-main">
                          {renamingLessonId === lesson.id ? (
                            <input
                              value={renamingLessonTitle}
                              onChange={(e) => setRenamingLessonTitle(e.target.value)}
                              onClick={(e) => e.stopPropagation()}
                              onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                  event.preventDefault();
                                  void saveLessonTitle(lesson);
                                }
                                if (event.key === "Escape") {
                                  setRenamingLessonId(null);
                                  setRenamingLessonTitle("");
                                }
                              }}
                            />
                          ) : (
                            <strong>{lesson.title}</strong>
                          )}
                          <span>{lesson.summary || t.lessonSummaryEmpty}</span>
                        </div>
                        <div className="studio-list-meta lessons-lesson-meta">
                          <span>{lesson.content_pages?.length ?? 1} {t.pages.toLowerCase()}</span>
                          <span>{lesson.duration_minutes} {language === "ru" ? "мин" : "min"}</span>
                        </div>
                      </button>
                      <div className="lesson-card-actions">
                        <select value={lesson.section_id ?? ""} onChange={(e) => void setLessonSection(lesson, e.target.value ? Number(e.target.value) : null)}>
                          <option value="">{language === "ru" ? "Без секции" : "No section"}</option>
                          {(sections.data ?? []).map((sectionOption) => (
                            <option key={sectionOption.id} value={sectionOption.id}>
                              {sectionOption.title}
                            </option>
                          ))}
                        </select>
                        <button type="button" className="page-action secondary" onClick={() => { setRenamingLessonId(lesson.id); setRenamingLessonTitle(lesson.title); }}>
                          {language === "ru" ? "Переименовать" : "Rename"}
                        </button>
                        <button type="button" className="page-action secondary" onClick={() => void moveLesson(lesson.id, -1)}>
                          {t.up}
                        </button>
                        <button type="button" className="page-action secondary" onClick={() => void moveLesson(lesson.id, 1)}>
                          {t.down}
                        </button>
                        <button type="button" className="page-action secondary" onClick={() => void duplicateLesson(lesson.id)}>
                          {language === "ru" ? "Дублировать" : "Duplicate"}
                        </button>
                        <button type="button" className="page-action secondary" onClick={() => void toggleLessonVisibility(lesson)}>
                          {(lesson.is_visible ?? true) ? (language === "ru" ? "Скрыть" : "Hide") : (language === "ru" ? "Показать" : "Show")}
                        </button>
                        <button type="button" className="page-action secondary" onClick={() => void toggleLessonPublication(lesson)}>
                          {(lesson.is_published ?? true) ? (language === "ru" ? "Снять" : "Unpublish") : (language === "ru" ? "Опубликовать" : "Publish")}
                        </button>
                        <button type="button" className="page-action secondary" onClick={() => requestDeleteLesson(lesson)}>
                          {t.remove}
                        </button>
                      </div>
                    </article>
                  ))}
                  {!sectionLessons.length && <EmptyState title={language === "ru" ? "В этой секции пока нет уроков" : "No lessons in this section yet"} />}
                </div>
              </div>
            ))}
            {Boolean(unsectionedLessons.length) && (
              <div className="lesson-section-group">
                <div className="lesson-section-head">
                  <strong>{language === "ru" ? "Без секции" : "No section"}</strong>
                </div>
                <div className="lesson-section-lessons">
                  {unsectionedLessons.map((lesson) => (
                    <article
                      key={lesson.id}
                      className={`studio-list-item lessons-lesson-card ${lesson.id === editingLessonId ? "active" : ""}`}
                    >
                      <button type="button" className="lesson-card-open" onClick={() => startEditing(lesson)}>
                        <div className="studio-list-main lessons-lesson-main">
                          <strong>{lesson.title}</strong>
                          <span>{lesson.summary || t.lessonSummaryEmpty}</span>
                        </div>
                        <div className="studio-list-meta lessons-lesson-meta">
                          <span>{lesson.content_pages?.length ?? 1} {t.pages.toLowerCase()}</span>
                          <span>{lesson.duration_minutes} {language === "ru" ? "мин" : "min"}</span>
                        </div>
                      </button>
                      <div className="lesson-card-actions">
                        <select value={lesson.section_id ?? ""} onChange={(e) => void setLessonSection(lesson, e.target.value ? Number(e.target.value) : null)}>
                          <option value="">{language === "ru" ? "Без секции" : "No section"}</option>
                          {(sections.data ?? []).map((sectionOption) => (
                            <option key={sectionOption.id} value={sectionOption.id}>
                              {sectionOption.title}
                            </option>
                          ))}
                        </select>
                        <button type="button" className="page-action secondary" onClick={() => void moveLesson(lesson.id, -1)}>
                          {t.up}
                        </button>
                        <button type="button" className="page-action secondary" onClick={() => void moveLesson(lesson.id, 1)}>
                          {t.down}
                        </button>
                        <button type="button" className="page-action secondary" onClick={() => void duplicateLesson(lesson.id)}>
                          {language === "ru" ? "Дублировать" : "Duplicate"}
                        </button>
                        <button type="button" className="page-action secondary" onClick={() => requestDeleteLesson(lesson)}>
                          {t.remove}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            )}
            {lessons.loading && <EmptyState title={t.loadingLessons} />}
            {lessons.error && <EmptyState title={lessons.error} />}
            {!lessons.loading && !(lessons.data ?? []).length && selectedCourseId && <EmptyState title={t.noLessonsYet} />}
          </div>
        </aside>

        <form className="lessons-editor" onSubmit={submit}>
          <section className="card studio-panel">
            <div className="studio-panel-head">
              <div>
                <strong className="studio-eyebrow">{editingLessonId ? t.lessonSettings : t.newLessonLabel}</strong>
                <h3>{editingLessonId ? (language === "ru" ? "Редактирование выбранного урока" : "Edit selected lesson") : t.createLessonInCourse}</h3>
              </div>
              <div className="studio-actions">
                <span className={`status-pill ${saveState === "error" ? "inactive" : "active"}`}>{saveStateLabel}</span>
                <button type="submit" disabled={!selectedCourseId}>
                  {editingLessonId ? t.saveLesson : t.createLessonAction}
                </button>
                <button type="button" className="page-action secondary" onClick={discardDraftChanges} disabled={!selectedCourseId}>
                  {language === "ru" ? "Отменить несохранённые изменения" : "Discard unsaved changes"}
                </button>
                {lastOrderSnapshot && (
                  <button type="button" className="page-action secondary" onClick={() => void undoLastReorder()}>
                    {language === "ru" ? "Undo reorder" : "Undo reorder"}
                  </button>
                )}
                {pendingDeleteLesson && (
                  <button type="button" className="page-action secondary" onClick={undoDeleteLesson}>
                    {language === "ru" ? "Отменить удаление" : "Undo delete"}
                  </button>
                )}
              </div>
            </div>
            <div className="studio-form-grid lessons-settings-grid">
              <label>
                {t.lessonTitle}
                <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder={t.lessonTitle} required />
              </label>
              <label>
                {t.sortOrder}
                <input
                  type="number"
                  value={form.sortOrder}
                  onChange={(e) => setForm({ ...form, sortOrder: Number(e.target.value) })}
                  placeholder={t.sortOrder}
                  required
                />
              </label>
              <label>
                {t.durationMinutes}
                <input
                  type="number"
                  min={1}
                  value={form.durationMinutes}
                  onChange={(e) => setForm({ ...form, durationMinutes: Number(e.target.value) })}
                  placeholder={t.durationMinutes}
                  required
                />
              </label>
              <label>
                {language === "ru" ? "Секция" : "Section"}
                <select value={form.sectionId ?? ""} onChange={(e) => setForm({ ...form, sectionId: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">{language === "ru" ? "Без секции" : "No section"}</option>
                  {(sections.data ?? []).map((section) => (
                    <option key={section.id} value={section.id}>
                      {section.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {language === "ru" ? "Видимость" : "Visibility"}
                <select value={form.isVisible ? "visible" : "hidden"} onChange={(e) => setForm({ ...form, isVisible: e.target.value === "visible" })}>
                  <option value="visible">{language === "ru" ? "Показан" : "Visible"}</option>
                  <option value="hidden">{language === "ru" ? "Скрыт" : "Hidden"}</option>
                </select>
              </label>
              <label>
                {language === "ru" ? "Публикация" : "Publication"}
                <select value={form.isPublished ? "published" : "draft"} onChange={(e) => setForm({ ...form, isPublished: e.target.value === "published" })}>
                  <option value="published">{language === "ru" ? "Опубликован" : "Published"}</option>
                  <option value="draft">{language === "ru" ? "Черновик" : "Draft"}</option>
                </select>
              </label>
              <label className="studio-form-span">
                {t.lessonSummary}
                <textarea value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} placeholder={t.lessonSummaryPlaceholder} rows={3} required />
              </label>
              <label className="studio-form-span">
                <span>{language === "ru" ? "Практическое задание" : "Practical assignment"}</span>
                <div className="course-access-checkbox">
                  <input
                    id="lesson-practice-enabled"
                    type="checkbox"
                    checked={practiceDraft.enabled}
                    onChange={(e) => setPracticeDraft((current) => ({ ...current, enabled: e.target.checked }))}
                  />
                  <label htmlFor="lesson-practice-enabled">
                    {language === "ru"
                      ? "Эта страница/урок содержит практику. Ученики смогут отправлять решение в разделе заданий."
                      : "This lesson contains practice. Learners can submit solutions in assignments."}
                  </label>
                </div>
              </label>
              {practiceDraft.enabled && (
                <>
                  <div className="studio-form-span">
                    <span className="form-helper">
                      {language === "ru"
                        ? "Название и описание практики берутся автоматически из названия урока и краткого описания."
                        : "Practice title and instructions are generated automatically from the lesson title and summary."}
                    </span>
                  </div>
                  <div className="studio-form-span">
                    <Link className="page-action secondary" to="/homework-reviews">
                      {language === "ru" ? "Проверка отправленных работ" : "Review submitted work"}
                    </Link>
                  </div>
                </>
              )}
            </div>
          </section>

          <section className="lesson-builder-layout lessons-pages-shell">
            <aside className="card lesson-builder-sidebar lessons-pages-sidebar">
              <div className="studio-panel-head">
                <div>
                  <strong className="studio-eyebrow">{t.pages}</strong>
                  <h3>{t.lessonOutline}</h3>
                </div>
                <button type="button" className="page-action secondary" onClick={addPage}>
                  {t.addPage}
                </button>
              </div>
              <p className="sidebar-text">{t.outlineHint}</p>
              <div className="lessons-page-list">
                {form.pages.map((page, index) => (
                  <article key={page.id} className={`page-list-item ${page.id === activePage?.id ? "active" : ""}`}>
                    <button type="button" className="page-list-select" onClick={() => setActivePageId(page.id)}>
                      <strong>
                        {index + 1}. {page.pageTitle || t.untitledPage}
                      </strong>
                      <span>{page.chapterTitle || t.noChapterLabel}</span>
                    </button>
                    <div className="page-list-actions">
                      <button type="button" className="page-action secondary" onClick={() => movePage(page.id, -1)} disabled={index === 0}>
                        {t.up}
                      </button>
                      <button type="button" className="page-action secondary" onClick={() => movePage(page.id, 1)} disabled={index === form.pages.length - 1}>
                        {t.down}
                      </button>
                      <button type="button" className="page-action secondary" onClick={() => removePage(page.id)} disabled={form.pages.length === 1}>
                        {t.remove}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </aside>

            <div className="lessons-page-main">
              {activePage ? (
                <section className="card studio-panel">
                  <div className="studio-panel-head">
                    <div>
                      <strong className="studio-eyebrow">{t.activePage}</strong>
                      <h3>{activePage.pageTitle || t.untitledPage}</h3>
                    </div>
                    <span className="studio-list-meta">
                      {form.pages.findIndex((page) => page.id === activePage.id) + 1} / {form.pages.length}
                    </span>
                  </div>
                  <div className="page-editor-grid">
                    <label>
                      {t.chapterTitle}
                      <input value={activePage.chapterTitle} onChange={(e) => updatePage(activePage.id, { chapterTitle: e.target.value })} placeholder={t.chapterTitle} />
                    </label>
                    <label>
                      {t.pageTitle}
                      <input value={activePage.pageTitle} onChange={(e) => updatePage(activePage.id, { pageTitle: e.target.value })} placeholder={t.pageTitle} />
                    </label>
                  </div>
                  <div className="media-attachment-grid">
                    <MediaAttachmentCard
                      scope="page"
                      kind="image"
                      url={activePage.imageUrl}
                      onAttach={() => openMediaDialog({ scope: "page", kind: "image", pageId: activePage.id })}
                      onRemove={() => updatePage(activePage.id, { imageUrl: "" })}
                    />
                    <MediaAttachmentCard
                      scope="page"
                      kind="video"
                      url={activePage.videoUrl}
                      onAttach={() => openMediaDialog({ scope: "page", kind: "video", pageId: activePage.id })}
                      onRemove={() => updatePage(activePage.id, { videoUrl: "" })}
                    />
                  </div>
                  <div className="document-insert-bar">
                    <button type="button" className="page-action secondary" onClick={() => openHtmlMediaDialog("image", activePage.id)}>
                      {getHtmlMediaInsertLabel("image", language)}
                    </button>
                    <button type="button" className="page-action secondary" onClick={() => openHtmlMediaDialog("video", activePage.id)}>
                      {getHtmlMediaInsertLabel("video", language)}
                    </button>
                    <button type="button" className="page-action secondary" onClick={() => openHtmlMediaDialog("document", activePage.id)}>
                      {getHtmlMediaInsertLabel("document", language)}
                    </button>
                    <span className="sidebar-text">
                      {language === "ru"
                        ? "Загрузите файл или выберите его из медиатеки, и он автоматически вставится в текст урока."
                        : "Upload a file or pick one from the media library, and it will be inserted into the lesson text."}
                    </span>
                  </div>
                  <LessonPagePreviewCard page={activePage} />
                  <details className="advanced-panel">
                    <summary>{t.advancedSettings}</summary>
                    <p className="sidebar-text">{t.pageAdvancedHint}</p>
                    <HtmlSourceEditor
                      value={activePage.html}
                      onChange={(html) => updatePage(activePage.id, { html })}
                      label={t.pageContent}
                      onUploadImage={(selection) => openHtmlMediaDialog("image", activePage.id, selection)}
                      onUploadVideo={(selection) => openHtmlMediaDialog("video", activePage.id, selection)}
                      onUploadDocument={(selection) => openHtmlMediaDialog("document", activePage.id, selection)}
                      pendingSnippet={pendingHtmlSnippet?.pageId === activePage.id ? pendingHtmlSnippet : null}
                      onPendingSnippetApplied={() => setPendingHtmlSnippet(null)}
                      onSelectionChange={(selection) => rememberHtmlSelection(activePage.id, selection)}
                    />
                    <div className="page-editor-grid">
                      <label>
                        {t.spotlightImageUrl}
                        <input value={activePage.imageUrl} onChange={(e) => updatePage(activePage.id, { imageUrl: e.target.value })} placeholder={t.optionalImageUrl} />
                      </label>
                      <label>
                        {t.spotlightVideoUrl}
                        <input value={activePage.videoUrl} onChange={(e) => updatePage(activePage.id, { videoUrl: e.target.value })} placeholder={t.optionalVideoUrl} />
                      </label>
                    </div>
                  </details>
                </section>
              ) : (
                <section className="card studio-panel">
                  <EmptyState title={language === "ru" ? "Добавьте первую страницу, чтобы начать редактировать урок." : "Add the first page to start editing this lesson."} />
                </section>
              )}

              <section className="card studio-panel">
                <div className="studio-panel-head">
                  <div>
                    <strong className="studio-eyebrow">{language === "ru" ? "Рекомендации" : "Recommendations"}</strong>
                    <h3>{language === "ru" ? "Подсказки к курсу и урокам" : "Course and lesson recommendations"}</h3>
                  </div>
                </div>
                <div className="stack">
                  <label>
                    {language === "ru" ? "Заголовок" : "Title"}
                    <input
                      value={recommendationDraft.title}
                      onChange={(e) => setRecommendationDraft((current) => ({ ...current, title: e.target.value }))}
                      placeholder={language === "ru" ? "Например, Повторите тему перед тестом" : "For example, Review this topic before the test"}
                    />
                  </label>
                  <label>
                    {language === "ru" ? "Текст рекомендации" : "Recommendation text"}
                    <textarea
                      value={recommendationDraft.text}
                      onChange={(e) => setRecommendationDraft((current) => ({ ...current, text: e.target.value }))}
                      rows={3}
                    />
                  </label>
                  <label>
                    {language === "ru" ? "Привязать к уроку" : "Attach to lesson"}
                    <select
                      value={recommendationDraft.lessonId}
                      onChange={(e) => setRecommendationDraft((current) => ({ ...current, lessonId: e.target.value }))}
                    >
                      <option value="">{language === "ru" ? "Только для курса" : "Course-level recommendation"}</option>
                      {(lessons.data ?? []).map((lesson) => (
                        <option key={lesson.id} value={lesson.id}>
                          {lesson.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button type="button" className="page-action secondary" onClick={() => void createRecommendation()} disabled={!selectedCourseId || !recommendationDraft.title.trim() || !recommendationDraft.text.trim()}>
                    {language === "ru" ? "Добавить рекомендацию" : "Add recommendation"}
                  </button>
                </div>
                <div className="stack">
                  {(recommendations.data ?? []).map((item) => (
                    <article key={item.id} className="list-row">
                      <div>
                        <strong>{item.title}</strong>
                        <span>{item.text}</span>
                        <div className="user-subline">
                          <span>{item.lesson_id ? `${language === "ru" ? "Урок" : "Lesson"} #${item.lesson_id}` : language === "ru" ? "Привязка к курсу" : "Course level"}</span>
                        </div>
                      </div>
                      <button type="button" className="page-action secondary" onClick={() => void removeRecommendation(item.id)}>
                        {t.remove}
                      </button>
                    </article>
                  ))}
                  {!recommendations.loading && !(recommendations.data ?? []).length && (
                    <EmptyState title={language === "ru" ? "Рекомендаций пока нет" : "No recommendations yet"} />
                  )}
                </div>
              </section>

              <section className="card studio-panel">
                <details className="advanced-panel">
                  <summary>{t.sharedLessonSettings}</summary>
                  <p className="sidebar-text">{t.lessonAdvancedHint}</p>
                  <div className="media-attachment-grid">
                    <MediaAttachmentCard
                      scope="lesson"
                      kind="image"
                      url={form.imageUrl}
                      onAttach={() => openMediaDialog({ scope: "lesson", kind: "image" })}
                      onRemove={() => setForm((current) => ({ ...current, imageUrl: "" }))}
                    />
                    <MediaAttachmentCard
                      scope="lesson"
                      kind="video"
                      url={form.videoUrl}
                      onAttach={() => openMediaDialog({ scope: "lesson", kind: "video" })}
                      onRemove={() => setForm((current) => ({ ...current, videoUrl: "" }))}
                    />
                  </div>
                  <div className="page-editor-grid">
                    <label>
                      {t.lessonHeroImage}
                      <input value={form.imageUrl} onChange={(e) => setForm({ ...form, imageUrl: e.target.value })} placeholder={t.imageUrl} />
                    </label>
                    <label>
                      {t.lessonHeroVideo}
                      <input value={form.videoUrl} onChange={(e) => setForm({ ...form, videoUrl: e.target.value })} placeholder={t.videoUrl} />
                    </label>
                  </div>
                  <label className="studio-form-span">
                    {t.legacyFallbackContent}
                    <textarea
                      value={form.content}
                      onChange={(e) => setForm({ ...form, content: e.target.value })}
                      placeholder={t.legacyFallbackPlaceholder}
                      rows={8}
                    />
                  </label>
                </details>
              </section>
            </div>
          </section>
        </form>
      </section>
      <MediaPickerDialog
        open={Boolean(mediaTarget)}
        kind={mediaTarget?.kind ?? "image"}
        assets={mediaAssets.data ?? []}
        onClose={() => setMediaTarget(null)}
        onSelect={applySelectedMedia}
        onUpload={uploadMediaFile}
      />
    </section>
  );
}

const TEST_PRESETS = [
  { id: "quick", baselineDifficulty: 2, questionLimit: 5 },
  { id: "standard", baselineDifficulty: 3, questionLimit: 10 },
  { id: "exam", baselineDifficulty: 4, questionLimit: 15 }
] as const;

function createQuestionDraft(difficulty = 3) {
  return {
    text: "",
    explanation: "",
    difficulty,
    estimatedSeconds: 30,
    topicIds: [] as string[],
    options: ["", "", "", ""],
    correctIndex: 0
  };
}

export function TestsPage({ session }: { session: SessionState }) {
  const { t } = useUi();
  const courses = useRemote<CourseInfo[]>("/courses", session);
  const tests = useRemote<TestInfo[]>("/tests", session);
  const topics = useRemote<TopicInfo[]>("/topics", session);
  const [refreshKey, setRefreshKey] = useState(0);
  const testsRefresh = useRemote<TestInfo[]>("/tests", session, refreshKey);
  const [form, setForm] = useState({ courseId: "", title: "", baselineDifficulty: 3, questionLimit: 10 });
  const [selectedTestId, setSelectedTestId] = useState("");
  const [questionRefreshKey, setQuestionRefreshKey] = useState(0);
  const [questionStatus, setQuestionStatus] = useState("");
  const [questionError, setQuestionError] = useState("");
  const [editingQuestionId, setEditingQuestionId] = useState<number | null>(null);
  const [questionForm, setQuestionForm] = useState(createQuestionDraft());
  const questionEditorRef = useRef<HTMLFormElement | null>(null);
  const questionTextFieldRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!form.courseId && courses.data?.length) {
      setForm((current) => ({ ...current, courseId: String(courses.data?.[0].id ?? "") }));
    }
  }, [courses.data, form.courseId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const created = (await apiPost("/tests", session, {
      course_id: Number(form.courseId),
      title: form.title,
      baseline_difficulty: form.baselineDifficulty,
      question_limit: form.questionLimit
    })) as { id?: number };
    setForm((current) => ({ ...current, title: "", baselineDifficulty: 3, questionLimit: 10 }));
    if (created.id) {
      setSelectedTestId(String(created.id));
    }
    setRefreshKey((value) => value + 1);
  }

  const effectiveTests = testsRefresh.data ?? tests.data ?? [];
  const activeCourseId = form.courseId || String(courses.data?.[0]?.id ?? "");
  const selectedCourse = (courses.data ?? []).find((course) => String(course.id) === activeCourseId);
  const courseTitles = new Map((courses.data ?? []).map((course) => [course.id, course.title]));
  const testsForCourse = effectiveTests.filter((item) => String(item.course_id) === activeCourseId);
  const difficultyDescriptions = [
    t.baselineDifficultyLevel1,
    t.baselineDifficultyLevel2,
    t.baselineDifficultyLevel3,
    t.baselineDifficultyLevel4,
    t.baselineDifficultyLevel5
  ];
  const difficultyDescription = difficultyDescriptions[Math.max(0, Math.min(4, form.baselineDifficulty - 1))];
  const questionPlanLabel =
    form.questionLimit <= 6 ? t.testsLengthShort : form.questionLimit <= 10 ? t.testsLengthBalanced : t.testsLengthExtended;
  const suggestedTitle = t.testsRecommendedTitle.replace("{course}", selectedCourse?.title ?? t.courseLabel);
  const courseQuestionBankCount = testsForCourse.reduce((total, item) => total + (item.question_count ?? 0), 0);
  const activeTestId = selectedTestId || String(testsForCourse[0]?.id ?? "");
  const questions = useRemote<TestQuestionInfo[]>(activeTestId ? `/questions?test_id=${activeTestId}` : null, session, questionRefreshKey);
  const selectedTest = testsForCourse.find((item) => String(item.id) === activeTestId);
  const defaultQuestionDifficulty = selectedTest?.baseline_difficulty ?? form.baselineDifficulty;

  useEffect(() => {
    if (!testsForCourse.length) {
      setSelectedTestId("");
      return;
    }
    if (!selectedTestId || !testsForCourse.some((item) => String(item.id) === selectedTestId)) {
      setSelectedTestId(String(testsForCourse[0].id));
    }
  }, [selectedTestId, testsForCourse]);

  useEffect(() => {
    setEditingQuestionId(null);
    setQuestionStatus("");
    setQuestionError("");
    setQuestionForm(createQuestionDraft(defaultQuestionDifficulty));
  }, [activeTestId, defaultQuestionDifficulty]);

  useEffect(() => {
    if (!editingQuestionId) {
      return;
    }
    questionEditorRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    window.setTimeout(() => {
      questionTextFieldRef.current?.focus({ preventScroll: true });
      questionTextFieldRef.current?.setSelectionRange(0, 0);
    }, 150);
  }, [editingQuestionId]);

  function applyPreset(presetId: (typeof TEST_PRESETS)[number]["id"]) {
    const preset = TEST_PRESETS.find((item) => item.id === presetId);
    if (!preset) {
      return;
    }
    setForm((current) => ({
      ...current,
      baselineDifficulty: preset.baselineDifficulty,
      questionLimit: preset.questionLimit
    }));
  }

  function updateQuestionOption(index: number, value: string) {
    setQuestionForm((current) => ({
      ...current,
      options: current.options.map((item, itemIndex) => (itemIndex === index ? value : item))
    }));
  }

  function addQuestionOption() {
    setQuestionForm((current) => {
      if (current.options.length >= 6) {
        return current;
      }
      return { ...current, options: [...current.options, ""] };
    });
  }

  function removeQuestionOption(index: number) {
    setQuestionForm((current) => {
      if (current.options.length <= 2) {
        return current;
      }
      const nextOptions = current.options.filter((_, itemIndex) => itemIndex !== index);
      return {
        ...current,
        options: nextOptions,
        correctIndex: Math.min(current.correctIndex, nextOptions.length - 1)
      };
    });
  }

  function toggleQuestionTopic(topicId: string) {
    setQuestionForm((current) => ({
      ...current,
      topicIds: current.topicIds.includes(topicId) ? current.topicIds.filter((item) => item !== topicId) : [...current.topicIds, topicId]
    }));
  }

  function resetQuestionEditor() {
    setEditingQuestionId(null);
    setQuestionStatus("");
    setQuestionError("");
    setQuestionForm(createQuestionDraft(defaultQuestionDifficulty));
  }

  function startQuestionEditing(question: TestQuestionInfo) {
    const optionTexts = (question.options ?? []).map((item) => item.text);
    while (optionTexts.length < 4) {
      optionTexts.push("");
    }
    setEditingQuestionId(question.id);
    setQuestionStatus("");
    setQuestionError("");
    setQuestionForm({
      text: question.text,
      explanation: question.explanation,
      difficulty: question.difficulty,
      estimatedSeconds: question.estimated_seconds,
      topicIds: (question.topic_ids ?? []).map((item) => String(item)),
      options: optionTexts,
      correctIndex: Math.max(0, (question.options ?? []).findIndex((item) => item.is_correct))
    });
  }

  return (
    <section className="page-stack">
      <PageHeader title={t.testsPageTitle} subtitle={t.testsPageSubtitle} />
      <section className="grid tests-layout">
        <FormCard title={t.createTest} onSubmit={submit}>
          <p className="form-helper">{t.testsSetupHint}</p>
          <label>
            {t.courseLabel}
            <select value={form.courseId} onChange={(e) => setForm({ ...form, courseId: e.target.value })}>
              {(courses.data ?? []).map((course) => (
                <option key={course.id} value={course.id}>
                  {course.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t.testTitle}
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder={suggestedTitle} required />
          </label>
          <section className="test-config-panel">
            <div className="test-config-head">
              <strong>{t.testsPresetLabel}</strong>
              <span>{t.testsPresetHint}</span>
            </div>
            <div className="test-preset-grid">
              <button type="button" className="secondary" onClick={() => applyPreset("quick")}>
                {t.testsPresetQuick}
              </button>
              <button type="button" className="secondary" onClick={() => applyPreset("standard")}>
                {t.testsPresetStandard}
              </button>
              <button type="button" className="secondary" onClick={() => applyPreset("exam")}>
                {t.testsPresetExam}
              </button>
            </div>
          </section>
          <label>
            {t.baselineDifficulty}
            <input
              type="range"
              value={form.baselineDifficulty}
              min={1}
              max={5}
              onChange={(e) => setForm({ ...form, baselineDifficulty: Number(e.target.value) })}
              aria-label={t.baselineDifficulty}
            />
            <span className="form-value-badge">{form.baselineDifficulty}</span>
            <span className="form-helper">{t.baselineDifficultyHint}</span>
            <span className="form-helper strong">{difficultyDescription}</span>
          </label>
          <label>
            {t.questionLimit}
            <input type="number" value={form.questionLimit} min={1} max={50} onChange={(e) => setForm({ ...form, questionLimit: Number(e.target.value) })} aria-label={t.questionLimit} />
            <span className="form-helper">{t.questionLimitHint}</span>
            <span className="form-helper strong">{questionPlanLabel}</span>
          </label>
          <section className="test-config-panel summary" aria-label={t.selectedCourseOverview}>
            <div className="test-config-head">
              <strong>{t.selectedCourseOverview}</strong>
              <span>{t.testsAdaptiveBehavior}</span>
            </div>
            <div className="test-summary-grid">
              <article>
                <strong>{t.selectedCourseDescription}</strong>
                <span>{selectedCourse?.title ?? t.loading}</span>
                <p>{selectedCourse?.description || t.selectedCourseEmptyDescription}</p>
              </article>
              <article>
                <strong>{t.selectedCourseTestsCount}</strong>
                <span>{testsForCourse.length}</span>
                <p>
                  {t.questionBankLabel}: {courseQuestionBankCount || t.testsBankEmpty}
                </p>
              </article>
              <article>
                <strong>{t.selectedCourseDifficultyPlan}</strong>
                <span>{form.baselineDifficulty}</span>
                <p>{difficultyDescription}</p>
              </article>
              <article>
                <strong>{t.selectedCourseQuestionPlan}</strong>
                <span>{form.questionLimit}</span>
                <p>{questionPlanLabel}</p>
              </article>
            </div>
            <div className="test-summary-note">
              <strong>{t.selectedCourseTitleSuggestion}</strong>
              <span>{suggestedTitle}</span>
            </div>
            <p className="form-helper">
              {t.testsAdaptiveBehaviorHint.replace("{difficulty}", String(form.baselineDifficulty)).replace("{limit}", String(form.questionLimit))}
            </p>
          </section>
          <button type="submit">{t.createTestAction}</button>
        </FormCard>
        <section className="stack">
          <DataTable
            title={t.testsLabel}
            columns={[t.id, t.title, t.courseLabel, t.baselineDifficulty, t.questionLimit, t.questionBankLabel]}
            rows={effectiveTests.map((item) => [
              String(item.id),
              item.title,
              courseTitles.get(item.course_id) ?? String(item.course_id),
              String(item.baseline_difficulty ?? "-"),
              String(item.question_limit),
              item.question_count ? String(item.question_count) : t.testsBankEmpty
            ])}
            loading={tests.loading && testsRefresh.loading}
            error={tests.error || testsRefresh.error}
          />
          <FormCard
            title={t.questionEditorTitle}
            onSubmit={async (event) => {
              event.preventDefault();
              if (!activeTestId) {
                return;
              }
              const options = questionForm.options
                .map((item, index) => ({ text: item.trim(), is_correct: index === questionForm.correctIndex }))
                .filter((item) => item.text);
              const payload = {
                test_id: Number(activeTestId),
                text: questionForm.text,
                explanation: questionForm.explanation,
                difficulty: questionForm.difficulty,
                estimated_seconds: questionForm.estimatedSeconds,
                topic_ids: questionForm.topicIds.map((item) => Number(item)),
                options
              };
              setQuestionError("");
              try {
                if (editingQuestionId) {
                  await apiPatch(`/questions/${editingQuestionId}`, session, payload);
                  setQuestionStatus(t.questionUpdated);
                } else {
                  await apiPost("/questions", session, payload);
                  setQuestionStatus(t.questionCreated);
                }
                setEditingQuestionId(null);
                setQuestionForm(createQuestionDraft(defaultQuestionDifficulty));
                setQuestionRefreshKey((value) => value + 1);
                setRefreshKey((value) => value + 1);
              } catch (err) {
                setQuestionError(err instanceof Error ? err.message : t.failedSaveQuestion);
              }
            }}
            className="question-editor-card"
            formRef={questionEditorRef}
          >
            <p className="form-helper">{t.questionEditorHint}</p>
            {questionStatus ? <Notice text={questionStatus} /> : null}
            {questionError ? <Notice text={questionError} tone="error" /> : null}
            <label>
              {t.selectTestForQuestions}
              <select value={activeTestId} onChange={(e) => setSelectedTestId(e.target.value)} disabled={!testsForCourse.length}>
                {testsForCourse.length ? (
                  testsForCourse.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.title}
                    </option>
                  ))
                ) : (
                  <option value="">{t.selectTestFirst}</option>
                )}
              </select>
            </label>
            {selectedTest ? (
              <>
                <div className="test-summary-note">
                  <strong>{selectedTest.title}</strong>
                  <span>
                    {t.baselineDifficulty}: {selectedTest.baseline_difficulty ?? form.baselineDifficulty} | {t.questionLimit}: {selectedTest.question_limit}
                  </span>
                </div>
                {editingQuestionId ? (
                  <div className="question-editor-banner">
                    <strong>{t.editingQuestionLabel.replace("{id}", String(editingQuestionId))}</strong>
                    <button type="button" className="secondary" onClick={resetQuestionEditor}>
                      {t.cancelQuestionEditing}
                    </button>
                  </div>
                ) : null}
                <label>
                  {t.questionText}
                  <textarea
                    ref={questionTextFieldRef}
                    value={questionForm.text}
                    onChange={(e) => setQuestionForm((current) => ({ ...current, text: e.target.value }))}
                    rows={4}
                    required
                  />
                </label>
                <div className="question-editor-grid">
                  <label>
                    {t.questionDifficulty}
                    <input
                      type="number"
                      min={1}
                      max={5}
                      value={questionForm.difficulty}
                      onChange={(e) => setQuestionForm((current) => ({ ...current, difficulty: Number(e.target.value) }))}
                      required
                    />
                  </label>
                  <label>
                    {t.questionEstimatedSeconds}
                    <input
                      type="number"
                      min={10}
                      max={600}
                      value={questionForm.estimatedSeconds}
                      onChange={(e) => setQuestionForm((current) => ({ ...current, estimatedSeconds: Number(e.target.value) }))}
                      required
                    />
                  </label>
                </div>
                <label>
                  {t.questionExplanation}
                  <textarea
                    value={questionForm.explanation}
                    onChange={(e) => setQuestionForm((current) => ({ ...current, explanation: e.target.value }))}
                    rows={3}
                  />
                </label>
                <section className="test-config-panel">
                  <div className="test-config-head">
                    <strong>{t.questionTopics}</strong>
                    <span>{topics.data?.length ? "" : t.noTopicsAvailable}</span>
                  </div>
                  {topics.data?.length ? (
                    <div className="question-topics-grid">
                      {topics.data.map((topic) => (
                        <label key={topic.id} className="topic-chip">
                          <input type="checkbox" checked={questionForm.topicIds.includes(String(topic.id))} onChange={() => toggleQuestionTopic(String(topic.id))} />
                          <span>{topic.title}</span>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <p className="form-helper">{t.noTopicsAvailable}</p>
                  )}
                </section>
                <section className="test-config-panel">
                  <div className="test-config-head">
                    <strong>{t.questionOptions}</strong>
                    <span>{t.questionCorrectOption}</span>
                  </div>
                  <div className="question-options-list">
                    {questionForm.options.map((option, index) => (
                      <div key={`option-${index}`} className="question-option-row">
                        <label className="question-option-radio">
                          <input
                            type="radio"
                            name="correctOption"
                            checked={questionForm.correctIndex === index}
                            onChange={() => setQuestionForm((current) => ({ ...current, correctIndex: index }))}
                          />
                          <span>{t.answerOptionLabel.replace("{number}", String(index + 1))}</span>
                        </label>
                        <input
                          value={option}
                          onChange={(e) => updateQuestionOption(index, e.target.value)}
                          placeholder={t.answerOptionLabel.replace("{number}", String(index + 1))}
                          required
                        />
                        <button type="button" className="secondary" onClick={() => removeQuestionOption(index)} disabled={questionForm.options.length <= 2}>
                          {t.removeAnswerOption}
                        </button>
                      </div>
                    ))}
                  </div>
                  <button type="button" className="secondary" onClick={addQuestionOption} disabled={questionForm.options.length >= 6}>
                    {t.addAnswerOption}
                  </button>
                </section>
                <div className="question-editor-actions">
                  <button type="submit">{editingQuestionId ? t.saveQuestionAction : t.createQuestionAction}</button>
                  {editingQuestionId ? (
                    <button type="button" className="secondary" onClick={resetQuestionEditor}>
                      {t.cancelQuestionEditing}
                    </button>
                  ) : null}
                </div>
                <article className="test-config-panel question-list-card">
                  <h3>{t.questionsInTest}</h3>
                  {questions.error ? <Notice text={questions.error} tone="error" /> : null}
                  {questions.loading ? (
                    <EmptyState title={t.loading} />
                  ) : questions.data?.length ? (
                    <div className="question-list">
                      {questions.data.map((item) => (
                        <article key={item.id} className="question-list-item">
                          <div className="question-list-head">
                            <strong>{item.text}</strong>
                            <span>#{item.id}</span>
                          </div>
                          <div className="question-list-meta">
                            <span>
                              {t.questionDifficulty}: {item.difficulty}
                            </span>
                            <span>
                              {t.questionEstimatedSeconds}: {item.estimated_seconds}
                            </span>
                            <span>
                              {t.optionCount}: {item.option_count}
                            </span>
                          </div>
                          <div className="question-list-actions">
                            <button type="button" className="secondary" onClick={() => startQuestionEditing(item)}>
                              {t.editQuestionAction}
                            </button>
                          </div>
                          {item.topic_titles.length ? <span>{item.topic_titles.join(", ")}</span> : null}
                          {item.explanation ? <p>{item.explanation}</p> : null}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <EmptyState title={t.noQuestionsInTest} />
                  )}
                </article>
              </>
            ) : (
              <EmptyState title={t.selectTestFirst} />
            )}
          </FormCard>
        </section>
      </section>
    </section>
  );
}

function AssignmentsPage({ session }: { session: SessionState }) {
  const { language, t } = useUi();
  const courses = useRemote<CourseInfo[]>("/courses", session);
  const users = useRemote<UserInfo[]>("/users", session);
  const [form, setForm] = useState({ courseId: "", userId: "" });
  const [status, setStatus] = useState("");

  useEffect(() => {
    const firstCourse = courses.data?.[0];
    const firstUser = users.data?.[0];
    if (!form.courseId && firstCourse) {
      setForm((current) => ({ ...current, courseId: String(firstCourse.id) }));
    }
    if (!form.userId && firstUser) {
      setForm((current) => ({ ...current, userId: String(firstUser.id) }));
    }
  }, [courses.data, form.courseId, form.userId, users.data]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const result = await apiPost(`/courses/${form.courseId}/assign`, session, { user_id: Number(form.userId) });
    setStatus(language === "ru" ? `Назначено для ${result.assigned_users} пользовател${result.assigned_users === 1 ? "я" : "ей"}` : `Assigned to ${result.assigned_users} user(s)`);
  }

  return (
    <section className="page-stack">
      <PageHeader title={t.assignmentsPageTitle} subtitle={t.assignmentsPageSubtitle} />
      {status && <Notice text={status} />}
      <section className="assignments-layout">
        <div className="assignment-primary-grid">
          <FormCard title={t.assignCourse} onSubmit={submit} className="assignment-primary-card">
            <p className="form-helper form-helper-intro">
              {language === "ru"
                ? "Основной сценарий страницы: выберите курс и слушателя, чтобы открыть ученику доступ к обучению."
                : "Primary workflow: choose a course and a learner to grant access to the learning path."}
            </p>
            <div className="assignment-form-row">
              <label>
                {t.courseLabel}
                <select value={form.courseId} onChange={(e) => setForm({ ...form, courseId: e.target.value })}>
                  {(courses.data ?? []).map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t.learner}
                <select value={form.userId} onChange={(e) => setForm({ ...form, userId: e.target.value })}>
                  {(users.data ?? []).map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.full_name} ({user.email})
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="assignment-actions">
              <button type="submit" className="assignment-primary-action" disabled={!form.courseId || !form.userId}>
                {t.assign}
              </button>
            </div>
          </FormCard>

          <article className="card assignment-guide-card">
            <span className="section-kicker">{language === "ru" ? "Как это работает" : "How it works"}</span>
            <h3>{t.howToDemo}</h3>
            <ol className="assignment-guide-list">
              <li>{t.howToDemo1}</li>
              <li>{t.howToDemo2}</li>
              <li>{t.howToDemo3}</li>
            </ol>
          </article>
        </div>
      </section>
    </section>
  );
}

function HomeworkReviewsPage({ session }: { session: SessionState }) {
  const { language } = useUi();
  const assignments = useRemote<AssignmentInfo[]>("/assignments", session);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string>("");
  const [submissionsRefreshKey, setSubmissionsRefreshKey] = useState(0);
  const [reviewForm, setReviewForm] = useState({ submissionId: "", status: "in_review", comment: "" });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const practicalSubmissions = useRemote<AssignmentSubmissionInfo[]>(
    selectedAssignmentId ? `/assignments/${selectedAssignmentId}/submissions` : null,
    session,
    submissionsRefreshKey
  );

  useEffect(() => {
    if (assignments.data?.length && !selectedAssignmentId) {
      setSelectedAssignmentId(String(assignments.data[0].id));
    }
  }, [assignments.data, selectedAssignmentId]);

  async function reviewSubmission(event: FormEvent) {
    event.preventDefault();
    if (!reviewForm.submissionId) {
      return;
    }
    setError("");
    setStatus("");
    try {
      await apiPost(`/submissions/${reviewForm.submissionId}/review`, session, {
        status: reviewForm.status,
        comment: reviewForm.comment
      });
      setReviewForm((current) => ({ ...current, comment: "" }));
      setSubmissionsRefreshKey((value) => value + 1);
      setStatus(language === "ru" ? "Проверка сохранена" : "Submission review saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : language === "ru" ? "Не удалось сохранить проверку" : "Failed to save review");
    }
  }

  const selectedAssignment = (assignments.data ?? []).find((item) => String(item.id) === selectedAssignmentId);
  const submissionStatusLabel = (rawStatus: string) => {
    const value = (rawStatus || "").toLowerCase();
    if (value === "submitted") return language === "ru" ? "Отправлено" : "Submitted";
    if (value === "approved") return language === "ru" ? "Принято" : "Approved";
    if (value === "rejected" || value === "needs_revision") return language === "ru" ? "Нужна доработка" : "Needs revision";
    if (value === "draft") return language === "ru" ? "Черновик" : "Draft";
    if (value === "in_review") return language === "ru" ? "На проверке" : "In review";
    return language === "ru" ? "Не начато" : "Not started";
  };
  const reviewStatusLabel = (rawStatus: string) => {
    const value = (rawStatus || "").toLowerCase();
    if (value === "in_review") return language === "ru" ? "На проверке" : "In review";
    if (value === "approved") return language === "ru" ? "Принято" : "Approved";
    if (value === "needs_revision") return language === "ru" ? "Нужна доработка" : "Needs revision";
    if (value === "rejected") return language === "ru" ? "Отклонено" : "Rejected";
    return rawStatus;
  };

  return (
    <section className="page-stack">
      <PageHeader
        title={language === "ru" ? "Проверка домашних заданий" : "Homework review"}
        subtitle={
          language === "ru"
            ? "Проверяйте отправленные практические работы учеников и возвращайте комментарии."
            : "Review submitted practical assignments and send feedback to learners."
        }
      />
      {status && <Notice text={status} />}
      {error && <Notice text={error} tone="error" />}
      <section className="homework-review-layout">
        <article className="card homework-review-sidebar">
          <span className="section-kicker">{language === "ru" ? "Задания" : "Assignments"}</span>
          <h3>{language === "ru" ? "Выберите практику" : "Select practice"}</h3>
          <div className="assignment-list">
            {(assignments.data ?? []).map((item) => (
              <button
                key={item.id}
                type="button"
                className={`list-button ${selectedAssignmentId === String(item.id) ? "active" : ""}`}
                onClick={() => {
                  setSelectedAssignmentId(String(item.id));
                  setReviewForm((current) => ({ ...current, submissionId: "" }));
                }}
              >
                <strong>{item.title}</strong>
                <span>#{item.id}</span>
              </button>
            ))}
            {assignments.loading && <EmptyState title={language === "ru" ? "Загружаем задания..." : "Loading assignments..."} />}
            {assignments.error && <Notice text={assignments.error} tone="error" />}
            {!assignments.loading && !(assignments.data ?? []).length && (
              <EmptyState title={language === "ru" ? "Практических заданий пока нет" : "No practical assignments yet"} />
            )}
          </div>
        </article>

        <FormCard title={language === "ru" ? "Проверить работу" : "Review submission"} onSubmit={reviewSubmission} className="homework-review-card">
          <p className="form-helper form-helper-intro">
            {selectedAssignment
              ? selectedAssignment.description || selectedAssignment.title
              : language === "ru"
                ? "Выберите задание слева, чтобы увидеть отправленные работы."
                : "Select an assignment on the left to see submitted work."}
          </p>
          <label>
            {language === "ru" ? "Работа ученика" : "Learner submission"}
            <select value={reviewForm.submissionId} onChange={(e) => setReviewForm({ ...reviewForm, submissionId: e.target.value })}>
              <option value="">{language === "ru" ? "Выберите работу" : "Select submission"}</option>
              {(practicalSubmissions.data ?? []).map((submission) => (
                <option key={submission.id} value={submission.id}>
                  #{submission.id} · user {submission.student_user_id} · {submissionStatusLabel(submission.status)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {language === "ru" ? "Статус проверки" : "Review status"}
            <select value={reviewForm.status} onChange={(e) => setReviewForm({ ...reviewForm, status: e.target.value })}>
              <option value="in_review">{reviewStatusLabel("in_review")}</option>
              <option value="approved">{reviewStatusLabel("approved")}</option>
              <option value="needs_revision">{reviewStatusLabel("needs_revision")}</option>
              <option value="rejected">{reviewStatusLabel("rejected")}</option>
            </select>
          </label>
          <label>
            {language === "ru" ? "Комментарий куратора" : "Curator comment"}
            <textarea value={reviewForm.comment} onChange={(e) => setReviewForm({ ...reviewForm, comment: e.target.value })} rows={6} />
          </label>
          <div className="assignment-actions">
            <button type="submit" disabled={!reviewForm.submissionId}>
              {language === "ru" ? "Сохранить проверку" : "Save review"}
            </button>
          </div>
          {practicalSubmissions.error && <Notice text={practicalSubmissions.error} tone="error" />}
          {(practicalSubmissions.data ?? []).length === 0 && (
            <EmptyState title={language === "ru" ? "Нет отправленных работ по выбранному заданию" : "No submissions for the selected assignment"} />
          )}
        </FormCard>
      </section>
    </section>
  );
}

function AnalyticsPage({ session }: { session: SessionState }) {
  const { language, t } = useUi();
  const [learnerId, setLearnerId] = useState("3");
  const [refreshKey, setRefreshKey] = useState(0);
  const dashboard = useRemote<Record<string, number>>("/analytics/dashboard", session);
  const learner = useRemote<{
    results: Array<{ score_percent: number; weak_topics: Array<{ topic_title: string; score: number }> }>;
    recommendations: Array<{
      text: string;
      priority: number;
      topic_title?: string | null;
      lesson_title?: string | null;
      course_title?: string | null;
      reason?: string | null;
      signal_level?: string | null;
    }>;
  }>(
    `/analytics/learners/${learnerId}`,
    session,
    refreshKey
  );

  return (
    <section className="page-stack">
      <PageHeader title={t.analyticsPageTitle} subtitle={t.analyticsPageSubtitle} />
      <section className="grid two-columns">
        <article className="card">
          <h3>{t.overview}</h3>
          {dashboard.data ? <KeyValueList items={Object.entries(dashboard.data).map(([key, value]) => [key, String(value)])} /> : <EmptyState title={t.loadingAnalytics} />}
        </article>
        <article className="card">
          <h3>{t.learnerDetail}</h3>
          <div className="inline-form">
            <input value={learnerId} onChange={(e) => setLearnerId(e.target.value)} placeholder={t.learnerId} />
            <button onClick={() => setRefreshKey((value) => value + 1)}>{t.load}</button>
          </div>
          {learner.error && <Notice text={learner.error} tone="error" />}
          <div className="stack">
            {(learner.data?.results ?? []).map((result, index) => (
              <div className="result-card" key={`${result.score_percent}-${index}`}>
                <strong>{language === "ru" ? `Результат попытки: ${result.score_percent}%` : `Attempt score: ${result.score_percent}%`}</strong>
                <span>{result.weak_topics.map((topic) => `${topic.topic_title}: ${topic.score}`).join(", ") || t.noWeakTopics}</span>
              </div>
            ))}
            {(learner.data?.recommendations ?? []).map((item) => (
              <div className="result-card" key={`${item.priority}-${item.text}`}>
                <strong>{item.topic_title || `${t.priority} ${item.priority}`}</strong>
                <span>
                  {[item.lesson_title, item.course_title].filter(Boolean).join(" • ") || t.noLinkedLesson}
                </span>
                <span>{item.reason || item.text}</span>
                <span>{t.action}: {item.text}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </section>
  );
}

function SettingsPage({ session }: { session: SessionState }) {
  const { language, setLanguage, t } = useUi();
  const profile = useRemote<UserProfileInfo>("/auth/me", session);

  return (
    <section className="page-stack">
      <PageHeader title={t.settingsPageTitle} subtitle={t.settingsPageSubtitle} />
      <section className="grid two-columns">
        <article className="card stack">
          <h3>{t.language}</h3>
          <select value={language} onChange={(e) => setLanguage(e.target.value === "en" ? "en" : "ru")}>
            <option value="ru">{t.russian}</option>
            <option value="en">{t.english}</option>
          </select>
          <p className="sidebar-text">
            {language === "ru"
              ? "Русский включен по умолчанию. Переключение применяется сразу и сохраняется в этом браузере."
              : "Russian is the default. Changing the language applies immediately and is saved in this browser."}
          </p>
        </article>
        <article className="card stack">
          <h3>{t.profile}</h3>
          {profile.data ? (
            <KeyValueList
              items={[
                [t.name, profile.data.full_name],
                [t.email, profile.data.email],
                [t.currentRole, formatRoleLabel(profile.data.tenant_role, t)],
                [t.tenantCode, session.tenantCode]
              ]}
            />
          ) : (
            <EmptyState title={t.loadingProfile} />
          )}
        </article>
      </section>
    </section>
  );
}

function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="page-header">
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </header>
  );
}

function FormCard({
  title,
  children,
  onSubmit,
  className = "",
  formRef
}: {
  title: string;
  children: ReactNode;
  onSubmit: (event: FormEvent) => void;
  className?: string;
  formRef?: Ref<HTMLFormElement>;
}) {
  return (
    <form ref={formRef} className={`card form-card ${className}`.trim()} onSubmit={onSubmit}>
      <h3>{title}</h3>
      {children}
    </form>
  );
}

function DataTable({ title, columns, rows, loading, error }: { title: string; columns: string[]; rows: ReactNode[][]; loading?: boolean; error?: string }) {
  const { t } = useUi();
  return (
    <article className="card">
      <h3>{title}</h3>
      {error && <Notice text={error} tone="error" />}
      {loading ? (
        <EmptyState title={t.loading} />
      ) : rows.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${title}-${index}`}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${title}-${index}-${cellIndex}`}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title={t.noData} />
      )}
    </article>
  );
}

function KeyValueList({ items }: { items: Array<[string, string]> }) {
  return (
    <div className="stack">
      {items.map(([key, value]) => (
        <div className="list-row" key={key}>
          <div>
            <strong>{key}</strong>
            <span>{value}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function Notice({ text, tone = "success" }: { text: string; tone?: "success" | "error" }) {
  return <div className={`notice ${tone}`}>{text}</div>;
}

function EmptyState({ title }: { title: string }) {
  return <div className="empty-state">{title}</div>;
}

export function App() {
  const [session, setSession] = useState<SessionState | null>(() => readStoredSession());
  const [savedAccounts, setSavedAccounts] = useState<SavedAccount[]>(() => readSavedAccounts());
  const [language, setLanguage] = useState<Language>(() => getInitialLanguage());
  const applySession = useCallback((nextSession: SessionState | null) => {
    if (!nextSession) {
      setSession(null);
      return;
    }
    setSession(normalizeSession(nextSession));
  }, []);

  const handleLogin = useCallback((
    nextSession: SessionState,
    options: { login: string; organizationCode: string },
  ) => {
    applySession(nextSession);
    setSavedAccounts((current) => upsertSavedAccount(current, {
      id: buildSavedAccountId(options.organizationCode, options.login),
      organizationCode: options.organizationCode,
      login: options.login,
      lastUsedAt: new Date().toISOString(),
    }));
  }, [applySession]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    }
  }, [language]);

  useEffect(() => {
    writeStoredSession(session);
  }, [session]);

  useEffect(() => {
    writeSavedAccounts(savedAccounts);
  }, [savedAccounts]);

  useEffect(() => {
    configureSessionLifecycle({
      onSessionUpdate: (nextSession) => applySession(nextSession),
      onSessionInvalid: () => applySession(null),
    });
    return () => {
      configureSessionLifecycle({});
    };
  }, [applySession]);

  const value = useMemo(() => ({ language, setLanguage, t: getMessages(language) }), [language]);

  return (
    <LanguageContext.Provider value={value}>
      {session ? (
        <Shell session={session} onLogout={() => applySession(null)} onSessionChange={applySession} />
      ) : (
        <LoginPage onLogin={handleLogin} />
      )}
    </LanguageContext.Provider>
  );
}

