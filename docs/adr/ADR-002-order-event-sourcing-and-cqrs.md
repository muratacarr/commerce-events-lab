# ADR-002: Event Sourcing and CQRS for Order only

Status: Proposed

## Decision
Order events are the source of truth (`order_events`, unique `(order_id, aggregate_version)`,
unique `event_id`, optimistic expected-version append). Aggregate state comes from pure
deterministic `apply(event)` reducers. `order_view` is an asynchronously polled projection with
per-stream checkpoints; it never authorizes a write. Snapshots come only after full replay works
and always fall back to full replay when missing, corrupt or incompatible. Payment and Inventory
use ordinary relational state plus inbox/outbox.

## Alternatives rejected
EventStoreDB (changes the stack); SQLite (hides PostgreSQL concurrency); CDC (extra infrastructure
beyond a polling outbox); a global `MAX(BIGSERIAL)` projection cursor (allocation order can differ
from commit order).

## Consequences
Eventual consistency between write and read side is visible by design (lag). Rebuilding Order
history cannot recreate Payment or Inventory databases.
