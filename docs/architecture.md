# Architecture Notes

## System context

The project is a monorepo containing:
- FastAPI backend as the source of truth
- React web panel for admins and teachers
- Flutter mobile client for learners

All clients communicate with the backend over REST API and rely on the same RBAC and tenant context rules.

## Backend subsystems

- `auth`: JWT login, refresh tokens, password hashing
- `tenants`: tenant resolution, current tenant lookup, tenant-safe membership checks
- `users`: tenant user management and role assignment through memberships
- `courses` and `lessons`: content management and progress tracking
- `tests`: adaptive attempt lifecycle
- `adaptive`: next-question selection and difficulty changes
- `recommendations`: weak-topic remediation output
- `analytics`: dashboard, course progress, learner detail
- `audit`: security and business event logging
- `notifications`: mockable external integration

## Multi-tenant isolation

Tenant isolation is enforced in three layers:

1. Request layer: tenant resolved from subdomain or `X-Tenant-Code` in demo mode.
2. Authorization layer: user must have active membership in the resolved tenant.
3. Data layer: all tenant-bound queries filter by `tenant_id`.

This combination is simple enough for thesis defense and strong enough to demonstrate practical SaaS isolation.

## Adaptive testing algorithm

- Every question has a discrete difficulty from `1` to `5`.
- Attempt starts from test baseline difficulty.
- Correct answer moves target difficulty up by one.
- Incorrect answer moves target difficulty down by one.
- Next question is chosen among unasked questions closest to current target difficulty.
- Weak topics accumulate penalties from wrong and slow answers.
- Final result stores score, weak topics, and generated recommendations.
