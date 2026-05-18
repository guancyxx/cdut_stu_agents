# Spec 008 — Register: optional email + optional student number

## Background
Users report that register form labels email as optional, but submit fails when email is empty. Also, register form lacks a student number input even though profile supports displaying student number.

## Goals
1) Keep email truly optional during registration.
2) Add optional student number field to register form and persist it.

## Scope
- Frontend register validator and register form fields.
- Backend register/profile payload handling in compat OJ API.
- Local user model column compatibility for student number.

## Non-goals
- Enforce student number format beyond basic trimming and max length.
- Add separate profile-edit API.

## Design
- Frontend:
  - `validateRegisterPayload`: only validate email format when email is non-empty.
  - include `student_number` in register payload (optional).
  - add register input `学号（选填）`.
- Backend:
  - `local_users` model adds nullable `student_number` column.
  - startup migration via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS student_number VARCHAR(64)`.
  - `/api/register` accepts optional `student_number` and stores it.
  - `/api/profile` returns `student_number`.

## Acceptance Criteria
1) Register succeeds with empty email.
2) Register succeeds with empty student number.
3) Register with provided student number persists and profile returns it.
4) Invalid non-empty email still returns validation error.

## Verification (Docker)
- Build `ai-agent-lite` and `vue-ai-chat`.
- API probes:
  - register without email => success
  - register with student_number => success
  - profile returns student_number
  - register with invalid email => error
