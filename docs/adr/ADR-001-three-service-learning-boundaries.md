# ADR-001: Three-service learning boundaries

Status: Proposed (setup stage; becomes Accepted when implementation is approved)

## Context
The generic recommendation is a single deployable with cohesive internal boundaries. This lab
exists to teach failure isolation across Order, Payment and Inventory, so independent
stop/crash/restart of each service is the learning goal, not a scaling need.

## Decision
Exactly three FastAPI services (Order, Payment, Inventory), one instance each, one repository,
one Compose project, one PostgreSQL process with three service-owned databases and credentials,
one RabbitMQ broker. Share only versioned wire schemas (`src/contracts`) and tiny transport
helpers, never ORM entities or repositories. No fourth coordinator, no generic event-bus or
repository framework.

## Alternatives rejected
Monolith (hides the failure boundaries); Celery (unrelated abstraction); three database
containers (operational isolation not needed yet); Kafka/Redis/Kubernetes (out of scope).

## Consequences
One PostgreSQL process and one broker are shared failure domains; in-process workers share their
service's failure domain. No cross-database reads, transactions or foreign keys. No availability
or throughput claim is made (NOT_MEASURED).
