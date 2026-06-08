from __future__ import annotations

import argparse
import asyncio
import math
import random
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


PASSWORD = "Password123!"
TENANT_CODE = "acme"
LEARNER_EMAILS = [f"learner{i}@acme.example.com" for i in range(1, 9)]
STAFF_EMAILS = ["teacher@acme.example.com", "admin@acme.example.com"]


@dataclass(frozen=True)
class Session:
    email: str
    role: str
    token: str


@dataclass
class Sample:
    name: str
    method: str
    status_code: int
    elapsed_ms: float


@dataclass
class UserState:
    session: Session
    courses: list[dict[str, Any]] = field(default_factory=list)
    tests: list[dict[str, Any]] = field(default_factory=list)
    lessons_by_course: dict[int, list[dict[str, Any]]] = field(default_factory=dict)


class LoadClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self.samples: list[Sample] = []
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self.client.aclose()

    async def request(
        self,
        state: UserState | None,
        method: str,
        path: str,
        *,
        name: str | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        headers = {"X-Tenant-Code": TENANT_CODE}
        if state is not None:
            headers["Authorization"] = f"Bearer {state.session.token}"
        started = time.perf_counter()
        status_code = 0
        try:
            response = await self.client.request(method, path, headers=headers, json=json)
            status_code = response.status_code
            if response.status_code >= 400:
                return None
            if response.content:
                return response.json()
            return {}
        except Exception:
            return None
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            async with self._lock:
                self.samples.append(Sample(name or path, method, status_code, elapsed_ms))

    async def login(self, email: str, role: str) -> Session | None:
        payload = await self.request(
            None,
            "POST",
            "/auth/login",
            name="auth.login",
            json={"email": email, "password": PASSWORD},
        )
        if not payload or "access_token" not in payload:
            return None
        return Session(email=email, role=role, token=payload["access_token"])


async def warm_user_state(client: LoadClient, session: Session) -> UserState:
    state = UserState(session=session)
    courses = await client.request(state, "GET", "/courses", name="courses.list")
    state.courses = courses if isinstance(courses, list) else []
    tests = await client.request(state, "GET", "/tests", name="tests.list")
    state.tests = tests if isinstance(tests, list) else []
    for course in state.courses[:3]:
        course_id = course.get("id")
        if isinstance(course_id, int):
            lessons = await client.request(state, "GET", f"/lessons?course_id={course_id}", name="lessons.list")
            state.lessons_by_course[course_id] = lessons if isinstance(lessons, list) else []
    return state


async def learner_step(client: LoadClient, state: UserState) -> None:
    action = random.choices(
        ["courses", "outline", "lesson", "progress", "history", "recommendations", "test"],
        weights=[18, 18, 22, 10, 12, 10, 10],
        k=1,
    )[0]
    if action == "courses" or not state.courses:
        courses = await client.request(state, "GET", "/courses", name="learner.courses")
        if isinstance(courses, list):
            state.courses = courses
        return

    course = random.choice(state.courses)
    course_id = course.get("id")
    if not isinstance(course_id, int):
        return

    if action == "outline":
        await client.request(state, "GET", f"/courses/{course_id}/outline", name="learner.course_outline")
    elif action == "lesson":
        lessons = state.lessons_by_course.get(course_id)
        if not lessons:
            lessons = await client.request(state, "GET", f"/lessons?course_id={course_id}", name="learner.lessons")
            state.lessons_by_course[course_id] = lessons if isinstance(lessons, list) else []
        if state.lessons_by_course.get(course_id):
            lesson_id = random.choice(state.lessons_by_course[course_id]).get("id")
            if isinstance(lesson_id, int):
                await client.request(state, "GET", f"/lessons/{lesson_id}/player", name="learner.lesson_player")
    elif action == "progress":
        lessons = state.lessons_by_course.get(course_id) or []
        if lessons:
            lesson_id = random.choice(lessons).get("id")
            if isinstance(lesson_id, int):
                await client.request(state, "POST", f"/lessons/{lesson_id}/progress", name="learner.lesson_progress")
    elif action == "history":
        await client.request(state, "GET", f"/attempts/history?course_id={course_id}&page=1&page_size=10", name="learner.attempt_history")
    elif action == "recommendations":
        await client.request(state, "GET", "/recommendations/me", name="learner.recommendations")
    elif action == "test":
        tests = [item for item in state.tests if item.get("course_id") == course_id]
        if tests:
            test_id = random.choice(tests).get("id")
            if isinstance(test_id, int):
                await client.request(state, "POST", f"/tests/{test_id}/start", name="learner.test_start")


async def staff_step(client: LoadClient, state: UserState) -> None:
    action = random.choices(
        ["dashboard", "course_progress", "problem_topics", "timeline", "courses", "users", "tests", "questions"],
        weights=[16, 14, 12, 10, 18, 12, 12, 6],
        k=1,
    )[0]
    if action == "dashboard":
        await client.request(state, "GET", "/analytics/dashboard", name="staff.analytics_dashboard")
    elif action == "course_progress":
        await client.request(state, "GET", "/analytics/course-progress", name="staff.course_progress")
    elif action == "problem_topics":
        await client.request(state, "GET", "/analytics/problem-topics", name="staff.problem_topics")
    elif action == "timeline":
        await client.request(state, "GET", "/analytics/timeline?period=30d", name="staff.timeline")
    elif action == "courses":
        courses = await client.request(state, "GET", "/courses", name="staff.courses")
        if isinstance(courses, list):
            state.courses = courses
    elif action == "users":
        await client.request(state, "GET", "/users", name="staff.users")
    elif action == "tests":
        tests = await client.request(state, "GET", "/tests", name="staff.tests")
        if isinstance(tests, list):
            state.tests = tests
    elif action == "questions" and state.tests:
        test_id = random.choice(state.tests).get("id")
        if isinstance(test_id, int):
            await client.request(state, "GET", f"/questions?test_id={test_id}&page=1&page_size=20", name="staff.questions")


async def virtual_user(client: LoadClient, template: UserState, deadline: float, think_time: tuple[float, float]) -> None:
    state = UserState(
        session=template.session,
        courses=list(template.courses),
        tests=list(template.tests),
        lessons_by_course={key: list(value) for key, value in template.lessons_by_course.items()},
    )
    while time.perf_counter() < deadline:
        if state.session.role == "learner":
            await learner_step(client, state)
        else:
            await staff_step(client, state)
        await asyncio.sleep(random.uniform(*think_time))


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = math.ceil((percent / 100) * len(ordered)) - 1
    return ordered[max(0, min(index, len(ordered) - 1))]


def summarize(samples: list[Sample], duration: float) -> dict[str, Any]:
    latencies = [sample.elapsed_ms for sample in samples]
    errors = [sample for sample in samples if sample.status_code >= 400 or sample.status_code == 0]
    return {
        "requests": len(samples),
        "rps": len(samples) / duration if duration else 0,
        "avg_ms": statistics.mean(latencies) if latencies else 0,
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "max_ms": max(latencies) if latencies else 0,
        "errors": len(errors),
        "error_rate": len(errors) / len(samples) if samples else 0,
    }


async def run_stage(client: LoadClient, templates: list[UserState], users: int, duration: int, think_time: tuple[float, float]) -> dict[str, Any]:
    client.samples.clear()
    deadline = time.perf_counter() + duration
    tasks = [
        asyncio.create_task(virtual_user(client, templates[index % len(templates)], deadline, think_time))
        for index in range(users)
    ]
    started = time.perf_counter()
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - started
    summary = summarize(list(client.samples), elapsed)
    summary["users"] = users
    summary["duration_s"] = elapsed
    return summary


async def main() -> None:
    parser = argparse.ArgumentParser(description="Load test Coursum LMS API with mobile and web panel user flows.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--users", default="10,25,50,75,100", help="Comma-separated virtual user stages.")
    parser.add_argument("--duration", type=int, default=30, help="Stage duration in seconds.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--think-min", type=float, default=0.2)
    parser.add_argument("--think-max", type=float, default=1.2)
    args = parser.parse_args()

    stages = [int(value.strip()) for value in args.users.split(",") if value.strip()]
    client = LoadClient(args.base_url, args.timeout)
    try:
        sessions: list[Session] = []
        for email in LEARNER_EMAILS:
            session = await client.login(email, "learner")
            if session:
                sessions.append(session)
        for email in STAFF_EMAILS:
            session = await client.login(email, "staff")
            if session:
                sessions.append(session)
        if not sessions:
            raise SystemExit("No demo sessions could log in. Seed demo data and check the API URL.")

        templates = await asyncio.gather(*(warm_user_state(client, session) for session in sessions))
        print(f"Loaded {len(templates)} session templates from {args.base_url}")
        print("users,requests,rps,avg_ms,p95_ms,p99_ms,max_ms,errors,error_rate")

        stable_users = 0
        for users in stages:
            summary = await run_stage(client, templates, users, args.duration, (args.think_min, args.think_max))
            print(
                f"{summary['users']},{summary['requests']},{summary['rps']:.2f},"
                f"{summary['avg_ms']:.1f},{summary['p95_ms']:.1f},{summary['p99_ms']:.1f},"
                f"{summary['max_ms']:.1f},{summary['errors']},{summary['error_rate']:.3%}",
                flush=True,
            )
            if summary["error_rate"] <= 0.01 and summary["p95_ms"] <= 1000:
                stable_users = users

        print(f"Estimated stable concurrency: {stable_users} users by p95<=1000ms and errors<=1%.")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
