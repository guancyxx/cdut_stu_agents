# Problem Database Backups

Timestamped backups of the QDUOJ problem database (2,683 problems + tags).

## Files

- `problems_dump.json.gz` — Django `dumpdata` output (problem.Problem + problem.ProblemTag), can be restored via `manage.py loaddata`
- `problems_pg.dump` — PostgreSQL custom-format dump of `problem`, `problem_tags`, `problem_problemtag` tables, can be restored via `pg_restore`

## Restore via Django loaddata

```bash
gunzip -c problems_dump.json.gz > /tmp/problems_dump.json
docker cp /tmp/problems_dump.json cdut-oj-backend:/tmp/
docker exec cdut-oj-backend python manage.py loaddata /tmp/problems_dump.json
```

## Restore via pg_restore

```bash
docker cp problems_pg.dump cdut-oj-postgres:/tmp/
docker exec cdut-oj-postgres pg_restore -U onlinejudge -d onlinejudge --clean --if-exists /tmp/problems_pg.dump
```

## Generation

```bash
# Django dumpdata
docker exec cdut-oj-backend python manage.py dumpdata problem.Problem problem.ProblemTag \
  --natural-foreign --natural-primary --indent 2 \
  -o /tmp/problems_dump.json
docker cp cdut-oj-backend:/tmp/problems_dump.json .

# pg_dump
docker exec cdut-oj-postgres pg_dump -U onlinejudge -d onlinejudge \
  --clean --if-exists \
  -t problem -t problem_tags -t problem_problemtag -t problem_problem_tags \
  --format=custom -f /tmp/problems_pg.dump
docker cp cdut-oj-postgres:/tmp/problems_pg.dump .
```
