---
stepsCompleted:
  - step-01-init
  - step-02-context
  - step-03-starter
  - step-04-decisions
  - step-05-patterns
  - step-06-structure
  - step-07-validation
  - step-08-complete
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief-Modu.md
workflowType: architecture
project_name: Modu
user_name: Willi
date: '2026-05-20'
status: complete
completedAt: '2026-05-20'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
31 FRs across 9 capability domains. Core architectural flows: (1) Document ingestion & AI parsing, (2) Design generation with human-in-the-loop review, (3) Code generation constrained by MISRA/ASIL templates, (4) Multi-layer testing (static MISRA scan, dynamic unit test with Mock/Stub, security audit), (5) Traceable release packaging to Git + Polarion.

**Non-Functional Requirements:**
14 NFRs drive key architectural decisions:
- Performance: Page load ≤ 3s, AI analysis ≤ 60s, full pipeline ≤ 10 min
- Reliability: ≥ 99.5% availability, network-fault tolerance, form auto-save
- Security: HTTPS/TLS, no sensitive data in frontend storage, AI call auditing, data desensitization
- Maintainability: Template versioning, smooth upgrade with schema migration
- Usability: WCAG 2.1 AA, browser compatibility, responsive for 1366×768+

**Scale & Complexity:**
- Primary domain: Full-stack web application (enterprise B2B)
- Complexity level: Enterprise / High
- Estimated architectural components: 8–10 major subsystems

### Technical Constraints & Dependencies

- **Deployment:** Private network, no external internet dependency except AI API calls
- **Target Platform:** Infineon AURIX TC38x + Tasking 6.3.1 compiler
- **External Integrations:** Siemens Polarion ALM, Git VCS, AD/LDAP, third-party LLM APIs
- **Compliance:** ASPICE Level 2, ISO 26262 (ASIL-A to D), ISO 21434, MISRA C:2012
- **AI Architecture:** Pluggable LLM backend; audit gateway mandatory

### Cross-Cutting Concerns Identified

1. **Audit & Traceability:** Every artifact must carry bidirectional Polarion trace IDs; audit logs ≥ 7 years for review records, ≥ 2 years for AI API calls
2. **Compliance-as-Code:** ASIL grade determines test coverage thresholds, template strictness, and documentation depth — must be configurable per tenant
3. **AI Reliability:** Hallucination mitigation, confidence scoring (OCR), fallback when AI output violates compliance gates
4. **Multi-Tenancy:** Data isolation, per-tenant template/code-template/compliance policy configuration
5. **Toolchain Integration:** External compiler (Tasking), static analyzer, simulator for TC38x target environment

## Starter Template Evaluation

### Primary Technology Domain

Full-stack enterprise web application (B2B, private deployment) with heavy AI orchestration, document processing, and external toolchain integration.

### Evaluation Note

Modu is a highly customized enterprise platform (AI orchestration + multi-tenancy + external toolchain integration). No standard off-the-shelf starter template directly applies. This evaluation defines the **layered technology stack foundation** instead.

### Selected Technology Stack

**Frontend Layer:**
- React 19 + TypeScript
- Ant Design (enterprise component library)
- react-pdf / @react-pdf-viewer (document preview)
- Zustand or Redux Toolkit (state management for complex form flows)

**Backend API Layer:**
- Python + FastAPI (async-native, OpenAPI auto-generation)
- SQLAlchemy 2.0 + Alembic (ORM and migrations)
- Pydantic (validation and settings management)

**Asynchronous Task Layer:**
- Celery + Redis (task queue, retry, scheduling)
- Flower (task monitoring dashboard)

**Database Layer:**
- PostgreSQL 16 (relational core + JSONB for flexible configs)

**AI Orchestration Layer:**
- LiteLLM (unified LLM API proxy, multi-model support)
- Custom constraint engine (MISRA/ASIL compliance filtering on AI output)
- Audit gateway middleware (logging, desensitization)

**External Integration Layer:**
- Polarion REST API adapter
- GitPython / libgit2 (Git operations)
- python-ldap (AD/LDAP authentication)
- Docker-based Tasking compiler invocation

**Deployment Layer:**
- Docker + Docker Compose (private deployment standard)
- Nginx (reverse proxy, HTTPS termination, static file serving)
- MinIO (optional S3-compatible object storage for artifacts)

### Rationale for Selection

| Decision | Why |
|----------|-----|
| React + Ant Design | Rich ecosystem for complex document processing UI; enterprise-grade form/table/step components match pipeline interactions |
| Python + FastAPI | AI/LLM SDK ecosystem (OpenAI, Anthropic, LangChain) is the decisive factor; FastAPI provides async-native performance and auto-generated API docs |
| Celery + Redis | Pipeline tasks (parse → design → generate → compile → test) naturally require queue, retry, and monitoring |
| PostgreSQL | Traceability chain is deeply relational; JSONB supports flexible tenant configs and template versioning |
| LiteLLM | Provides unified interface for pluggable LLM backends (OpenAI, Claude, local models) without vendor lock-in |
| Docker Compose | Single-server deployment standard for private environments; customer IT teams are familiar with it |

### Rejected Alternatives

| Alternative | Why Rejected |
|-------------|--------------|
| Node.js backend | AI library ecosystem is significantly weaker; calling Python subprocess adds complexity |
| Vue frontend | React has more mature document processing libraries (PDF viewers, diff editors) for this specific domain |
| MongoDB | Traceability matrix requires complex multi-table JOINs and transactions; document database is a burden here |
| Kubernetes | Overkill for private deployment; most customers do not have K8s operations capability |
| Microservices | Increases operational complexity for private deployment; modular monolith provides better code isolation with simpler ops |

### Key Architectural Decisions Pre-Loaded

1. **Modular Monolith:** Code organized by domain modules (Document, Design, CodeGen, Test, Release) but deployed as a single service to reduce private-deployment operational burden.
2. **AI Service as Independent Container:** AI inference may consume significant memory/GPU resources; isolation prevents impacting main API service stability.
3. **Compiler/Test Execution in Sandboxed Environment:** Tasking compiler licensing and TC38x simulator require specific host environment; executed in isolated Docker containers or dedicated worker nodes.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Multi-tenant data isolation model
- Authentication and authorization strategy
- AI service deployment topology
- External toolchain integration architecture

**Important Decisions (Shape Architecture):**
- API design patterns and error handling standards
- Frontend state management and component architecture
- Caching and file storage strategy
- Monitoring and alerting approach

**Deferred Decisions (Post-MVP):**
- Horizontal scaling strategy (current vertical scaling sufficient)
- Advanced analytics and BI reporting
- Custom plugin/IDE integration architecture

### Data Architecture

**Database:** PostgreSQL 16 with shared schema + `tenant_id` + Row-Level Security (RLS)

**Rationale:**
- Modu targets enterprise customers with 10–50 tenants per instance; schema-per-tenant introduces unnecessary connection pool complexity
- PostgreSQL RLS provides defense-in-depth: even if application layer misses tenant filtering, database enforces isolation
- Backup strategy: partition exports by `tenant_id`

**Data Model Strategy:**
- Document metadata stored in PostgreSQL; file binaries stored on local Docker Volume (default) or MinIO (optional upgrade)
- Traceability chain: independent tables per Work Item type (Requirement, Design, Code, Test) with `trace_source_id` / `trace_target_id` many-to-many relationships
- Template versioning: JSONB columns with `version`, `effective_from`, `effective_to` fields

**Migration:** Alembic (SQLAlchemy standard)

**Caching:** Redis (dual purpose as Celery broker and application cache). Cached: Polarion project config, LDAP org structure, AI prompt templates. Not cached: document parse results, AI-generated artifacts.

### Authentication & Security

**Primary Authentication:** AD/LDAP integration (FR-REQ-029) using standard LDAP/LDAPS protocol
**Fallback Authentication:** Local admin account for initial platform setup
**Session Management:** JWT (short-lived access token + long-lived refresh token)

**Authorization:** RBAC with tenant isolation
- Roles: Platform Admin, Tenant Admin, Engineer, Quality Auditor, Read-Only User
- Permission matrix: Role × Tenant × Action
- Sensitive operations (release, config changes) require audit logging with secondary confirmation

**AI API Security:**
- Dedicated audit gateway intercepts all LLM requests
- Desensitization middleware filters chip models, customer names, internal architecture details
- Full request/response persisted to audit log table (retention ≥ 2 years)
- API keys configured by platform admin, never exposed to end users

### API & Communication Patterns

**API Style:** REST (FastAPI native), resource-oriented endpoints:
- `/documents`, `/designs`, `/code-modules`, `/test-runs`, `/releases`, `/admin/tenants`

**Real-Time Communication:** WebSocket for pipeline progress push notifications; fallback to long polling if enterprise firewall blocks WebSocket

**Error Handling Standard:**
```json
{
  "error_code": "DESIGN_REVIEW_BLOCKED",
  "message": "设计评审未通过，无法进入代码生成阶段",
  "detail": { "review_node": "FR-REQ-007", "status": "rejected" },
  "trace_id": "uuid-for-debugging"
}
```

**Rate Limiting:**
- AI API layer: per-tenant token budget throttling
- General API: per-user IP + user ID combination
- Implementation: Redis-backed counter middleware

### Frontend Architecture

**State Management:** Zustand (modular stores: AuthStore, PipelineStore, DocumentStore, ConfigStore)

**Component Architecture:** Feature-based directory structure
```
src/
  features/
    documents/     → upload, preview, parse status
    design/        → review, edit, approval workflow
    pipeline/      → execution status, logs, artifacts
    admin/         → tenant config, Polarion/LDAP settings
  components/      → shared UI primitives
  hooks/           → reusable logic
  api/             → TanStack Query wrappers
```

**Server State:** TanStack Query (React Query) for document lists, pipeline status, test reports — automatic caching, background refetch, optimistic updates

**Routing:** React Router v7

### Infrastructure & Deployment

**Deployment Topology (Docker Compose):**
```
Nginx (HTTPS / Static Files)
    ├── React SPA (frontend)
    ├── FastAPI (main API)
    └── AI Worker (Celery worker for LLM calls)
    
Shared Services:
    ├── PostgreSQL 16
    ├── Redis
    └── Tasking Compiler (Docker or host-mounted)
```

**File Storage:** Local Docker Volume (default); MinIO as optional S3-compatible upgrade

**Logging:** Structured JSON logs with tenant tagging

**Monitoring:** Prometheus + Grafana (optional for MVP); email/企微/钉钉 alerts per FR-REQ-031

### Decision Impact Analysis

**Implementation Sequence:**
1. Database schema + migration setup (tenant model, RLS)
2. Auth module (LDAP integration, JWT, RBAC)
3. Document upload & parse service (async Celery task)
4. AI orchestration layer (LiteLLM adapter, prompt templates, audit gateway)
5. Design generation & review workflow
6. Code generation with MISRA constraints
7. Test execution pipeline (static + dynamic + security)
8. Release packaging & Polarion/Git integration
9. Admin configuration UI
10. Monitoring and alerting

**Cross-Component Dependencies:**
- Auth module must be implemented before any business feature (tenant isolation is foundational)
- AI orchestration layer must be ready before Design/CodeGen features
- Document parse service feeds into Design generation, which feeds into Code generation, forming a linear pipeline dependency
- Polarion/Git adapters are leaf nodes (only Release feature depends on them)

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 6 areas where AI agents could make different choices — naming conventions, project structure, API response formats, event naming, error handling, loading state management.

### Naming Patterns

**Database Naming Conventions:**
- Table names: snake_case, plural nouns (`code_modules`, `test_cases`, `review_records`)
- Column names: snake_case (`created_at`, `tenant_id`, `polarion_work_item_id`)
- Foreign keys: `{table}_id` (`module_id`, `design_id`)
- Indexes: `idx_{table}_{column}` (`idx_code_modules_tenant_id`)
- SQLAlchemy model classes: PascalCase, singular (`CodeModule`, `TestCase`)

**API Naming Conventions:**
- Path segments: kebab-case, plural nouns (`/code-modules`, `/test-runs`, `/design-reviews`)
- Path parameters: kebab-case (`/code-modules/{module-id}`)
- Query parameters: snake_case (`?tenant_id=123&status=pending`)
- Python route handler functions: snake_case (`get_code_modules`, `create_design_review`)

**Frontend Code Naming Conventions:**
- React components: PascalCase (`DesignReviewPanel`, `PipelineStatusBadge`)
- Component filenames: PascalCase matching component name (`DesignReviewPanel.tsx`)
- Hooks: camelCase prefixed with `use` (`usePipelineStatus`, `useDocumentUpload`)
- Zustand stores: PascalCase suffixed with `Store` (`PipelineStore`, `AuthStore`)
- Utility functions: camelCase (`formatTraceId`, `debounceRequest`)
- Constants: SCREAMING_SNAKE_CASE (`MAX_UPLOAD_SIZE_MB`, `DEFAULT_ASIL_LEVEL`)

### Structure Patterns

**Backend Project Organization (FastAPI):**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # Pydantic settings
│   ├── dependencies.py      # Shared DI (DB session, auth, tenant)
│   ├── exceptions.py        # Custom exceptions + global handlers
│   ├── middleware/          # Audit, tenant resolution, rate limiting
│   ├── routers/             # API route modules
│   │   ├── v1/
│   │   │   ├── documents.py
│   │   │   ├── designs.py
│   │   │   ├── code_modules.py
│   │   │   ├── test_runs.py
│   │   │   ├── releases.py
│   │   │   └── admin.py
│   ├── services/            # Business logic (orchestration)
│   ├── repositories/        # DB access layer
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response DTOs
│   ├── tasks/               # Celery task definitions
│   └── integrations/        # Polarion, Git, LDAP adapters
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── alembic/                 # DB migrations
├── Dockerfile
└── pyproject.toml
```

**Frontend Project Organization (React):**
```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── config.ts            # API base URL, feature flags
│   ├── api/                 # TanStack Query hooks + axios instance
│   ├── features/            # Domain-driven modules
│   │   ├── documents/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── api.ts
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   ├── design/
│   │   ├── pipeline/
│   │   ├── codeGen/
│   │   ├── testing/
│   │   └── admin/
│   ├── components/          # Shared UI primitives
│   ├── stores/              # Zustand stores
│   ├── hooks/               # Shared hooks
│   ├── utils/               # Helpers
│   └── types/               # Shared TypeScript types
├── tests/
└── vite.config.ts
```

### Format Patterns

**API Response Wrapper (Mandatory):**
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
Error response:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "DESIGN_REVIEW_BLOCKED",
    "message": "设计评审未通过",
    "detail": { "node": "FR-REQ-007" }
  },
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**JSON Field Naming:**
- Internal (DB / API / Python): snake_case
- Frontend consumption: camelCase
- Conversion: Pydantic `alias_generator=to_camel` (backend outbound); axios interceptor (frontend outbound)

**Date/Time Format:**
- API transport: ISO 8601 string (`2026-05-20T14:30:00+08:00`)
- Database: PostgreSQL `TIMESTAMPTZ`
- Frontend display: localized by UI component

### Communication Patterns

**Celery Task Naming:**
Format: `modu.{tenant_slug}.{feature}.{action}`
Examples: `modu.oem_a.documents.parse_pdf`, `modu.oem_a.pipeline.generate_design`

**WebSocket Event Naming:**
Format: `{entity}:{action}`
Examples: `pipeline:started`, `pipeline:progress`, `pipeline:completed`, `pipeline:failed`

**Event Payload Structure:**
```json
{
  "event": "pipeline:progress",
  "timestamp": "2026-05-20T14:30:00+08:00",
  "tenant_id": 123,
  "payload": {
    "pipeline_id": "uuid",
    "stage": "static_test",
    "progress_percent": 65,
    "message": "MISRA scan in progress..."
  }
}
```

### Process Patterns

**Error Handling:**
- Backend: FastAPI global exception handler (`@app.exception_handler`); all unhandled exceptions converted to standard response format
- Frontend: React Error Boundary per Feature route; API errors handled via TanStack Query `onError`
- User-facing messages: use `error.message` (Chinese-friendly)
- Debugging: use `error.trace_id` + console logs

**Loading States:**
- Global loading: page initial data fetch only
- Local loading: button submission, form save
- Forbidden: global overlay blocking all operations during data fetch (except page-level initialization)

**Authentication Flow:**
1. User login → LDAP verification → issue JWT access (15 min) + refresh (7 days)
2. Frontend stores in httpOnly cookie (XSS protection)
3. Each request carries `Authorization: Bearer {token}`
4. Token expiry → 401 → frontend silent refresh → retry original request → failure redirects to login

### Enforcement Guidelines

**All AI Agents MUST:**
- Use kebab-case plural nouns for backend API paths (`/code-modules`, not `/codeModule`)
- Use snake_case for DB tables/columns and PascalCase for model classes
- Wrap all API responses in standard format (`success` / `data` / `error` / `trace_id`)
- Name Celery tasks as `modu.{tenant}.{feature}.{action}`
- Match frontend component filenames exactly to component name (PascalCase)
- Use ISO 8601 strings for all dates at API layer

**Pattern Verification:**
- Backend: Pydantic models enforce schemas; API tests assert response format
- Frontend: ESLint rules (filenames, variable naming) + TypeScript strict mode
- Database: Alembic migration review checks naming conventions
- CI: Lint and type-check gates block non-compliant code

## Project Structure & Boundaries

### Requirements to Structure Mapping

| PRD REQ Group | Backend Router | Backend Service | Frontend Feature | Celery / AI Service |
|---|---|---|---|---|
| REQ-1 Documents | `routers/v1/documents.py` | `services/document_parser.py` | `features/documents/` | `tasks/documents.py` |
| REQ-2 Design | `routers/v1/designs.py` | `services/design_generator.py` | `features/design/` | `ai-service/` design prompt |
| REQ-3 CodeGen | `routers/v1/code_modules.py` | `services/code_generator.py` | `features/codeGen/` | `ai-service/` code prompt |
| REQ-4–7 Testing | `routers/v1/test_runs.py` | `services/test_executor.py` | `features/testing/` | `tasks/test.py` + Tasking Docker |
| REQ-8 Release | `routers/v1/releases.py` | `services/release_packager.py` | `features/releases/` | Polarion/Git adapters |
| REQ-9 Admin | `routers/v1/admin.py` | `services/tenant_manager.py` | `features/admin/` | — |
| Auth / Tenant | `routers/v1/auth.py` | — | `features/auth/` | LDAP adapter |
| AI Orchestration | — | `services/ai_orchestrator.py` | `features/pipeline/` | `ai-service/` container |

### Complete Project Directory Structure

```
modu/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docker-compose.override.yml
│
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── ssl/
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── middleware/
│   │   │   ├── tenant_resolution.py
│   │   │   ├── audit_logger.py
│   │   │   ├── rate_limiter.py
│   │   │   └── cors_security.py
│   │   ├── routers/v1/
│   │   │   ├── auth.py
│   │   │   ├── documents.py
│   │   │   ├── designs.py
│   │   │   ├── code_modules.py
│   │   │   ├── test_runs.py
│   │   │   ├── releases.py
│   │   │   └── admin.py
│   │   ├── services/
│   │   │   ├── document_parser.py
│   │   │   ├── design_generator.py
│   │   │   ├── code_generator.py
│   │   │   ├── test_executor.py
│   │   │   ├── release_packager.py
│   │   │   ├── tenant_manager.py
│   │   │   └── ai_orchestrator.py
│   │   ├── repositories/
│   │   │   ├── base.py
│   │   │   ├── document_repo.py
│   │   │   ├── design_repo.py
│   │   │   ├── code_module_repo.py
│   │   │   ├── test_run_repo.py
│   │   │   ├── release_repo.py
│   │   │   ├── tenant_repo.py
│   │   │   └── traceability_repo.py
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── parsed_requirement.py
│   │   │   ├── design.py
│   │   │   ├── design_review.py
│   │   │   ├── code_module.py
│   │   │   ├── test_case.py
│   │   │   ├── test_run.py
│   │   │   ├── test_result.py
│   │   │   ├── release_package.py
│   │   │   ├── trace_link.py
│   │   │   └── audit_log.py
│   │   ├── schemas/
│   │   │   ├── base.py
│   │   │   ├── auth.py
│   │   │   ├── document.py
│   │   │   ├── design.py
│   │   │   ├── code_module.py
│   │   │   ├── test.py
│   │   │   ├── release.py
│   │   │   └── admin.py
│   │   ├── tasks/
│   │   │   ├── celery_app.py
│   │   │   ├── documents.py
│   │   │   ├── design.py
│   │   │   ├── code.py
│   │   │   └── test.py
│   │   └── integrations/
│   │       ├── polarion/
│   │       │   ├── client.py
│   │       │   ├── mapper.py
│   │       │   └── importer.py
│   │       ├── git/
│   │       │   ├── client.py
│   │       │   └── commit_formatter.py
│   │       └── ldap/
│   │           ├── client.py
│   │           └── sync.py
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       └── integration/
│
├── ai-service/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── adapters/
│       │   ├── litellm_client.py
│       │   ├── openai_adapter.py
│       │   ├── anthropic_adapter.py
│       │   └── local_llm_adapter.py
│       ├── templates/
│       │   ├── design_prompt_v1.j2
│       │   ├── code_prompt_v1.j2
│       │   └── test_prompt_v1.j2
│       ├── constraints/
│       │   ├── misra_filter.py
│       │   ├── asil_validator.py
│       │   └── security_scanner.py
│       └── audit/
│           ├── gateway.py
│           └── storage.py
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── config.ts
│       ├── api/
│       │   ├── axios.ts
│       │   ├── auth.ts
│       │   ├── documents.ts
│       │   ├── designs.ts
│       │   ├── codeModules.ts
│       │   ├── testRuns.ts
│       │   ├── releases.ts
│       │   └── admin.ts
│       ├── features/
│       │   ├── auth/
│       │   ├── documents/
│       │   ├── design/
│       │   ├── pipeline/
│       │   ├── codeGen/
│       │   ├── testing/
│       │   ├── releases/
│       │   └── admin/
│       ├── components/
│       ├── stores/
│       ├── hooks/
│       ├── utils/
│       └── types/
│
└── toolchain/
    └── tasking/
        ├── Dockerfile
        └── scripts/
            ├── build.sh
            └── run_tests.sh
```

### Architectural Boundaries

**API Boundaries:**
- External (Nginx): `/api/v1/*` — all business endpoints; `/ws` — WebSocket progress push
- Internal (Docker network): `ai-service:8000/*` — backend only; `tasking:22` — containerized compiler
- Auth boundary: all `/api/v1/*` (except `/auth/login`) require valid JWT; `/admin/*` require Platform Admin role
- Tenant boundary: middleware resolves `X-Tenant-ID` or JWT claim; Repository layer auto-attaches `tenant_id`

**Component Boundaries:**
- Frontend: Features share state via Zustand + TanStack Query; no direct cross-Feature internal imports
- Backend: Router → Service → Repository strict layering; Service may call other Services, no cross-Repository direct access
- AI Service: internal REST only; all LLM calls pass through audit gateway

**Service Boundaries:**
- `backend` ↔ `ai-service`: HTTP internal network, standard JSON
- `backend` ↔ `tasking`: Docker exec / SSH scripts, stdout/stderr + artifact files
- `backend` ↔ `PostgreSQL`: SQLAlchemy asyncpg
- `backend` ↔ `Redis`: Celery broker + cache
- `backend` ↔ `Polarion/Git/LDAP`: individual adapters with independent connection pools

**Data Boundaries:**
- DB: `public` shared schema + RLS; every business table has `tenant_id`
- File storage: `/data/uploads/{tenant_id}/` and `/data/builds/{tenant_id}/`
- Cache: Redis key prefix `modu:{tenant_id}:{feature}:*`

### Integration Points

**Internal Communication:**
- Synchronous: HTTP REST between frontend ↔ backend, backend ↔ ai-service
- Asynchronous: Celery + Redis for pipeline stages; WebSocket for real-time progress

**External Integrations:**
- Siemens Polarion ALM: REST API, Work Item import, LiveDoc creation
- Git VCS: libgit2/GitPython, commit with Polarion Work Item ID
- AD/LDAP: python-ldap, org structure sync on first login
- Third-party LLM: LiteLLM unified proxy (OpenAI, Claude, local)
- Tasking Compiler: Docker container or host-mounted toolchain

**Data Flow:**
```
Upload Document → Parse (Celery) → AI Design (ai-service) → Human Review → AI Code (ai-service) → Static Test (Tasking) → Dynamic Test (Tasking) → Security Audit → Package → Git + Polarion
```

## Architecture Paradigm Update

### Shift: Programmatic Pipeline → BMAD-Agent Workflow

During Step 4 validation, the architecture underwent a paradigm shift from a traditional programmatic service-oriented pipeline to a **BMAD-Agent workflow paradigm**. This decision was driven by the recognition that Modu's core value is AI-driven automation, and an Agent-centric architecture provides superior extensibility, observability, and alignment with AI-native application design.

### What Changed

| Aspect | Original (Programmatic) | Updated (BMAD-Agent) |
|---|---|---|
| **Execution Unit** | Service functions (`design_generator.py`) | Autonomous Agents (`DesignAgent`, `CodeAgent`) |
| **Flow Control** | Hard-coded state machine | Declarative YAML Workflow definition |
| **Output Constraint** | Code logic + Pydantic schema | Jinja2 Templates + YAML Checklists |
| **Stage Transition** | API calls triggered by frontend/user | Workflow engine auto-schedules Agents based on conditions |
| **Retry/Feedback** | Manual re-trigger | Agent receives feedback and autonomously retries |
| **Audit Trail** | Manually logged | Workflow engine natively records full execution trace |

### Agent Framework Selection

**LangGraph** (LangChain ecosystem) was selected as the Agent orchestration framework.

**Rationale:**
- Native support for multi-Agent workflows with state management
- Built-in checkpointing and resumption (critical for long-running pipelines)
- Seamless integration with LiteLLM for pluggable LLM backends
- Conditional edges support complex branching (checklist pass/fail/human-in-the-loop)
- Python-native, fits the FastAPI backend stack

### Agent Taxonomy

| Agent | Type | Goal | Human-in-the-Loop |
|---|---|---|---|
| **DocumentParserAgent** | Tool Agent | Parse and structure input documents | No |
| **DesignAgent** | Creative Agent | Generate ASPICE-compliant design documents | No (auto) |
| **ReviewGate** | Decision Gate | Block for human approval/rejection | **Yes** |
| **CodeAgent** | Creative Agent | Generate MISRA/ASIL-compliant C code | No (auto) |
| **TestAgent** | Execution Agent | Execute static, dynamic, and regression tests | No (auto) |
| **SecurityAgent** | Audit Agent | Perform ISO 21434 security audit | No (auto) |
| **ReleaseAgent** | Packaging Agent | Package artifacts and push to Git/Polarion | No (auto) |

### Workflow Engine Design

```yaml
# workflow/pipeline_modu.yaml (conceptual)
name: modu_module_pipeline
version: 1.0

agents:
  DocumentParser:
    type: tool_agent
    tools: [PDFParser, OCR, RequirementExtractor]
    checklist: checklists/parse_exit.yaml

  DesignAgent:
    type: creative_agent
    tools: [LLMCaller, TemplateLoader, PolarionMapper, ASILValidator]
    template: templates/design_v1.j2
    checklist: checklists/design_exit.yaml

  ReviewGate:
    type: human_gate
    timeout: 7d
    notify: [websocket, email]

  CodeAgent:
    type: creative_agent
    tools: [LLMCaller, TemplateLoader, MISRAChecker, TraceIDInjector]
    template: templates/code_v1.j2
    checklist: checklists/code_exit.yaml

  TestAgent:
    type: execution_agent
    tools: [MISRAScanner, UnitTestRunner, CoverageAnalyzer, TaskingCompiler]
    checklist: checklists/test_exit.yaml

  SecurityAgent:
    type: audit_agent
    tools: [SecurityScanner, AttackSurfaceAnalyzer, CVSSRating]
    checklist: checklists/security_exit.yaml

  ReleaseAgent:
    type: packaging_agent
    tools: [ArtifactPackager, PolarionImporter, GitCommitter]
    checklist: checklists/release_exit.yaml

transitions:
  - from: DocumentParser
    to: DesignAgent
    condition: "checklist.all_passed"

  - from: DesignAgent
    to: ReviewGate
    condition: "checklist.all_passed"

  - from: ReviewGate
    to: CodeAgent
    condition: "human.approved"

  - from: ReviewGate
    to: DesignAgent
    condition: "human.rejected"
    action: "retry_with_feedback"

  - from: CodeAgent
    to: TestAgent
    condition: "checklist.all_passed"

  - from: TestAgent
    to: SecurityAgent
    condition: "checklist.all_passed"

  - from: TestAgent
    to: CodeAgent
    condition: "checklist.coverage_failed"
    action: "retry_with_asil_adjustment"

  - from: SecurityAgent
    to: ReleaseAgent
    condition: "checklist.all_passed"

  - from: ReleaseAgent
    to: "[END]"
    condition: "checklist.all_passed"
```

### Checklist Execution Model

**Checklists are executed programmatically** (not by AI) to ensure deterministic compliance validation:

```yaml
# checklists/design_exit.yaml
name: design_exit_v1
items:
  - id: DES-001
    category: traceability
    rule: "每个章节必须包含至少一个 Polarion 追溯 ID"
    validator: tools.polarion_mapper.has_trace_ids
    severity: blocking

  - id: DES-002
    category: compliance
    rule: "ASIL 等级必须与输入需求声明一致"
    validator: tools.asil_validator.match_input
    severity: blocking

  - id: DES-003
    category: completeness
    rule: "必须包含概述、架构、接口定义、动态行为、错误处理、测试策略六个章节"
    validator: tools.template_loader.validate_sections
    severity: blocking

  - id: DES-004
    category: quality
    rule: "设计文档不得超过 5000 字"
    validator: "lambda doc: len(doc.content) <= 5000"
    severity: warning
    action_on_fail: "split_or_summarize"
```

### Updated Project Structure (Agent Layer)

```
backend/app/
├── workflow/                    # ★ Workflow 引擎核心
│   ├── engine.py                # YAML 解析 + 状态机驱动
│   ├── state_manager.py         # Pipeline 状态持久化
│   ├── event_bus.py             # Agent 间事件总线
│   └── definitions/
│       └── pipeline_modu.yaml
│
├── agents/                      # ★ Agent 实现层
│   ├── base.py                  # BaseAgent 抽象类
│   ├── document_parser_agent.py
│   ├── design_agent.py
│   ├── code_agent.py
│   ├── test_agent.py
│   ├── security_agent.py
│   └── release_agent.py
│
├── tools/                       # ★ Agent 可调用的工具
│   ├── base.py                  # BaseTool 抽象类
│   ├── llm_caller.py            # 调用 ai-service / LiteLLM
│   ├── template_loader.py
│   ├── polarion_mapper.py
│   ├── misra_checker.py
│   ├── asil_validator.py
│   ├── security_scanner.py
│   ├── tasking_compiler.py
│   └── git_committer.py
│
├── templates/                   # ★ 产物模板（约束 Agent 输出格式）
│   ├── design_v1.j2
│   ├── code_v1.j2
│   ├── test_case_v1.j2
│   └── security_report_v1.j2
│
├── checklists/                  # ★ 退出验证清单
│   ├── parse_exit.yaml
│   ├── design_exit.yaml
│   ├── code_exit.yaml
│   ├── test_exit.yaml
│   ├── security_exit.yaml
│   └── release_exit.yaml
│
├── services/                    # 非 AI 业务服务（保留）
│   ├── tenant_manager.py
│   ├── file_storage.py
│   └── audit_logger.py
│
├── routers/v1/                  # HTTP API（人类操作界面）
│   ├── auth.py
│   ├── pipeline.py              # 触发/查询流水线
│   ├── review.py                # 人工评审接口
│   └── admin.py
│
├── models/, schemas/, repositories/  # 数据层（保留）
└── middleware/                  # 租户、审计、限流（保留）
```

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**
All technology choices work together without conflicts. LangGraph (Agent framework) integrates natively with Python/FastAPI backend. LiteLLM (ai-service) serves as the unified LLM proxy for all Agents. PostgreSQL + Redis continue to serve as persistence and message broker layers.

**Pattern Consistency:**
Naming conventions, API response formats, and communication patterns established in Step 5 remain fully applicable. The Agent paradigm adds new patterns (Agent base class, Tool base class, Checklist YAML schema) that are consistent with the existing codebase style.

**Structure Alignment:**
The updated project structure adds `agents/`, `tools/`, `workflow/`, `templates/`, and `checklists/` directories while preserving the existing layered architecture (Router → Service/Agent → Repository). Boundaries remain well-defined.

### Requirements Coverage Validation

**Functional Requirements Coverage:**
All 31 FRs are architecturally supported:
- REQ-1 (Documents): `DocumentParserAgent` + `tools.PDFParser/OCR`
- REQ-2 (Design): `DesignAgent` + `ReviewGate` (human-in-the-loop)
- REQ-3 (Code): `CodeAgent` + `tools.MISRAChecker`
- REQ-4–7 (Testing): `TestAgent` + `tools.TaskingCompiler/UnitTestRunner`
- REQ-7 (Security): `SecurityAgent` + `tools.SecurityScanner`
- REQ-8 (Release): `ReleaseAgent` + `tools.PolarionImporter/GitCommitter`
- REQ-9 (Admin): `services.tenant_manager` + `routers.admin`

**Non-Functional Requirements Coverage:**
All 14 NFRs are addressed:
- Performance: Nginx + FastAPI async + LangGraph checkpointing (resumable state)
- Reliability: Celery retry + Workflow engine state persistence + network fault tolerance
- Security: JWT + LDAP + HTTPS + audit gateway + data desensitization
- Maintainability: Alembic + Template versioning + Agent modularity
- Usability: React + Ant Design + WCAG 2.1 AA

### Implementation Readiness Validation

**Decision Completeness:**
All critical decisions documented with specific versions and frameworks:
- Agent Framework: LangGraph (latest stable)
- LLM Proxy: LiteLLM
- Checklist Execution: Programmatic (YAML-defined, Python-executed)
- Human-in-the-Loop: ReviewGate with WebSocket + timeout handling

**Structure Completeness:**
Complete directory tree defined to file level. All integration points mapped.

**Pattern Completeness:**
Naming, structure, format, communication, and process patterns fully specified with concrete examples. Agent-specific patterns (Tool invocation, Checklist validation, Workflow transitions) documented.

### Gap Analysis Results

**Critical Gaps:** None

**Important Gaps:**
1. CI/CD pipeline definition — Deferred to Post-MVP
2. Detailed database schema design — To be completed during implementation
3. Frontend page-level route definitions — To be defined during UX design or implementation

**Nice-to-Have Gaps:**
1. Agent performance benchmarking methodology
2. Workflow visualization dashboard (beyond basic status)

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY WITH MINOR GAPS

**Confidence Level:** High

**Key Strengths:**
- Agent paradigm provides superior extensibility for future pipeline stages
- Workflow-as-Code (YAML) enables non-developer adjustment of compliance gates
- Programmatic Checklist execution ensures deterministic audit trails required for automotive compliance
- Human-in-the-Loop design aligns with ASPICE review requirements

**Areas for Future Enhancement:**
- CI/CD pipeline for Agent/Template/Checklist versioning
- Workflow visualization and debugging tools
- Agent performance telemetry and optimization

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- All Agents MUST inherit from `BaseAgent`; all Tools MUST inherit from `BaseTool`
- All Checklists MUST be YAML-defined and programmatically executed
- Refer to this document for all architectural questions

**First Implementation Priority:**
1. Set up database schema (tenant, user, pipeline_state, audit_log)
2. Implement `workflow/engine.py` (YAML loader + state machine)
3. Implement `agents/base.py` and `tools/base.py`
4. Implement `DocumentParserAgent` as the first end-to-end Agent
5. Connect frontend `features/pipeline/` to backend Workflow API
