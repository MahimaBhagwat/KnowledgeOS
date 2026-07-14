# KnowledgeOS - System Architecture

# Part 2 — Module-Level Architecture

---

# 11. Module-Level Architecture

KnowledgeOS follows a **feature-based modular architecture** rather than a traditional layer-based folder structure.

Instead of grouping files by type (controllers, services, models), the project groups them by business capability.

Each feature owns its APIs, business logic, validation schemas, database models, and utilities.

This approach provides:

* Better scalability
* Easier navigation
* High cohesion
* Loose coupling
* Independent feature development
* Easier testing

---

# 12. Frontend Architecture

The frontend is organized around **feature modules**.

Each module contains everything required to implement a specific feature.

```text
src/

├── app/
│
├── assets/
│
├── components/
│
├── features/
│   ├── auth/
│   ├── home/
│   ├── documents/
│   ├── folders/
│   ├── notes/
│   ├── chat/
│   ├── insights/
│   ├── profile/
│   └── settings/
│
├── layouts/
│
├── hooks/
│
├── api/
│
├── services/
│
├── store/
│
├── routes/
│
├── types/
│
├── utils/
│
├── styles/
│
└── main.tsx
```

---

# 13. Frontend Module Responsibilities

## app/

Application bootstrap.

Contains

* Providers
* Theme
* Global configuration

---

## assets/

Static resources.

Examples

* Images
* Icons
* Fonts

---

## components/

Reusable UI components shared across multiple features.

Examples

* Buttons
* Cards
* Sidebar
* Navbar
* Breadcrumbs
* Modal
* Dialog
* Toast
* Loader
* Skeleton
* Search Bar

---

## features/

Contains all business features.

Every feature owns

* Pages
* Components
* Hooks
* API Calls
* Types
* Utilities

Example

```text
features/

chat/

├── components/
├── pages/
├── hooks/
├── api/
├── types/
└── utils/
```

---

## layouts/

Application layouts.

Examples

* Auth Layout
* Dashboard Layout

---

## hooks/

Global reusable hooks.

Examples

* useDebounce
* useLocalStorage
* useTheme

---

## api/

API client configuration.

Responsibilities

* Axios instance
* Authentication interceptor
* Request handling

---

## services/

Frontend-only services.

Examples

* File upload helper
* Download helper
* Markdown export
* PDF export

---

## store/

Global application state.

Stores

* User
* Theme
* Authentication
* UI preferences

---

## routes/

Application routing configuration.

---

## types/

Global TypeScript interfaces.

---

## utils/

Shared utility functions.

---

## styles/

Global styling.

---

# 14. Backend Architecture

The backend follows the same feature-based philosophy.

```text
backend/

app/

├── api/
│
├── auth/
│
├── users/
│
├── documents/
│
├── folders/
│
├── notes/
│
├── chat/
│
├── insights/
│
├── rag/
│
├── agents/
│
├── embeddings/
│
├── storage/
│
├── database/
│
├── core/
│
├── middleware/
│
├── models/
│
├── schemas/
│
├── utils/
│
└── main.py
```

---

# 15. Backend Module Responsibilities

## api/

API routing layer.

Responsibilities

* Route registration
* API versioning
* Request dispatching

---

## auth/

Authentication and authorization.

Responsibilities

* Login
* Google OAuth
* JWT validation
* Protected routes

---

## users/

User management.

Responsibilities

* Profile
* Preferences
* Account settings

---

## documents/

Document lifecycle.

Responsibilities

* Upload
* Delete
* Rename
* Metadata
* Processing status

---

## folders/

Folder management.

Responsibilities

* Create
* Rename
* Delete
* Move documents

---

## notes/

Quick Notes management.

Responsibilities

* Create
* Update
* Delete
* Convert pasted text into managed documents

---

## chat/

Conversation management.

Responsibilities

* Chat history
* Conversation titles
* Export
* Share
* Memory integration

---

## insights/

Knowledge intelligence.

Responsibilities

* Recommendations
* Learning insights
* Knowledge gaps
* Statistics

---

## rag/

Knowledge retrieval.

Responsibilities

* Hybrid retrieval
* Context ranking
* Context compression
* Citation generation

---

## agents/

AI workflow logic.

Responsibilities

* Planner Agent
* Reviewer Agent
* Workflow state
* Retry loop

---

## embeddings/

Embedding generation.

Responsibilities

* Chunk embeddings
* Embedding provider abstraction
* Batch generation

---

## storage/

File storage abstraction.

Responsibilities

* Upload
* Download
* Delete
* Signed URLs

---

## database/

Database configuration.

Responsibilities

* PostgreSQL
* ChromaDB
* Session management

---

## core/

Application configuration.

Contains

* Settings
* Environment variables
* Constants

---

## middleware/

Cross-cutting concerns.

Examples

* Authentication
* Logging
* Rate limiting
* Exception handling

---

## models/

Database models.

---

## schemas/

Request and response validation.

---

## utils/

Shared helper functions.

---

# 16. AI Architecture

The AI subsystem is intentionally separated into two complementary layers.

---

## AI Orchestration Layer

Framework

**LangGraph**

Responsibilities

* Stateful workflow execution
* Planner Agent
* Reviewer Agent
* Workflow routing
* Retry management
* Conversation state
* Conditional execution
* Fast-path routing
* Long-running workflow coordination

LangGraph acts as the "brain" that coordinates every AI interaction.

---

## Knowledge Layer

Framework

**LlamaIndex**

Responsibilities

* Document ingestion
* File parsing
* Chunking
* Metadata extraction
* Index creation
* Hybrid retrieval
* Context reranking
* Context assembly

LlamaIndex acts as the "knowledge engine" responsible for preparing and retrieving information.

---

## Language Model Layer

The system interacts with an abstract **LLM Provider Interface**.

Supported providers may include

* Google Gemini
* OpenAI GPT
* Anthropic Claude
* Ollama (local models)

The remainder of the application is independent of the chosen provider.

---

## Embedding Layer

A dedicated embedding provider generates vector representations of document chunks.

The embedding provider is abstracted so that different embedding models can be used without affecting downstream components.

---

# 17. Storage Architecture

KnowledgeOS separates storage responsibilities across specialized systems.

## PostgreSQL

Stores structured application data.

Examples

* Users
* Chats
* Folders
* Document metadata
* Settings
* Processing status

---

## ChromaDB

Stores vector embeddings for semantic retrieval.

Each user's embeddings are logically isolated.

---

## Supabase Storage

Stores original uploaded files.

Documents remain in their original format for viewing, downloading, and future reprocessing.

---

# 18. Inter-Module Communication

Modules communicate through clearly defined service interfaces.

Direct dependencies between unrelated modules should be avoided.

Typical communication flow:

```text
Frontend
    │
    ▼
API Router
    │
    ▼
Feature Service
    │
    ├── Database
    ├── Storage
    ├── AI Layer
    └── External Services
```

This separation keeps modules independent and improves maintainability.

---

# 19. Module-Level Summary

KnowledgeOS adopts a feature-oriented architecture across both the frontend and backend.

Each feature owns its implementation while shared infrastructure remains centralized.

The AI subsystem is divided into an orchestration layer (LangGraph) and a knowledge layer (LlamaIndex), enabling complex stateful workflows without tightly coupling retrieval logic to agent execution.

This modular design improves readability, simplifies onboarding for new contributors, and allows the application to evolve as additional AI capabilities and integrations are introduced.
