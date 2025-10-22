import os
import shutil
import subprocess
import time
from uuid import uuid4

from celery import signals
from celery.utils.log import get_task_logger

from openrelik_common.logging import Logger
from openrelik_worker_common.file_utils import create_output_file
from openrelik_worker_common.task_utils import create_task_result, get_input_files

import yaml
from pathvalidate import sanitize_filename

from .app import celery

# Task name used to register and route the task to the correct queue.
TASK_NAME = "openrelik-worker-evtxecmd.tasks.evtxecmd"

# Task metadata for registration in the core system.
TASK_METADATA = {
    "display_name": "Eric Zimmerman's EvtxECmd ",
    "description": "Runs Eric Zimmerman's EvtxECmd  application on evtx files",
}

COMPATIBLE_INPUTS = {
    "data_types": [],
    "mime_types": ["application/x-ms-evtx", "text/plain"],
    "filenames": [
        "*.evtx",
        ".openrelik-config"
        ],
}

log_root = Logger()
logger = log_root.get_logger(__name__, get_task_logger(__name__))


@signals.task_prerun.connect
def on_task_prerun(sender, task_id, task, args, kwargs, **_):
    log_root.bind(
        task_id=task_id,
        task_name=task.name,
        worker_name=TASK_METADATA.get("display_name"),
    )

@celery.task(bind=True, name=TASK_NAME, metadata=TASK_METADATA)
def evtxecmd(
    self,
    pipe_result=None,
    input_files=[],
    output_path=None,
    workflow_id=None,
    task_config={},
) -> str:
    output_files = []
    input_files = get_input_files(pipe_result, input_files or [], filter=COMPATIBLE_INPUTS)
    if not input_files:
        return create_task_result(
            output_files=output_files,
            workflow_id=workflow_id,
            command="",
        )

    # .openrelik-config 'hostname' key support
    prefix = ""
    config_item = next((f for f in input_files if f.get('display_name') == ".openrelik-config"), None)
    if config_item:
        try:
            with open(config_item.get('path'), "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if isinstance(config_data, dict) and "hostname" in config_data:
                raw_hostname = str(config_data["hostname"]).strip()
                prefix = f"{sanitize_filename(raw_hostname)}_"
            else:
                logger.info("No 'hostname' key found in .openrelik-config file.")

        except yaml.YAMLError:
            logger.error(".openrelik-config is not a valid YAML file.")
        except Exception as e:
            logger.error(f"Error reading .openrelik-config: {e}")

        # Pass through .openrelik-config as an output
        # need to move/rename .openrelik-config to the uuid and extension?
        config_passthrough_file = create_output_file(
            output_path,
            display_name=config_item.get('display_name'),
            data_type="openrelik:openrelik-config:openrelik-config",
        )
        # link file to location of new output_file
        os.link(config_item.get("path"), config_passthrough_file.path)
        # output our file
        output_files.append(config_passthrough_file.to_dict())

    # Prep for output file
    output_file = create_output_file(
        output_path,
        display_name=f"{prefix}EvtxECmd_output.csv",
        data_type="openrelik:evtxecmd:evtxecmd",
    )

    # Create temporary directory and hard link files for processing
    temp_dir = os.path.join(output_path, uuid4().hex)
    os.mkdir(temp_dir)
    for file in input_files:
        filename = os.path.basename(file.get("path"))
        os.link(file.get("path"), f"{temp_dir}/{filename}")

    command = [
        "dotnet",
        "/evtxecmd/EvtxeCmd/EvtxECmd.dll",
        "-d",
        temp_dir,
        "--csv",
        output_path,
        "--csvf",
        output_file.path,
    ]

    INTERVAL_SECONDS = 2
    process = subprocess.Popen(command)
    while process.poll() is None:
        self.send_event("task-progress", data=None)
        time.sleep(INTERVAL_SECONDS)

    # Remove temp directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    output_files.append(output_file.to_dict())

    return create_task_result(
        output_files=output_files,
        workflow_id=workflow_id,
        command=" ".join(command),
    )
