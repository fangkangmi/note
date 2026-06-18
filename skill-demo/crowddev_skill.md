================ CLAUDE.md ================
# CDP — Community Data Platform

CDP is a community data platform by the Linux Foundation. It ingests millions of
activities and events daily from platforms like GitHub, GitLab, and many others
(not just code hosting). Open-source projects get onboarded by connecting
integrations, and data flows continuously at scale.

The ingested data is often messy. A big part of what CDP does is improve data quality: deduplicating member and organization profiles through merge and unmerge operations, enriching data via third-party providers, and resolving identities across sources. The cleaned data powers analytics and insights for LFX products.

The codebase started as crowd.dev, an open-source startup later acquired by the Linux Foundation. Speed was prioritized over standards, but the platform is now stable. The focus has shifted to maintainable patterns, scalability, and good developer experience. Performance matters at this scale, even small inefficiencies compound across millions of data points.

## Tech stack

TypeScript, Node.js, Express, PostgreSQL (pg-promise), Temporal, Kafka, Redis, OpenSearch, Zod, Bunyan, AWS S3.

Vue 3, Vite, Tailwind CSS, Element Plus, Pinia, TanStack Vue Query, Axios.

Package manager is **pnpm**. Monorepo managed via pnpm workspaces.

## Codebase structure

```
backend/          -> APIs (public endpoints for LFX products + internal for CDP UI)
frontend/         -> CDP Platform UI
services/apps/    -> Microservices — Temporal workers, Node.js workers, webhook APIs
services/libs/    -> Shared libraries used across services
```

`services/libs/common` holds shared utilities, error classes,
and helpers. If a piece of logic is reusable (not business logic), it belongs there.

`services/libs/data-access-layer` holds all
database query functions. Check here before writing new ones — duplicates are
already a problem.

## Patterns in transition

Old and new patterns coexist. Always use the new pattern.

- **Sequelize -> pg-promise**: Sequelize is legacy (backend only). Use
  `queryExecutor` from `@crowd/data-access-layer` for all new database code.
- **Classes -> functions**: Class-based services and repos are legacy. Write
  plain functions — composable, modular, easy to test.
- **Multi-tenancy -> single tenant**: Multi-tenancy is being phased out. The
  tenant table still exists. Code uses `DEFAULT_TENANT_ID` from `@crowd/common`.
  Don't add new multi-tenant logic.
- **Legacy auth -> Auth0**: Auth0 is the current auth system. Ignore old JWT
  patterns.
- **Zod for validation**: Public API endpoints use Zod schemas with
  `validateOrThrow`. Follow this pattern for all new endpoints.

## Working with the database

Millions of rows. Every query matters.

- Look up the table schema and indexes before writing any query. Don't select
  or touch columns blindly.
- Check existing functions in `data-access-layer` before writing new ones.
  Weigh the blast radius of modifying a shared function — sometimes a new
  function is safer.
- Write queries with performance in mind. Think about what indexes exist, what
  the query plan looks like, and whether you're scanning more rows than needed.

## Code quality

- Functional and modular. Code should be easy to plug in, pull out, and test
  independently.
- Think about performance at scale, even for small changes.
- Define types properly — extend and reuse existing types. Don't sprinkle `any`.
- Don't touch working code outside the scope of the current task.
- Prefer doing less over introducing risk. Weigh trade-offs before acting.

================ .claude/rules/commit-workflow.md ================
---
description: Commit conventions, branch naming, PR format, PR size guidelines, sign-off + GPG signing, and JIRA tracking workflow
paths:
  - '*'
---

# Commit & PR Workflow

## Commit Conventions

- Follow the [Conventional Commits](https://www.conventionalcommits.org/) format: `type: description`
- A scope is **optional** — most commits in this repo do not use one
- Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Use present tense, imperative mood: "add feature" not "added feature"
- Include the JIRA ticket **inline at the end** of the description, in parentheses
- Examples:
  - `feat: add github discussions integration (CM-1164)`
  - `fix: improve member merge suggestions (CM-1137)`
  - `chore: update stale dependency versions`

## Commit Signing

All commits must be both DCO-signed and GPG-signed:

- **DCO sign-off (`--signoff`)** — required by LF governance; validated by the Probot DCO check in CI. The `Signed-off-by: Name <email>` trailer is appended automatically when you pass `--signoff` (or `-s`).
- **GPG signature (`-S`)** — required by repo policy. Configure a signing key once:

  ```bash
  git config --global user.signingkey <KEY_ID>
  git config --global commit.gpgsign true
  ```

Standard commit command:

```bash
git commit --signoff -S -m "type: description (CM-XXX)"
```

If signing fails, fix the underlying issue — do not push unsigned commits. To verify signature status on a branch's commits:

```bash
git log --format='%G? %h %s' origin/main..HEAD
```

Acceptable `%G?` codes: `G` (good signature) or `U` (good signature, key not in local trust db). Codes `N`, `B`, or `E` need investigation.

## Branch Naming

- Format: `type/CM-<number>-short-description` (e.g. `feat/CM-1164-github-discussions`)
- The JIRA key in the branch name lets `/commit` include it automatically in the message

## PR Titles

- PR titles must contain a JIRA key — validated by CI (`.github/workflows/pr-title-jira-key-lint.yml`)
- Format: `type: description (CM-XXX)` — Conventional Commits format with the JIRA key in parens at the end
- Example: `feat: add github discussions source (CM-1164)`

## PR Size & Focus

- **Target under 1000 lines of diff** — one feature, one bug fix, or one refactor per PR
- **Don't bundle unrelated changes** — keeps reviews focused and rollbacks clean

## JIRA Tracking

Before starting any work:

1. Check if there is a JIRA ticket in the `CM` project
2. Create one if untracked work
3. Include `CM-XXX` in commit messages and PR title

================ .claude/skills/review-pr/references/backend-checklist.md ================
# Backend Review Checklist

Express.js / pg-promise API review standards for the CDP repo (`backend/`).

---

## 1. New Sequelize usage (CRITICAL)

All new database code must use `queryExecutor` from `@crowd/data-access-layer`, not Sequelize. Sequelize is legacy and limited to existing usage in `backend/src/database/repositories/` and `backend/src/services/`.

**Violation:**
```ts
import { Sequelize } from 'sequelize'
const result = await Model.findAll({ where: { id } })
```

**Fix:**
```ts
// Use an existing DAL function from services/libs/data-access-layer/src/
// or add a new one using queryExecutor
```

Do **not** flag existing Sequelize in `backend/src/database/repositories/` or `backend/src/services/` — those are legacy files being migrated incrementally.

---

## 2. New public endpoints missing Zod + validateOrThrow (CRITICAL)

All new public API endpoints must validate input with a Zod schema using `validateOrThrow`.

**Violation:**
```ts
router.post('/members', async (req, res) => {
  const { name, email } = req.body // no validation
})
```

**Fix:**
```ts
import { z } from 'zod'
import { validateOrThrow } from '@crowd/common'

const schema = z.object({ name: z.string(), email: z.string().email() })

router.post('/members', async (req, res) => {
  const body = validateOrThrow(schema, req.body)
})
```

---

## 3. New multi-tenant logic (CRITICAL)

Multi-tenancy is being phased out. New code must use `DEFAULT_TENANT_ID` from `@crowd/common` rather than introducing new multi-tenant logic.

**Fix:**
```ts
import { DEFAULT_TENANT_ID } from '@crowd/common'
```

---

## 4. New class-based services or repositories (SHOULD FIX)

New code should use plain functions, not class-based patterns.

**Violation:**
```ts
export class MemberService {
  async findById(id: string) { ... }
}
```

**Fix:**
```ts
export async function findMemberById(id: string) { ... }
```

---

## 5. DAL function added without checking for existing equivalents (SHOULD FIX)

Before adding a new function to `services/libs/data-access-layer/src/`, verify no equivalent already exists. Flag any new DAL function that appears to duplicate an existing one.

---

## 6. `any` types in new code (SHOULD FIX)

Avoid `any`. Use proper types, `unknown` with narrowing, or generics.

---

## 7. No secrets hardcoded (CRITICAL)

API keys, tokens, and credentials must come from environment variables, never hardcoded.

---

## 8. Auth0 vs legacy JWT (SHOULD FIX)

New auth code must use Auth0 patterns. Do not introduce new legacy JWT patterns.

---

## Known false positives — do NOT flag

- Sequelize usage in `backend/src/database/repositories/` or `backend/src/services/` — legacy files
- `DEFAULT_TENANT_ID` usage — this is the correct pattern
- Zod usage outside `validateOrThrow` (e.g. internal validation) — not a violation

================ .claude/skills/review-pr/references/services-checklist.md ================
# Services Review Checklist

Review standards for microservices under `services/apps/` and shared libraries under `services/libs/`.

---

## Temporal Worker patterns (`services/apps/*/`)

### 1. Workflows must be deterministic (CRITICAL)

Temporal workflows must be fully deterministic. No direct I/O, no `Math.random()`, no `Date.now()`, no non-deterministic APIs inside workflow code. Move all I/O into Activities.

### 2. Activities should be idempotent (SHOULD FIX)

Temporal may retry activities on failure. Activities should be safe to run multiple times without unintended side effects.

### 3. No direct Kafka/Redis calls inside Temporal workflows (CRITICAL)

Kafka producers and Redis clients must only be called from Activities, not from Workflow code.

---

## Shared Libraries (`services/libs/*/`)

### 4. New DAL functions — check for existing equivalents first (SHOULD FIX)

Before adding a new function to `services/libs/data-access-layer/src/`, verify no equivalent exists.

### 5. `queryExecutor` from `@crowd/data-access-layer` (CRITICAL)

All new database queries must use `queryExecutor`. Do not add Sequelize or raw `pg` queries to service libraries.

### 6. Query performance awareness (SHOULD FIX)

Flag queries that clearly scan large tables without an appropriate WHERE clause using an indexed column.

### 7. Bunyan logger usage (SHOULD FIX)

Use the logger from `@crowd/logging`, not `console.log/error/warn`.

### 8. New class-based code (SHOULD FIX)

New service/worker code should use plain functions, not class-based patterns. Classes are legacy.

---

## Known false positives — do NOT flag

- Existing class-based workers that have not been refactored — only flag **new** classes
- `queryExecutor` usage in `services/libs/data-access-layer/` — correct pattern
- `DEFAULT_TENANT_ID` from `@crowd/common` — correct pattern

================ .claude/skills/review-pr/references/frontend-checklist.md ================
# Frontend Review Checklist

Vue 3 / Vite frontend review standards for the CDP repo (`frontend/`).

---

## 1. Composition API with `<script setup>` (SHOULD FIX)

Use `<script setup>` with Composition API. No Options API components.

**Violation:**
```vue
<script>
export default {
  data() { return { count: 0 } }
}
</script>
```

**Fix:**
```vue
<script setup lang="ts">
const count = ref(0)
</script>
```

---

## 2. TanStack Vue Query for server state (SHOULD FIX)

Use `useQuery` / `useMutation` from TanStack Vue Query for data fetching. Do not use raw `axios` directly in `onMounted` for data that should be cached.

**Violation:**
```ts
const data = ref(null)
onMounted(async () => {
  data.value = await axios.get('/api/members')
})
```

**Fix:**
```ts
import { useQuery } from '@tanstack/vue-query'
const { data } = useQuery({
  queryKey: ['members'],
  queryFn: () => axios.get('/api/members').then(r => r.data),
})
```

---

## 3. Pinia for shared client state (SHOULD FIX)

Use Pinia stores for shared client-side state. Do not pass deeply nested props for state that should be in a store.

---

## 4. TypeScript — no `any` (SHOULD FIX)

Avoid `any`. Use proper types, `unknown` with narrowing, or generics.

---

## 5. Tailwind CSS conventions (SHOULD FIX)

- **Prefer `gap-*` over `space-y-*`** for vertical stacking
- No hard-coded hex color values in templates — use Tailwind color tokens

---

## 6. Reactive refs over non-reactive values (SHOULD FIX)

State that should trigger re-renders must use `ref()` or `computed()`.

**Violation:**
```ts
let isLoading = false // won't trigger re-render
```

**Fix:**
```ts
const isLoading = ref(false)
```

---

## 7. Element Plus usage patterns (NIT)

The project uses Element Plus (`el-*`). Follow existing component usage patterns — check how similar components are used elsewhere before introducing a new pattern.

================ .claude/skills/review-pr/references/sql-checklist.md ================
# SQL & Migration Review Checklist

Review standards for database queries in `services/libs/data-access-layer/` and migrations in `backend/src/database/migrations/`.

---

## Flyway Migrations

### 1. Migrations are append-only (CRITICAL)

Never modify an existing migration file that has been applied. Create a new migration to alter or fix a previous one.

**Violation:** Editing `V1234__create_members_table.sql` after it has been applied.

**Fix:** Create `V1235__alter_members_add_column.sql` with the corrective change.

---

### 2. Migration filename format (SHOULD FIX)

Migration files must follow: `V{epoch}__{description}.sql` and `U{epoch}__{description}.sql` (undo). The version must be unique and greater than all existing versions.

---

### 3. Migrations must be safe for production (CRITICAL)

Avoid:
- `DROP TABLE` without verifying data is no longer needed
- `ALTER TABLE ... NOT NULL` without a default or two-step migration (add nullable first, backfill, then add constraint)
- Renaming columns without updating all code references first
- Large table operations without considering lock impact

---

## Data Access Layer Queries

### 4. Parameterized queries only — no string interpolation (CRITICAL)

All queries must use parameterized placeholders (`$1`, `$2`, etc.). Never interpolate user input directly into SQL.

**Violation:**
```ts
await queryExecutor.query(`SELECT * FROM members WHERE email = '${email}'`)
```

**Fix:**
```ts
await queryExecutor.query('SELECT * FROM members WHERE email = $1', [email])
```

---

### 5. Placeholder count matches bind values (CRITICAL)

Every `$N` placeholder must have a corresponding value in the binds array, in correct order. Mismatch causes runtime errors.

---

### 6. Index awareness (SHOULD FIX)

Before writing a query, verify the table has an index on the WHERE clause columns. Flag queries that will cause full table scans on large tables (`members`, `activities`, `organizations`).

Common indexed columns: `id`, `tenantId`, `platform`, `sourceId`, `memberId`, `organizationId`, `timestamp`, `deletedAt`.

---

### 7. Blast radius check for modified DAL functions (SHOULD FIX)

If a shared DAL function in `services/libs/data-access-layer/src/` is modified, check all callers. Use `grep -r "functionName" services/ backend/` to find them.

---

### 8. Soft-delete awareness (SHOULD FIX)

Many tables use `deletedAt` for soft deletes. Queries that don't filter on `deletedAt IS NULL` may return deleted records. Verify the intended behavior.

