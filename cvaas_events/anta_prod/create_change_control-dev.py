import grpc
import logging
import json
import os
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
from google.protobuf.timestamp_pb2 import Timestamp

RPC_TIMEOUT = 30  # in seconds

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Configuration ---
# Your CVaaS server and API token.
CVAAS_SERVER = "www.cv-staging.corp.arista.io:443"
# IMPORTANT: Replace the placeholder below with your valid API token.
API_TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJkaWQiOjQyOTc4NzE4MDQsImRzbiI6ImFuZHJlYXNfYXZkIiwiZHN0IjoiYWNjb3VudCIsImV4cCI6MTkwMzU1NzU5OSwiaWF0IjoxNzQ3MzkwODE4LCJvZ2kiOjkwODE1LCJvZ24iOiJhcmlzdGEtc2Utbm9yZGljIiwic2lkIjoiZDZhNzZhZmIyYTk2ZDExNjUyMWQxYWYyNmE3ZTFhMzBjNTgyMTFmMzJjNWNmMmFlZWI3YWUxZjcxN2NkOTQ5Ny1VdHFpRzdNN2ZVcVNnSXhfc3BLOTZldnVnSWlaYjhpYnhKZUZlYXFMIn0.ZsVOGt4gtDCzvHYPbdmm1pJ06XIOoy5xOfnk-qYuum6CtO8rm79SF6ATJsvJTvbviAkoZyZ7OfNnBQTx5tlFpg"
# IMPORTANT: Provide the path to your certificate file if required, otherwise leave as None.
CERT_FILE = None

# List of devices to check for pending tasks.
DEVICES = ["andreas-ceos-pe1", "andreas-ceos-pe2"]

def create_grpc_channel(server: str, token: str, cert_file_path: str = None) -> grpc.Channel:
    """
    Creates a grpc secure channel with the provided token and optional certificate.

    Args:
        server (str): Address of the CV instance to connect to (e.g., "<host>:<port>").
        token (str): The authentication token.
        cert_file_path (str, optional): Path to a file containing the self-signed cert.

    Returns:
        grpc.Channel: A channel that rAPI stubs can use.
    """
    call_creds = grpc.access_token_call_credentials(token)

    if cert_file_path and os.path.exists(cert_file_path):
        with open(cert_file_path, 'rb') as f:
            cert = f.read()
        channel_creds = grpc.ssl_channel_credentials(root_certificates=cert)
    else:
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
    
    pending_task_id = f"task-apply-configs-{str(uuid4())}"
    
    logging.info(f"Found 1 conceptual pending task: {pending_task_id}")
    return [pending_task_id]

def addCC(channel: grpc.Channel, ccID: str, actionsAndArgs: Dict[str, Dict[str, str]]) -> Timestamp:
    """
    Creates a Change Control of the given ID and returns the Timestamp for approval.
    Based on the example you provided.
    """
    logging.info(f"Creating Change Control with ID {ccID}")
    ccName = "Automated Change Control Job"
    rootStageId = "stage-root"
    rootStageRows = []
    stageConfigMapDict = {}
    for actionID, args in actionsAndArgs.items():
        currActionID = f"stage-action-{actionID}"
        action = models.Action(
            name=wrappers.StringValue(value=actionID),
            args=fmp_wrappers.MapStringString(values=args),
        )
        rootStageRows.append(fmp_wrappers.RepeatedString(values=[currActionID]))
        stageConfigMapDict[currActionID] = models.StageConfig(
            name=wrappers.StringValue(value=f"Scheduled action {actionID}"),
            action=action
        )

    stageConfigMapDict[rootStageId] = models.StageConfig(
        name=wrappers.StringValue(value=f"{ccName} Root"),
        rows=models.RepeatedRepeatedString(
            values=rootStageRows
        )
    )
    stageConfigMap = models.StageConfigMap(
        values=stageConfigMapDict
    )
    changeConfig = models.ChangeConfig(
        name=wrappers.StringValue(value=ccName),
        root_stage_id=wrappers.StringValue(value=rootStageId),
        stages=stageConfigMap,
        notes=wrappers.StringValue(value="Created and managed by script")
    )
    key = models.ChangeControlKey(id=wrappers.StringValue(value=ccID))
    setReq = services.ChangeControlConfigSetRequest(
        value=models.ChangeControlConfig(
            key=key,
            change=changeConfig,
        )
    )

    cc_stub = services.ChangeControlConfigServiceStub(channel)
    resp = cc_stub.Set(setReq, timeout=RPC_TIMEOUT)
    logging.info(f"Change Control {ccID} created successfully at time: {resp.time.ToDatetime()}")
    return resp.time

def approveCC(channel: grpc.Channel, ccID: str, ts: Timestamp):
    """
    Approves a Change Control of the given ID and Timestamp.
    Based on the example you provided.
    """
    logging.info(f"Approving Change Control with ID {ccID}")
    key = models.ChangeControlKey(id=wrappers.StringValue(value=ccID))
    setReq = services.ApproveConfigSetRequest(
        value=models.ApproveConfig(
            key=key,
            approve=models.FlagConfig(
                value=wrappers.BoolValue(value=True),
            ),
            version=ts
        )
    )
    cc_apr_stub = services.ApproveConfigServiceStub(channel)
    cc_apr_stub.Set(setReq, timeout=RPC_TIMEOUT)
    logging.info(f"Change Control {ccID} approved successfully")

def executeCC(channel: grpc.Channel, ccID: str):
    """
    Executes an approved Change Control of the given ID.
    Based on the example you provided.
    """
    logging.info(f"Executing Change Control with ID {ccID}")
    key = models.ChangeControlKey(id=wrappers.StringValue(value=ccID))
    setReq = services.ChangeControlConfigSetRequest(
        value=models.ChangeControlConfig(
            key=key,
            start=models.FlagConfig(
                value=wrappers.BoolValue(value=True),
            ),
        )
    )
    cc_stub = services.ChangeControlConfigServiceStub(channel)
    cc_stub.Set(setReq, timeout=RPC_TIMEOUT)
    logging.info(f"Change Control {ccID} executed successfully")

def subscribeToCCStatus(channel: grpc.Channel, ccID: str):
    """
    Subscribes to a Change Control and monitors it until completion.
    Based on the example you provided.
    """
    logging.info(f"Subscribing to {ccID} to monitor for completion")
    key = models.ChangeControlKey(id=wrappers.StringValue(value=ccID))
    subReq = services.ChangeControlStreamRequest()
    subReq.partial_eq_filter.append(models.ChangeControl(key=key))

    cc_stub = services.ChangeControlServiceStub(channel)
    for resp in cc_stub.Subscribe(subReq, timeout=RPC_TIMEOUT):
        if resp.value.status == models.CHANGE_CONTROL_STATUS_COMPLETED:
            if resp.value.error and resp.value.error.value:
                err = resp.value.error.value
                logging.info(f"Changecontrol {ccID} completed with error: {err}")
            else:
                logging.info(f"Changecontrol {ccID} completed successfully")
            break

# --- Main Script Execution ---
if __name__ == "__main__":
    try:
        with create_grpc_channel(CVAAS_SERVER, API_TOKEN, CERT_FILE) as channel:
            # Step 1: Get pending tasks (conceptual)
            pending_task_ids = get_pending_tasks(channel, DEVICES)
            
            if pending_task_ids:
                cc_id = str(uuid4())
                
                # Step 2: Define actions to be run in the change control
                # We are using "Update Config" based on your input.
                actions_and_args = {
                    "Update Config": {
                        "device_ids": json.dumps(DEVICES),
                        "task_ids": json.dumps(pending_task_ids)
                    }
                }
                
                # Step 3: Create the change control job
                ts = addCC(channel, cc_id, actions_and_args)
                
                # Step 4: Commented out because you want to approve manually
                # approveCC(channel, cc_id, ts)
                
                # Step 5: Commented out because you want to approve manually
                # executeCC(channel, cc_id)
                
                # Step 6: Subscribe to the change control status for completion
                subscribeToCCStatus(channel, cc_id)
            else:
                logging.info("\nNo change control job was created because there were no pending tasks.")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
            logging.error("Authentication failed. This could be due to an invalid or expired API token, or a lack of necessary permissions. Please check your token and its permissions in the CVaaS console.")
        elif e.code() == grpc.StatusCode.FAILED_PRECONDITION:
            logging.error(f"The action ID is invalid. Details: {e.details()}")
            logging.error("The action ID 'Update Config' was rejected by the server. Please double-check that this is the exact name of the action in your CVaaS UI, as it may be case-sensitive or have slight variations.")
        else:
            logging.error(f"An unexpected gRPC error occurred: {e}")

