# Стратегия тестирования

## Цели

- Защитить ключевые обучающие сценарии от регрессий.
- Сделать проверяемыми гарантии tenant-изоляции и RBAC.
- Проверять критичные UI-потоки через детерминированные браузерные тесты.

## Слои тестирования

### Backend unit/integration (Pytest)

Покрывает:
- auth, RBAC и tenant-границы
- API по курсам/урокам/тестам/практикам
- адаптивную логику и генерацию рекомендаций
- endpoint аналитики

Команда:

```bash
python -m pytest backend/tests -q
```

### Web unit/integration (Vitest + RTL)

Покрывает:
- рендер и взаимодействия на уровне страниц
- обработку API-состояний
- поведение dashboard/analytics

Команда:

```bash
cd web
npm test
```

### UI E2E smoke (Playwright)

Покрывает:
- страницу auth и поток логина
- навигацию по основным страницам teacher/admin панели
- отображение activity summary на dashboard

Команда:

```bash
cd web
npm run test:e2e
```

## Отчетность

### API Allure results

```bash
python -m pytest backend/tests --alluredir allure-results/api -q
```

### UI Allure results

Формируются reporter-ом Playwright в `allure-results/ui`.

### Общий отчет API + UI

```bash
cd web
npm run allure:all:generate
npm run allure:all:open
```

## Приоритеты покрытия к защите ВКР

1. tenant-изоляция и RBAC
2. жизненный цикл адаптивного тестирования
3. сценарий assignment review
4. согласованность аналитики дашборда
5. стабильная навигация и логин в админском UI
