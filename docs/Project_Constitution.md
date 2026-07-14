# KnowledgeOS Project Constitution

Version: 1.0

This document defines the immutable engineering principles, coding standards, and development rules for KnowledgeOS.

Every implementation must comply with these rules unless explicitly overridden by me.

---

# 1. Core Principle

KnowledgeOS is a production-grade AI-powered Personal Knowledge Operating System.

Every implementation should prioritize:

- Correctness
- Readability
- Maintainability
- Scalability
- Security
- Extensibility

Never optimize for writing fewer lines of code.

Always optimize for long-term maintainability.

---

# 2. Single Source of Truth

The project documentation is the authority.

Priority order:

00_Product_Discovery.md

↓

01_Product.md

↓

02_UI.md

↓

03_Architecture.md

↓

04_Database.md

↓

05_APIs.md

↓

06_Roadmap.md

↓

Project_Constitution.md

If implementation conflicts occur, follow the higher-priority document.

Never invent undocumented features.

---

# 3. General Engineering Rules

Always write production-quality code.

Never write prototype code.

Never write demo code.

Never write placeholder implementations.

Avoid shortcuts.

Avoid hacks.

Avoid duplicated logic.

Every implementation should be deployable.

---

# 4. Architecture Rules

Follow Clean Architecture.

Never mix responsibilities.

Separate:

Presentation

↓

API

↓

Services

↓

Repositories

↓

Database

↓

AI

↓

Utilities

Business logic must never exist inside:

- API Routes
- React Components
- Database Models

---

# 5. Backend Standards

Language

Python

Framework

FastAPI

Requirements

- Type hints everywhere
- PEP8
- Async where appropriate
- Dependency Injection
- Repository Pattern
- Service Layer
- Centralized exception handling

Never access the database directly from API routes.

Always use Services.

---

# 6. Frontend Standards

Language

TypeScript

Framework

React

Requirements

- Functional Components only
- Strict typing
- Reusable components
- Custom hooks
- Component composition
- Feature-based organization

Avoid large components.

Prefer multiple smaller reusable components.

---

# 7. Database Standards

Database

PostgreSQL

ORM

SQLAlchemy

Migration

Alembic

Requirements

Never execute raw SQL unless necessary.

Every schema change must be introduced through a migration.

Never modify production tables manually.

---

# 8. Naming Conventions

## Python

Variables

snake_case

Functions

snake_case

Classes

PascalCase

Constants

UPPER_SNAKE_CASE

---

## React

Components

PascalCase

Hooks

useSomething

Props

camelCase

Files

PascalCase.tsx

---

## Database

Tables

snake_case

Columns

snake_case

Indexes

idx_table_column

Foreign Keys

fk_child_parent

Unique Constraints

uq_table_column

---

## APIs

Use plural nouns.

Examples

/api/v1/documents

/api/v1/chat

/api/v1/insights

Never use verbs inside endpoints.

---

# 9. Folder Organization

Always follow feature-based architecture.

Backend

```text
app/

api/

core/

models/

schemas/

repositories/

services/

workers/

ai/

middleware/

utils/
```

Frontend

```text
src/

components/

pages/

layouts/

hooks/

contexts/

services/

types/

utils/

assets/
```

Never create deeply nested folders without necessity.

---

# 10. API Rules

Always:

Validate requests.

Validate responses.

Return consistent response objects.

Use proper HTTP status codes.

Implement pagination.

Implement filtering.

Implement sorting.

Never expose internal errors.

---

# 11. Database Rules

Follow 04_Database.md exactly.

Respect:

Soft Delete

Versioning

Folder hierarchy

Triggers

Indexes

Constraints

Enums

Document ownership

User isolation

Never change schema without approval.

---

# 12. AI Rules

Follow 03_Architecture.md exactly.

Pipeline:

Intent Detection

↓

Planner

↓

Query Rewriter

↓

Hybrid Retrieval

↓

Ranking

↓

Prompt Builder

↓

LLM

↓

Reviewer

↓

Formatter

↓

Streaming

↓

Memory Update

Never bypass the Planner.

Never bypass the Reviewer.

Memory updates must remain asynchronous.

---

# 13. UI Rules

Follow 02_UI.md exactly.

Never redesign UI.

Never change navigation.

Never change layouts.

Never change colors.

Use the finalized palette.

---

# 14. Security Rules

Every endpoint must:

Authenticate

Authorize

Validate

Log

Protect against invalid input

Never trust frontend validation.

Always validate on the backend.

Never expose secrets.

Never expose API keys.

Never log passwords.

Never log tokens.

---

# 15. Logging Rules

Use structured logging.

Log:

Errors

Warnings

Important events

Performance metrics

Never log:

Passwords

JWT

API Keys

Sensitive user data

Raw document content

---

# 16. Error Handling

Always raise meaningful exceptions.

Never return generic stack traces.

Every error should include:

Code

Message

HTTP Status

Follow the standardized API error format.

---

# 17. Testing Rules

Every feature requires:

Unit Tests

Integration Tests

Manual Testing

No feature is complete without testing.

---

# 18. Git Rules

Branch naming:

feature/document-upload

feature/chat

bugfix/sidebar

fix/vector-search

Commit style:

feat:

fix:

refactor:

docs:

test:

style:

Example

feat: implement document upload API

---

# 19. Performance Rules

Prefer:

Pagination

Lazy loading

Streaming

Caching

Background workers

Batch processing

Avoid:

N+1 queries

Repeated embedding generation

Repeated API calls

Duplicate retrieval

---

# 20. Documentation Rules

Whenever implementation changes:

Update documentation.

Never allow documentation to become outdated.

---

# 21. Decision Rules

If implementation requires an undocumented decision:

DO NOT guess.

Instead:

Explain available options.

Recommend the best production solution.

Wait for confirmation.

---

# 22. Code Generation Rules

Always generate complete files.

Never generate incomplete snippets unless requested.

Never write:

TODO

Coming Soon

Placeholder

Mock implementation

If a feature is generated, implement it completely.

---

# 23. Development Workflow

For every implementation step:

1. Explain the goal.

2. List files to be created.

3. List files to be modified.

4. Generate complete code.

5. Explain how to run.

6. Explain how to test.

7. Wait for approval.

Never jump to the next roadmap phase automatically.

---

# 24. Definition of Done

A feature is complete only if:

✓ Code compiles

✓ No lint errors

✓ Types are correct

✓ Validation exists

✓ Error handling exists

✓ Logging exists

✓ Tests pass

✓ APIs documented

✓ UI integrated

✓ Security verified

✓ Documentation updated

---

# 25. Final Rule

Build KnowledgeOS exactly as specified.

Improve implementation quality where appropriate.

Never redesign the product.

Never remove existing functionality.

Never make architectural changes without explicit approval.

When in doubt, ask before implementing.