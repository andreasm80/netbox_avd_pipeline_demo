import argparse
import grpc
import json
import arista.changecontrol.v1
from google.protobuf.json_format import Parse, MessageToJson
import os
import datetime
import pytz

RPC_TIMEOUT = 300  # in seconds

def main(args):
    token = args.token_file.read().strip()
    callCreds = grpc.access_token_call_credentials(token)

    if args.cert_file:
        cert = args.cert_file.read()
        channelCreds = grpc.ssl_channel_credentials(root_certificates=cert)
    else:
        channelCreds = grpc.ssl_channel_credentials()
    connCreds = grpc.composite_channel_credentials(channelCreds, callCreds)

    json_request = json.dumps({})
    req = Parse(json_request, arista.changecontrol.v1.services.ChangeControlStreamRequest(), False)

    TARGET_DEVICE_IDS = [
        "9AAEE15EEB3A18FADDA20C1BACDB76F8"
    ]
    TARGET_STATUS = "CHANGE_CONTROL_STATUS_COMPLETED"

    output_file_path = "completed_change_controls_new_events.txt"

    with grpc.secure_channel(args.server, connCreds) as channel:
        tag_stub = arista.changecontrol.v1.services.ChangeControlServiceStub(channel)
        print("Subscribed to ChangeControl events. Waiting for real-time updates...")
        print(f"Filtered events will be written to: {output_file_path}")

        # Record the start time of the subscription in UTC
        # We add a small buffer (e.g., 1 second) to account for any network latency/processing time
        subscription_start_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc) - datetime.timedelta(seconds=1)
        print(f"Only processing events generated after: {subscription_start_time}")

        try:
            with open(output_file_path, 'a') as f:
                for response in tag_stub.Subscribe(req, timeout=RPC_TIMEOUT):
                    response_json_str = MessageToJson(response, preserving_proto_field_name=True, indent=2)
                    response_data = json.loads(response_json_str)

                    # Extract the event time
                    event_time_str = response_data.get('time')
                    if not event_time_str:
                        continue

                    try:
                        # CloudVision timestamps can have nanosecond precision, which fromisoformat
                        # doesn't handle directly (it supports microseconds).
                        # We need to truncate the fractional seconds to microseconds (6 digits)
                        # or handle the 'Z' (UTC) indicator.

                        # First, remove 'Z' and split at '.'
                        parts = event_time_str.rstrip('Z').split('.')
                        main_part = parts[0] # YYYY-MM-DDTHH:MM:SS

                        # Handle fractional seconds, truncate to microseconds (6 digits)
                        if len(parts) > 1:
                            fractional_seconds = parts[1]
                            if len(fractional_seconds) > 6:
                                fractional_seconds = fractional_seconds[:6] # Truncate to microseconds
                            # Reconstruct the string for fromisoformat
                            parsed_time_str = f"{main_part}.{fractional_seconds}+00:00"
                        else:
                            parsed_time_str = f"{main_part}+00:00" # No fractional seconds

                        event_time = datetime.datetime.fromisoformat(parsed_time_str)
                        event_time = event_time.replace(tzinfo=pytz.utc)

                    except ValueError as e:
                        print(f"Warning: Could not parse event time '{event_time_str}': {e}")
                        continue

                    # Check if the event was generated *after* the script started the subscription
                    if event_time > subscription_start_time:
                        event_status = response_data.get('value', {}).get('status')
                        if event_status == TARGET_STATUS:
                            device_ids_in_event = response_data.get('value', {}).get('device_ids', {}).get('values', [])

                            if any(device_id in TARGET_DEVICE_IDS for device_id in device_ids_in_event):
                                print(f"Found a matching NEW event for status '{TARGET_STATUS}' and device_ids: {device_ids_in_event}")
                                f.write(response_json_str)
                                f.write("\n---\n")

        except grpc.RpcError as e:
            print(f"Error during subscription: {e}")
        except KeyboardInterrupt:
            print("Subscription interrupted by user.")
        finally:
            print(f"Script finished. Check '{output_file_path}' for recorded new events.")


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
