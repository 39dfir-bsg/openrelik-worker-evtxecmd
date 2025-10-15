# Openrelik worker evtxecmd
## Description
This worker runs eric zimmerman's evtxecmd application against evtx files.

## Deploy
Add the below configuration to the OpenRelik docker-compose.yml file.

```
openrelik-worker-evtxecmd:
    container_name: openrelik-worker-evtxecmd
    image: openrelik-worker-evtxecmd:${OPENRELIK_WORKER_EVTXECMD_VERSION}
    restart: always
    environment:
      - REDIS_URL=redis://openrelik-redis:6379
    volumes:
      - ./data:/usr/share/openrelik/data
    command: "celery --app=src.app worker --task-events --concurrency=4 --loglevel=INFO -Q openrelik-worker-evtxecmd"
    
    # ports:
      # - 5678:5678 # For debugging purposes.
```

## Test
```
uv sync --group test
uv run pytest -s --cov=.
```
