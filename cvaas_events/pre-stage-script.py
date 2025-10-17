import argparse
import grpc
import json
import arista.changecontrol.v1
from google.protobuf.json_format import Parse, MessageToDict

RPC_TIMEOUT = 300  # in seconds

def trigger_action(device_ids):
    """
    Custom action to be triggered when CHANGE_CONTROL_STATUS_COMPLETED is detected.
    Writes to devices_changed.txt for valid device IDs.
    """
    # List of valid device IDs
    valid_device_ids = {
        "2E85018A64223A538DF7998034B03EDC",
        "4F29E152080FCEFB29DB756B4F2C3577",
        "9AAEE15EEB3A18FADDA20C1BACDB76F8",
        "9CDD2323393E14468FC22C4AF1F1D99B",
        "B52C1D9B0CA30A90F2A9E7046D573EE6",
        "CEEEDE54D6FC6582BC75FF7E2B8FCE2D",
        "D264759BAB01E3100E3A85704B65CBA1",
        "F61379FA1B345E2FFDD5FB1B156FB329",
        "2AB9BDD18A71C07B6A8A953AD88601E1",
        "BBF97A93C142AB9A11F2C3358FAA6A8C"
    }

    for device_id in device_ids:
        if device_id in valid_device_ids:
            print(f"Triggering action for device ID: {device_id}")
            with open("devices_changed.txt", "a") as log_file:
                log_file.write(f"Change control completed for device ID: {device_id}\n")
        else:
            print(f"Skipping unknown device ID: {device_id}")

def main(args):
    # Dictionary to store mapping of change control ID to device IDs
    change_to_device_ids = {}

    # read the file containing a session token to authenticate with
    token = args.token_file.read().strip()
    # create the header object for the token
    callCreds = grpc.access_token_call_credentials(token)

    # if using a self-signed certificate (should be provided as arg)
    if args.cert_file:
        # create the channel using the self-signed cert
        cert = args.cert_file.read()
        channelCreds = grpc.ssl_channel_credentials(root_certificates=cert)
    else:
        # otherwise default to checking against CAs
        channelCreds = grpc.ssl_channel_credentials()
    connCreds = grpc.composite_channel_credentials(channelCreds, callCreds)

    json_request = json.dumps({})
    req = Parse(json_request, arista.changecontrol.v1.services.ChangeControlStreamRequest(), False)

    # initialize a connection to the server using our connection settings (auth + TLS)
    with grpc.secure_channel(args.server, connCreds) as channel:
        tag_stub = arista.changecontrol.v1.services.ChangeControlServiceStub(channel)

        try:
            print("Attempting to subscribe to Change Control events...")
            for event in tag_stub.Subscribe(req, timeout=RPC_TIMEOUT):
                print("Received event:")
                print(event)  # Print the protobuf message object

                try:
                    # Convert protobuf message to dictionary for easier processing
                    event_dict = MessageToDict(event, preserving_proto_field_name=True)

                    # Handle INITIAL_SYNC_COMPLETE event separately
                    if event_dict.get("type") == "INITIAL_SYNC_COMPLETE":
                        device_ids = event_dict.get("device_ids", {}).get("values", [])
                        if device_ids:
                            print(f"INITIAL_SYNC_COMPLETE device IDs: {device_ids}")
                        continue  # Skip further processing for this event

                    # Ensure event_dict["value"] is a dictionary
                    if not isinstance(event_dict.get("value"), dict):
                        print(f"Skipping event: 'value' is not a dictionary, got {event_dict.get('value')}")
                        continue

                    # Extract change control ID from value.key
                    value_dict = event_dict.get("value", {})
                    key_field = value_dict.get("key", "Unknown")
                    if isinstance(key_field, dict):
                        change_control_id = key_field.get("value", "Unknown")
                    else:
                        change_control_id = key_field  # Use string directly
                    if change_control_id == "Unknown":
                        print(f"Skipping event: Invalid or missing change control ID")
                        continue

                    # Update device ID mapping
                    device_ids_dict = value_dict.get("device_ids", {})
                    if not isinstance(device_ids_dict, dict):
                        print(f"Skipping device_ids: 'device_ids' is not a dictionary, got {device_ids_dict}")
                    else:
                        device_ids = device_ids_dict.get("values", [])
                        if device_ids:
                            change_to_device_ids[change_control_id] = device_ids
                            print(f"Updated device IDs for change control {change_control_id}: {device_ids}")

                    # Check for CHANGE_CONTROL_STATUS_COMPLETED
                    status = value_dict.get("status", "")
                    if status == "CHANGE_CONTROL_STATUS_COMPLETED":
                        # Get device IDs from the mapping
                        device_ids = change_to_device_ids.get(change_control_id, [])
                        if device_ids:
                            print(f"Detected CHANGE_CONTROL_STATUS_COMPLETED for device IDs: {device_ids}")
                            trigger_action(device_ids)
                        else:
                            print(f"No device IDs found for change control ID: {change_control_id}")

                except Exception as e:
                    # Log any errors during event processing
                    print(f"Error processing event: {e}")
                    print(f"Event content: {event}")

        except grpc.RpcError as e:
            # gRPC specific errors
            print(f"gRPC Error: {e.code()} - {e.details()}")
            if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                print("Authentication failed. Check your token's validity and permissions.")
            elif e.code() == grpc.StatusCode.UNAVAILABLE:
                print("Server unavailable. Check the server address and connectivity.")
            elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                print("RPC Deadline Exceeded. The server did not respond within the timeout.")
            elif e.code() == grpc.StatusCode.CANCELLED:
                print("The RPC was cancelled (e.g., by the client closing the connection).")
            else:
                print("An unexpected gRPC error occurred.")
        except Exception as e:
            # Catch any other unexpected Python errors
            print(f"An unexpected Python error occurred: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--server',
        required=True,
        help="CloudVision server to connect to in <host>:<port> format")
    parser.add_argument("--token-file", required=True,
                        type=argparse.FileType('r'), help="file with access token")
    parser.add_argument("--cert-file", type=argparse.FileType('rb'),
                        help="certificate to use as root CA")
    args = parser.parse_args()
    main(args)
