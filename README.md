# Openrelik worker evtxecmd
## Description
This worker runs eric zimmerman's evtxecmd application against evtx files.

Supports an `.openrelik-config` file.

Supply an `.openrelik-config` file to this worker with an `openrelik-hostname:` argument and it will prefix any output with the included hostname. It will also perform passthrough of the `.openrelik-config` file so it can be used in any follow on worker tasks. If you're running an extract from an archive task before this, place your `.openrelik-config` file in an archive (eg. `openrelik-config.zip`) and add globs for it (`*.openrelik-config`) to your extract from archive task.

You might want to use the following glob when extracting from a zip archive before this.

`*.evtx`

## Deploy
Update your `config.env` file to set `OPENRELIK_WORKER_EVTXECMD_VERSION` to the tagged release version you want to use.

Add the below configuration to the OpenRelik docker-compose.yml file, you may need to update the `image:` value to point to the container in a  registry.

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
