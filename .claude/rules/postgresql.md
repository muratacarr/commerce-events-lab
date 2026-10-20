# postgresql

<!-- Kept unscoped (path-scoped loading NOT_VERIFIED). Intended scope: migrations/**, src/**, tests/** -->

- PG-001 [MANDATORY] When PostgreSQL selected: Use schema migrations, appropriate primary/foreign/unique/check constraints, parameterized access, explicit transaction boundaries and concurrency safeguards.
- PG-002 [MANDATORY] When PostgreSQL selected: Use least-privilege database access, secure connections, bounded pooling and query/index review; prevent N+1 queries.
- PG-003 [CONDITIONAL] When important durable data: Define backup retention, tested restore and migration recovery evidence; replicas do not replace backups.
