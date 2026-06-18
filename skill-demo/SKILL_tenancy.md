# Skill: Multi-tenancy & data-isolation conventions

This app is multi-tenant on a SHARED database: one row set, a `tenant_id` column on
every business table. Isolation is NOT enforced by the database or the ORM base class
— it is a CODE CONVENTION. Apply it when reviewing.

## The one rule that matters
- Every read or write of a tenant-scoped model (Invoice, Order, Customer, Subscription, …)
  MUST go through `scoped(session, Model)` from `db.py`, which appends
  `WHERE tenant_id = <current request tenant>`.
- A bare `session.query(Model)` / `Model.query` returns rows for **ALL tenants**. There is
  no global filter. This is our #1 cause of cross-tenant data leaks and has caused SEV1s.
- The current tenant is read from request context inside `scoped()`; never pass a
  tenant_id from the request body.

## Review checklist
- Any new `session.query(<TenantModel>)` without `scoped(...)` is a CRITICAL data-isolation
  bug — even if the code is otherwise perfectly correct and idiomatic.
