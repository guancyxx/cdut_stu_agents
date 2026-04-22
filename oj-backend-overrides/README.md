# OJ backend runtime overrides

This directory stores source-controlled runtime overrides for the upstream QDUOJ backend image.

Upstream base:
- Backend image: `registry.cn-hongkong.aliyuncs.com/oj-image/backend:1.6.1`
- Upstream project: `QingdaoU/OnlineJudge`
- Synced file origin at the time of patching: `/app/judge/dispatcher.py` from the running `cdut-oj-backend` container

Current override:
- `judge/dispatcher.py`: guards against empty judge-server test case results so submissions no longer remain stuck in `JUDGING` when the judge returns `{"err": null, "data": []}`.

The root `docker-compose.yml` bind-mounts this file into `/app/judge/dispatcher.py` inside `cdut-oj-backend`.

Verification:
1. Recreate the backend service so the bind mount is active:
   `docker compose up -d oj-backend`
2. Run the regression test inside the backend container:
   `docker cp oj-backend-overrides/test_dispatcher_empty_data.py cdut-oj-backend:/tmp/test_dispatcher_empty_data.py && docker exec cdut-oj-backend python3 /tmp/test_dispatcher_empty_data.py`
3. Confirm the mounted runtime file contains the fix:
   `docker exec cdut-oj-backend python3 - <<'PY'
from pathlib import Path
text = Path('/app/judge/dispatcher.py').read_text()
print('Judge server returned empty test case results.' in text)
PY`
