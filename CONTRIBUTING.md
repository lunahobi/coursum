# Руководство по вкладу

## Требования к окружению

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose (рекомендуется для полного стека)

## Локальный запуск

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
```

### Web

```bash
cd web
npm install
```

## Ветки и коммиты

- Создавайте отдельную ветку под каждую задачу.
- Держите коммиты небольшими и логически цельными.
- В сообщениях коммита описывайте причину и эффект изменений, а не только список файлов.

## Обязательные проверки

Перед открытием PR выполните:

### Backend

```bash
cd backend
python -m ruff check app tests
python -m mypy app/core app/models
python -m pytest -q
```

### Web

```bash
cd web
npm run lint
npm run format:check
npm test
npm run build
```

### E2E UI

```bash
cd web
npm run test:e2e
```

## Отчеты по тестам (Allure)

### API-результаты

```bash
python -m pytest backend/tests --alluredir allure-results/api -q
```

### UI-результаты

```bash
cd web
npm run test:e2e
```

### Общий отчет

```bash
cd web
npm run allure:all:generate
npm run allure:all:open
```

## Стиль кода

- Соблюдайте `.editorconfig` и правила линтеров проекта.
- Не добавляйте тестовые ветки логики в runtime-код.
- Сохраняйте обратную совместимость API, если явно не описана миграция.

## Чеклист PR

- [ ] Объем и цель изменений описаны.
- [ ] Добавлены/обновлены тесты для измененного поведения.
- [ ] Локально проходят lint/type/test проверки.
- [ ] Описаны последствия для миграций/деплоя (если есть).
- [ ] Обновлена документация (`README`, `docs`, `CHANGELOG`) при изменении поведения.
