# Infrastructure Plan

> Planning only. This document describes future infrastructure work. No installations, configuration changes, containers, workflows, deployments, or other implementation files were created by the infrastructure-planning process.

## 1. Project and User Experience

- **Application:** Personal, account-based web application.
- **Primary users:** Individual users managing their own data.
- **Primary user task:** Not yet specified; the platform supports personal structured data and account workflows.
- **Selected platform:** React web application.
- **User-experience rationale:** Provides direct browser access while keeping the backend in Python.
- **Required operating systems, browsers, or devices:** Current major browsers.
- **Offline or native-device requirements:** No strong offline or native-device requirement confirmed.

## 2. Connectivity and Application Shape

- **Connectivity model:** Single-user web-enabled.
- **Accounts and authentication:** One account per user; authentication is required. Choose a maintained Django-compatible authentication approach during implementation.
- **Backend required:** Yes: a single Django application exposes the API and owns account data.
- **Cross-device persistence:** Hosted PostgreSQL is the source of truth.
- **Interaction between accounts:** None planned; user data remains private to its owner.
- **Primary application components:** Django API, React web client, and PostgreSQL.

## 3. Selected Technology Stack

| Area | Selected technology | Purpose | Version policy |
|---|---|---|---|
| Primary language | Python | Backend application code | Supported stable Python release compatible with Django |
| Web language | TypeScript | Type-safe React web client | Supported stable TypeScript |
| Application framework | Django with Django REST Framework | Account-aware API and backend | Current supported Django and DRF releases |
| Web framework | React with Vite | Browser client and static build | Current supported React and Vite releases |
| Python package manager | uv | Reproducible Python dependency management | Current supported release |
| JavaScript package manager | pnpm | Reproducible web dependencies | Current supported release |
| Build tool | Vite | Build web assets | Versions pinned by lockfiles |
| API layer | REST over HTTPS | API for the web client | Version endpoints when breaking changes are needed |

## 4. Storage and Persistence

- **Storage model:** Hosted relational storage.
- **Primary data store:** Managed PostgreSQL.
- **User files or object storage:** None selected; add managed object storage only if uploads are introduced.
- **Local-development storage:** PostgreSQL service container with a named volume.
- **Production hosting model:** Managed PostgreSQL separate from the backend application container.
- **Schema and migration approach:** Django migrations, reviewed and applied as part of a controlled release.
- **Backup, export, or recovery approach:** Enable managed-provider automated backups and document a user-data export path before launch.
- **Secrets and connection-string approach:** Use environment-provided secrets; never commit database URLs, credentials, or Django secret keys.
- **Reason this storage fits the access pattern:** PostgreSQL provides reliable, structured, hosted data for one user's account across all clients.

## 5. Testing Tools

| Test layer | Tool or library | Planned scope | Planned execution point |
|---|---|---|---|
| Unit | pytest and Django test utilities | Backend domain logic, views, serializers, and permissions | Local and pull requests |
| Integration | pytest, Django test client, Testcontainers for PostgreSQL | API, migration, and real-database behavior | Local and pull requests |
| Web component | Jest and React Testing Library | React rendering, accessibility, and interaction | Local and pull requests |
| Web end-to-end | Playwright | Critical account and primary user workflows | Pull requests and releases |

## 6. Test Analysis

| Capability | Tool | Planned policy |
|---|---|---|
| Backend coverage | coverage.py with pytest | Collect on pull requests and retain reports |
| Client coverage | Jest coverage (V8) | Collect on pull requests and retain reports |
| Coverage threshold or regression rule | Per-project modest threshold, initially agreed before enforcement | Block pull requests that fall below the agreed baseline |
| Mutation testing | Not initially selected | Reassess for critical backend logic after core workflows stabilize |
| Reporting | GitHub Actions artifacts and pull-request summaries | Preserve coverage output for failed or reviewed runs |

## 7. Static Analysis and Security

| Check | Tool | Planned enforcement |
|---|---|---|
| Python formatting and linting | Ruff | Blocking pull-request check |
| Python type checking | Pyright | Blocking pull-request check |
| Web formatting | Prettier | Blocking pull-request verification |
| Web linting | ESLint | Blocking pull-request check |
| Web type checking | TypeScript compiler | Blocking pull-request check |
| Dependency vulnerability scanning | Dependabot | Automated update proposals and review |
| Secret scanning | Gitleaks | Blocking pull-request and release check |
| Static security analysis | Bandit, Semgrep, and CodeQL | Bandit/Semgrep on pull requests; CodeQL scheduled and on release |
| Container scanning | Trivy | Scan backend image before publication |

## 8. Development Technologies Requiring Manual Installation

These are developer-workstation prerequisites that will not be supplied by the planned Docker environment.

| Technology | Why it is needed | Required on which machines | Version policy | Planned installation or verification method | Why Docker does not provide it |
|---|---|---|---|---|---|
| Git | Source control | All developer machines | Supported current release | Future documented setup check | Repository work happens on the host |
| Docker Desktop or Docker Engine | Local containers | Developers working on backend/database | Supported current release | Future documented setup check | Docker is the host container runtime |
| Node.js and pnpm | React web development | Web developers and CI runners | Supported Node LTS | Future documented setup check | Needed for the host-facing web toolchain |
| Python and uv | Django local development | Backend developers and CI runners | Supported Python release | Future documented setup check | Needed for editor integration and non-container workflows |

### Host tools intentionally not required

- **Not required because Docker supplies them:** Local PostgreSQL server installation.
- **Not required for this platform:** Desktop-native packaging toolchains and decentralized-storage software.

## 9. Docker Plan

- **Planned Docker role:** Development and production deployment for the Django backend.
- **Future files that would be created during implementation:** Backend `Dockerfile`, development Compose file, `.dockerignore`, and environment-variable templates.
- **Planned images and services:** A Django backend image and local PostgreSQL service; production uses managed PostgreSQL.
- **Development container behavior:** Bind-mount backend source; use a named volume for PostgreSQL data; run dependencies within the planned development image.
- **Ports:** Document backend and PostgreSQL ports in future Compose configuration; bind database access locally only.
- **Bind mounts and named volumes:** Backend source bind mount for development; named volume for local database persistence.
- **Environment-variable and secret handling:** Local non-secret templates only; production values originate in protected hosting and GitHub environments.
- **Local database or service containers:** PostgreSQL only unless a later feature adds a justified service.
- **Production image or non-container release path:** Multi-stage, minimal, non-root backend image; Vite build deploys static web files.
- **Build stages and hardening:** Multi-stage build, non-root runtime user, minimal runtime image, `.dockerignore`, health check, and no embedded secrets.
- **Planned future development command:** Document a future Compose command after Compose files exist; do not run it during planning.
- **Planned future production command:** Document a future image build command after its configuration exists; do not run it during planning.

## 10. GitHub Actions Plan

### A. Automated pull-request checks

- **Future workflow file:** `.github/workflows/pr-checks.yml`
- **Trigger:** `pull_request`.
- **Runner or matrix:** Ubuntu runner for backend, web, database integration, and web E2E.
- **Permissions:** Read-only repository contents; grant only the minimal permissions required to report checks or upload artifacts.
- **Planned jobs in order:**
  1. Checkout, set up pinned Python and Node LTS, restore dependency caches, and perform lockfile-enforced installs.
  2. Verify Ruff, Pyright, Prettier, ESLint, and TypeScript checks.
  3. Run backend unit/integration tests with PostgreSQL/Testcontainers and client component tests; collect coverage.
  4. Build Django assets as applicable and Vite web client; run Playwright critical workflows.
  5. Run Gitleaks, Bandit, Semgrep, dependency checks, and selected CodeQL analysis; upload reports and failure artifacts.
- **Service containers:** Prefer Testcontainers for real PostgreSQL integration tests; use a GitHub service container only if faster and equivalent.
- **Caching:** Cache uv and pnpm stores using lockfile keys; cache Playwright browsers using a versioned key.
- **Coverage and analysis reporting:** Publish coverage summaries and retain raw reports as artifacts; enforce the agreed modest threshold.
- **Failure artifacts:** Playwright traces/screenshots, test logs, coverage reports, and relevant scan reports.
- **Checks that should block merging:** Lockfile installs, formatting, lint/type checks, tests, threshold, build, Playwright critical path, Gitleaks, Bandit, and Semgrep.
- **Proposed branch-protection settings:** Require the blocking checks, one approving review, an up-to-date branch, and no unresolved conversations.

### B. New-release deployment

- **Future workflow file:** `.github/workflows/release.yml`
- **Release trigger:** Protected `v*` tag or `workflow_dispatch` targeting a protected production environment.
- **Release destination:** Managed hosting for the Django backend and React web client.
- **Runner or matrix:** Ubuntu for validation, image build/scan, backend deployment, and web deployment.
- **Planned jobs in order:**
  1. Validate the release commit using the required checks and build backend and web artifacts.
  2. Scan the backend image, publish it to the selected registry, then deploy backend and static web assets after protected-environment approval.
  3. Apply reviewed Django migrations once and run smoke checks.
  4. Publish GitHub Release notes with checksums and links to release artifacts where appropriate.
- **Build artifacts:** Backend container digest, web build identifier, checksums, and release notes.
- **Signing, notarization, or store requirements:** Protected secret storage for hosting and registry deployment credentials.
- **Database migration step:** Run controlled Django migrations after a verified backup point and before traffic relies on schema changes.
- **Environment approval:** Use a protected GitHub `production` environment for backend/web deployment and release credentials.
- **Post-deployment verification:** Authenticated and unauthenticated health checks plus critical web API smoke tests.
- **Failed-release or rollback approach:** Redeploy the prior backend image and web build; use backward-compatible migrations or a reviewed migration recovery procedure.

### GitHub configuration required later

| Name | Type | Purpose |
|---|---|---|
| `production` | GitHub environment | Protected approval boundary for production deployment |
| `DATABASE_URL` | Secret | Production PostgreSQL connection string |
| `DJANGO_SECRET_KEY` | Secret | Django cryptographic secret |
| `DEPLOY_*` | Secret/token | Managed-hosting and container-registry deployment credentials |
| `CODEQL` configuration | Repository security configuration | Enable scheduled code scanning results |

## 11. Planned Repository Artifacts - Not Created by This Skill

- [ ] Backend application manifest/project file and Python lockfile.
- [ ] Web package manifest and pnpm lockfile.
- [ ] Backend and web test configuration.
- [ ] Ruff, Pyright, Prettier, ESLint, TypeScript, Bandit, Semgrep, and Gitleaks configuration.
- [ ] Backend `Dockerfile`, Compose file, `.dockerignore`, and non-secret environment template.
- [ ] `.github/workflows/pr-checks.yml`.
- [ ] `.github/workflows/release.yml`.
- [ ] Managed-hosting release configuration.

## 12. Assumptions and Open Items

- **Assumptions:** The application handles private personal data, requires normal account authentication, does not currently require uploads, collaboration, or offline-first synchronization, and will use one deployable Django backend rather than microservices.
- **Decisions still requiring an external account, credential, certificate, or organizational approval:** Hosting provider and container registry; PostgreSQL provider; production-domain ownership.
- **Items to confirm before implementation begins:** Primary user workflow and data model, authentication provider/method, privacy and retention requirements, exact supported browser versions, hosting and registry providers, and coverage threshold.
