# Runbook деплоя

## Целевая структура на сервере

Ожидаемый корень приложения:

- `/opt/app_new`
  - `backend`
  - `web`
  - `docker-compose.yml`

## Переменные окружения

Минимально необходимые production-переменные:

- `POSTGRES_PASSWORD`
- `LMS_SECRET_KEY` (длинный, нестандартный)
- `LMS_ENVIRONMENT=production`
- `LMS_CORS_ORIGINS` (список публичных web-origin)

## Стандартный сценарий деплоя

```bash
cd /opt/app_new
docker compose up -d --build backend web
docker compose ps
```

## Поведение миграций

В entrypoint backend-контейнера выполняется:

1. Проверка/stamp для уже существующей схемы (если нужно)
2. `alembic upgrade head`
3. Запуск приложения

Если backend уходит в restart-loop:

```bash
docker compose logs --tail=200 backend
```

## Проверки работоспособности

Проверка API и БД:

```bash
curl -f http://127.0.0.1:8000/health
curl -f http://127.0.0.1:8000/health/db
```

Проверка CORS preflight на публичном API:

```bash
curl -i -X OPTIONS "https://api.<your-domain>/api/v1/auth/login" \
  -H "Origin: https://<your-web-domain>" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"
```

## Smoke-проверки после деплоя

- вход в web-панель
- открытие страниц dashboard и analytics
- один полный цикл assignment submit + review

## Заметки по откату

- По возможности сохраняйте предыдущие слои образов.
- При неуспешном деплое восстановите предыдущий рабочий набор файлов и пересоберите сервис:

```bash
cd /opt/app_new
docker compose up -d --build backend
```

## Операционная чистка

Если на сервер случайно попали test/dev артефакты, удалите их из deploy-каталога перед пересборкой.
