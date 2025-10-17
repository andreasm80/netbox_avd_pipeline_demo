import grpc
import logging
import json
from typing import Dict, List
from uuid import uuid4

# NOTE: Requires the following libraries to be installed:
# pip install grpcio
# pip install grpcio-tools
# pip install arista-eapi-client
# pip install arista-cvp-client
# NOTE: The 'fmp' library is required for the MapStringString wrapper.
# You will need to obtain this from the official Arista SDKs.
from fmp import wrappers_pb2 as fmp_wrappers

from arista.changecontrol.v1 import models, services
from google.protobuf import wrappers_pb2 as wrappers

RPC_TIMEOUT = 30  # in seconds

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Configuration ---
# Your CVaaS server and API token.
CVAAS_SERVER = "www.cv-staging.corp.arista.io:443"
API_TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJkaWQiOjQyOTc4NzE4MDQsImRzbiI6ImFuZHJlYXNfYXZkIiwiZHN0IjoiYWNjb3VudCIsImV4cCI6MTkwMzU1NzU5OSwiaWF0IjoxNzQ2OTkwODE4LCJvZ2kiOjkwODE1LCJvZ24iOiJhcmlzdGEtc2Utbm9yZGljIiwic2lkIjoiZDZhNzZhZmIyYTk2ZDExNjUyMWQxYWYyMWQxYWYyNmE3ZTFhMzBjNTgyMTFmMzJjNWNmMmFlZWI3YWUxZjcxN2NkOTQ5Ny1VdHFpRzdNN2ZVcVNnSXhfc3BLOTZldnVnSWlaYjhpYnhKZUZlYXFMIn0.ZsVOGt4gtDCzvHYPbdmm1pJ06XIOoy5xOfnk-qYuum6CtO8rm79SF6ATJsvJTvbviAkoZyZ7OfNnBQTx5tlFpg"

# List of devices to check for pending tasks.
DEVICES = ["andreas-ceos-pe1", "andreas-ceos-pe2"]

def create_grpc_channel(server: str, token: str) -> grpc.Channel:
    """
    Creates a gRPC secure channel with the provided token.
    This is a simplified version of the example you provided,
    assuming no custom certificate is needed.

    Args:
        server (str): The address of the CV instance to connect to (e.g., "<host>:<port>").
        token (str): The authentication token.

    Returns:
        grpc.Channel: The gRPC channel.
    """
    call_creds = grpc.access_token_call_credentials(token)
    channel_creds = grpc.ssl_channel_credentials()
    conn_creds = grpc.composite_channel_credentials(channel_creds, call_creds)

    return grpc.secure_channel(server, conn_creds)

def get_pending_tasks(channel: grpc.Channel, device_list: List[str]) -> List[str]:
    """
    This is a conceptual function. The Arista change control API you provided
    does not have a direct method for "getting pending tasks". In a real-world
    scenario, you would use the appropriate rAPI stub (e.g., from the
    "task" service) to retrieve this information.

    For this example, we will simulate a list of pending tasks to demonstrate
    the change control creation process.

    Args:
        channel (grpc.Channel): The gRPC channel.
        device_list (List[str]): A list of device IDs to check.

    Returns:
        List[str]: A list of task IDs that are pending.
    """
    logging.info(f"Fetching pending tasks for devices: {device_list}")
    # In a real script, this would be a gRPC call.
    # e.g., using a TaskServiceStub and a GetTasksRequest
    # For now, we return a dummy list to show the next steps work.
    
    # We will use a dummy task ID that represents the task of applying configs.
    # In a real-world scenario, this ID would be retrieved from the API.
    pending_task_id = f"task-apply-configs-{str(uuid4())}"
    
    logging.info(f"Found 1 conceptual pending task: {pending_task_id}")
    return [pending_task_id]

def create_change_control_job(channel: grpc.Channel, task_ids: List[str]) -> Dict:
    """
    Creates a new change control job with a single stage containing the given tasks.

    Args:
        channel (grpc.Channel): The gRPC channel.
        task_ids (List[str]): A list of task IDs to include in the job.

    Returns:
        Dict: The created Change Control object details.
    """
    cc_id = str(uuid4())
    cc_name = f"Automated Change Control Job for {', '.join(task_ids)}"
    root_stage_id = "stage-root"
    action_stage_id = f"stage-action-{cc_id}"
    action_id = "applyDeviceConfigs"
    
    logging.info(f"\nCreating Change Control with ID {cc_id}")
    
    # Define the arguments for the action. Note that the values must be strings.
    # The user's example uses a string map for args, so we must serialize our data.
    action_args = {
        "device_ids": json.dumps(DEVICES),
        "task_ids": json.dumps(task_ids)
    }

    # Define the action to be run, wrapping the arguments in the fmp wrapper.
    action = models.Action(
        name=wrappers.StringValue(value=action_id),
        args=fmp_wrappers.MapStringString(values=action_args),
    )

    # Define the action stage
    action_stage_config = models.StageConfig(
        name=wrappers.StringValue(value=f"Scheduled action {action_id}"),
        action=action
    )
    
    # Define the root stage which references the action stage
    root_stage_config = models.StageConfig(
        name=wrappers.StringValue(value=f"{cc_name} Root"),
        rows=models.RepeatedRepeatedString(
            # The inner list must be of fmp_wrappers.RepeatedString, as per the example
            values=[fmp_wrappers.RepeatedString(values=[action_stage_id])]
        )
    )
    
    # Build the stage config map
    stage_config_map = models.StageConfigMap(
        values={
            root_stage_id: root_stage_config,
            action_stage_id: action_stage_config
        }
    )
    
    change_config = models.ChangeConfig(
        name=wrappers.StringValue(value=cc_name),
        root_stage_id=wrappers.StringValue(value=root_stage_id),
        stages=stage_config_map,
        notes=wrappers.StringValue(value="Created and managed by script")
    )
    
    key = models.ChangeControlKey(id=wrappers.StringValue(value=cc_id))
    set_req = services.ChangeControlConfigSetRequest(
        value=models.ChangeControlConfig(
            key=key,
            change=change_config,
        )
    )
    
    cc_stub = services.ChangeControlConfigServiceStub(channel)
    resp = cc_stub.Set(set_req, timeout=RPC_TIMEOUT)
    logging.info(f"Change Control {cc_id} created successfully at time: {resp.time.ToDatetime()}")
    
    # Return a dictionary representation of the response for readability
    return {
        "id": cc_id,
        "name": cc_name,
        "timestamp": resp.time.ToDatetime().isoformat()
    }

# --- Main Script Execution ---
if __name__ == "__main__":
    with create_grpc_channel(CVAAS_SERVER, API_TOKEN) as channel:
        # Step 1: Get pending tasks
        pending_task_ids = get_pending_tasks(channel, DEVICES)
        
        # Step 2: Create a change control job if there are pending tasks
        if pending_task_ids:
            new_job_details = create_change_control_job(channel, pending_task_ids)
            print("\nNew Job Details:")
            print(json.dumps(new_job_details, indent=2))
        else:
            logging.info("\nNo change control job was created because there were no pending tasks.")

