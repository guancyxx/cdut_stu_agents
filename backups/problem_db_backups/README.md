# Problem Database Backups

Timestamped backups of the problem database (problem/tags) for the current single-DB runtime.

## Files

- `problems_dump.json.gz` — JSON dump (problem + tags)
- `problems_pg.dump` — PostgreSQL custom dump of problem tables

## Restore via psql (recommended)

```bash
docker cp problems_pg.dump cdut-postgres:/tmp/
docker exec cdut-postgres pg_restore -U cdut -d cdut_oj --clean --if-exists /tmp/problems_pg.dump
```

## Restore via JSON dump

```bash
gunzip -c problems_dump.json.gz > /tmp/problems_dump.json
# 使用自定义导入脚本按当前表结构落库
# 说明：该仓库已不再依赖 QDUOJ Django manage.py loaddata
```

## Generation

```bash
# pg_dump (current runtime)
docker exec cdut-postgres pg_dump -U cdut -d cdut_oj \
  --clean --if-exists \
  -t public.problem -t public.problem_tag -t public.problem_tags \
  --format=custom -f /tmp/problems_pg.dump
docker cp cdut-postgres:/tmp/problems_pg.dump .
```
