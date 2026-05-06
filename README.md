# Corporate LMS MVP

Multi-tenant client-server corporate learning system for a bachelor thesis: backend REST API, React admin panel, and Flutter learner app with adaptive testing.

## Monorepo layout

- `backend` FastAPI + SQLAlchemy + Alembic + PostgreSQL-ready data model
- `web` React + TypeScript admin/teacher panel
- `mobile` Flutter learner app
- `docs` thesis-friendly architecture notes

## Key features

- multi-tenant isolation via `tenant_id` and request-scoped tenant resolution
- roles: learner, teacher, organization admin, system admin
- course, lesson, test and question management
- course assignment to users and groups
- adaptive testing with difficulty changes from `1..5`
- weak-topic recommendations after attempt completion
- analytics dashboard and learner reports
- password hashing, JWT auth with refresh, audit logs
- optional mock notification integration

## Backend setup

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
copy ..\\.env.example .env
python -m scripts.seed_demo
uvicorn app.main:app --reload
```

Default API base: `http://localhost:8000/api/v1`

## Docker setup

Run the full local stack:

```bash
docker compose up --build
```

Services:
- backend: `http://localhost:8000`
- web: `http://localhost:8080`
- postgres: `localhost:5432`

Load demo data into PostgreSQL:

```bash
docker compose run --rm --profile tools seed
```

Stop the stack:

```bash
docker compose down
```

Reset database volume completely:

```bash
docker compose down -v
```

## Web setup

```bash
cd web
npm install
npm run dev
```

Default web URL: `http://localhost:5173`

## Mobile setup

```bash
cd mobile
flutter pub get
flutter run
```

Mobile app is not containerized; it connects to the backend started locally or via Docker.

Default mobile API base:
- Android emulator: `http://10.0.2.2:8000/api/v1`
- other local targets: `http://localhost:8000/api/v1`

Override the mobile API base when needed:

```bash
flutter run --dart-define=API_BASE=http://<your-host-ip>:8000/api/v1
```

## Tenant model

- production-oriented mode: tenant resolved from subdomain
- local/test fallback: header `X-Tenant-Code`
- every tenant-bound table stores `tenant_id`
- protected routes require both JWT and active membership for current tenant

## Demo credentials

- system admin: `sysadmin@example.com` / `Password123!`
- tenant admin: `admin@acme.example.com` / `Password123!`
- teacher: `teacher@acme.example.com` / `Password123!`
- learner: `learner1@acme.example.com` / `Password123!`
- second tenant examples follow `@beta.example.com`

## Important API routes

- auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`
- tenants: `GET /tenants`, `GET /tenants/current`, `POST /tenants/select`
- users: `GET/POST/PATCH /users`
- courses: `GET/POST /courses`, `GET /courses/{id}`, `POST /courses/{id}/assign`
- lessons: `GET /lessons?course_id=`, `POST /lessons`, `POST /lessons/{id}/progress`
- tests: `GET/POST /tests`, `POST /questions`, `POST /tests/{id}/start`, `GET /attempts/{id}/next-question`, `POST /attempts/{id}/submit-answer`, `POST /attempts/{id}/finish`
- recommendations: `GET /recommendations/me`
- analytics: `GET /analytics/dashboard`, `GET /analytics/course-progress`, `GET /analytics/problem-topics`, `GET /analytics/learners/{id}`

## Database schema overview

Core tables:
- tenants
- roles
- users
- memberships
- groups
- group_members
- courses
- lessons
- enrollments
- course_assignments
- topics
- tests
- questions
- answer_options
- question_topics
- attempts
- attempt_answers
- results
- recommendations
- refresh_tokens
- audit_logs
- notification_deliveries

## Seed data

`backend/scripts/seed_demo.py` creates:
- 2 tenants
- 4 roles
- 20+ users
- 500+ total records across content, enrollments, questions, attempts, results, and recommendations

## Tests

```bash
cd backend
pytest

cd ../web
npm test

cd ../mobile
flutter test
```

Backend tests cover tenant isolation, role access, adaptive difficulty bounds, recommendations, learner completion flow, and admin analytics access.

### Production smoke check for assignments endpoint

Before shipping a backend release, verify that assignment routes are reachable in the deployed environment:

```bash
python backend/scripts/smoke_assignments_endpoint.py \
  --base-url https://<your-host>/api/v1 \
  --token <staff-or-learner-access-token> \
  --tenant-code <tenant-code>
```

The command must print `OK` and return exit code `0`. Fail the release if it returns non-zero.

## Thesis-ready notes

- Adaptive algorithm starts at baseline difficulty `3`.
- Correct answer raises target difficulty by `+1`, incorrect lowers by `-1`.
- Weak-topic scoring grows from incorrect and slow answers.
- Recommendations map weak topics to revision advice.
- Architecture remains monolithic for explainability, but clearly modularized by subsystem.
