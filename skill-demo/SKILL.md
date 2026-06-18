# Skill: Billing & Resilience Conventions

This service has a few non-obvious infra conventions. Apply them when reviewing billing code.

## Resilience: the @retry decorator
- `infra.retry.retry` catches **every** exception (`except Exception`) and **re-executes the entire wrapped function from the top**, up to `max_attempts` (default **5**).
- It does NOT roll anything back. Any side effect performed before the failure point runs again on each retry.
- **Rule:** only decorate functions that are fully idempotent. Never put `@retry` on a function that performs a non-idempotent external side effect (charging a card, sending an email, posting to a queue) unless every such side effect is itself idempotency-keyed.

## Payments
- `PaymentsClient.charge(...)` creates a brand-new charge on every call **unless** an `idempotency_key` is passed. With a key, the gateway guarantees at-most-once.
- **Rule:** every call to `charge()` that can be retried MUST pass a stable `idempotency_key` (use the order/invoice id, never a random value).

## Ledger writes
- `db.execute` raises on transient failures (deadlocks, connection resets). These are common in production and WILL trigger @retry.
