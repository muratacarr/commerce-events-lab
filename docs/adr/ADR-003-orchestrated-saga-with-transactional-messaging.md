# ADR-003: Orchestrated charge-then-allocate saga with transactional messaging

Status: Proposed

## Decision
Order orchestrates: charge, then allocate stock, refund if allocation is rejected after a
successful charge. Saga progress is a durable cursor in Order, consistent with aggregate history.
Each service writes its outgoing messages to a transactional outbox and a polling relay publishes
them after commit (publisher confirms plus mandatory routing). Consumers use a unique
`(consumer_name, message_id)` inbox and a unique business `operation_id`, ack only after COMMIT,
and quarantine poison messages durably in the database before ack. Delivery is at-least-once; the
design claims duplicate-safe effects, never exactly-once delivery.

## Alternatives rejected
Choreography (kept as an optional later comparison exercise, PROJECT-025); publishing inside the
business transaction; hot nack/requeue retry loops; a broker DLQ as the only quarantine.

## Consequences
A saga gives compensating business consistency, not a distributed SQL transaction or isolation.
A refund that cannot complete leaves the order `COMPENSATING` or `NEEDS_ATTENTION`, never falsely
`COMPENSATED`.
