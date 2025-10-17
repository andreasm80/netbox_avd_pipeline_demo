import argparse
import grpc
import json
import arista.changecontrol.v1
from google.protobuf.json_format import MessageToJson
import os
import time # Import the time module for sleeping

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

    req = arista.changecontrol.v1.services.ChangeControlStreamRequest()

    TARGET_DEVICE_IDS = [
        "9AAEE15EEB3A18FADDA20C1BACDB76F8"
    ]
    TARGET_STATUS = "CHANGE_CONTROL_STATUS_COMPLETED"

    output_file_path = "completed_change_controls_realtime_waittime.txt"

    # --- NEW STRATEGY VARIABLE ---
    # Define the warmup time in seconds.
    # This is the duration for which the script will listen to the stream
    # but discard all incoming events. This allows historical data to flush.
    WARMUP_TIME_SECONDS = 15 # Adjust this value based on how long initial bursts last
    # --- END NEW STRATEGY VARIABLE ---

    with grpc.secure_channel(args.server, connCreds) as channel:
        tag_stub = arista.changecontrol.v1.services.ChangeControlServiceStub(channel)
        print("Subscribed to ChangeControl events. Performing initial warmup...")
        print(f"Filtered real-time events will be written to: {output_file_path}")
        print(f"Will wait for {WARMUP_TIME_SECONDS} seconds to flush historical events before logging.")

        # --- WARMUP PHASE ---
        start_warmup_time = time.monotonic() # Use monotonic for reliable time measurement
        events_discarded_during_warmup = 0

        # Create an iterator from the subscribe call
        event_iterator = tag_stub.Subscribe(req, timeout=RPC_TIMEOUT)

        print(f"Discarding events for {WARMUP_TIME_SECONDS} seconds...")
        try:
            # Continuously read and discard events until warmup time is over
            while (time.monotonic() - start_warmup_time) < WARMUP_TIME_SECONDS:
                try:
                    # Attempt to read an event, non-blocking if possible (though gRPC iterators block)
                    # This will block until an event comes or timeout occurs,
                    # but the outer loop will continue for the warmup duration.
                    next(event_iterator)
                    events_discarded_during_warmup += 1
                except StopIteration:
                    print("Stream ended during warmup period. No new events will be received.")
                    return # Exit if stream closes unexpectedly
                except grpc.RpcError as e:
                    # Handle potential errors during warmup (e.g., connection issues)
                    print(f"Error during warmup: {e}")
                    return

            print(f"Warmup complete. Discarded {events_discarded_during_warmup} events during warmup.")
            print("\n--- Now processing real-time events. ---\n")

            # --- REAL-TIME PROCESSING PHASE ---
            # From here on, all events received are considered "new" after the warmup.
            # We don't need `seen_change_control_ids` for filtering "newness",
            # but still need `completed_change_control_ids_written` to prevent duplicate writes.
            completed_change_control_ids_written = set()

            with open(output_file_path, 'a') as f:
                for response in event_iterator: # Continue iterating from where warmup left off
                    response_json_str = MessageToJson(response, preserving_proto_field_name=True, indent=2)
                    response_data = json.loads(response_json_str)

                    change_control_id = response_data.get('value', {}).get('key', {}).get('id')
                    current_status = response_data.get('value', {}).get('status')
                    device_ids_in_event = response_data.get('value', {}).get('device_ids', {}).get('values', [])

                    # Filter based on target device IDs
                    if not change_control_id or not any(device_id in TARGET_DEVICE_IDS for device_id in device_ids_in_event):
                        continue

                    # Only process if status is COMPLETED and not already written
                    if current_status == TARGET_STATUS:
                        if change_control_id in completed_change_control_ids_written:
                            continue # Already processed and written this one as completed

                        # This event is a real-time completion for a targeted device
                        event_type = response_data.get('type', 'UNKNOWN')
                        event_time = response_data.get('time', 'N/A')

                        print(f"[{event_type}] Matching REAL-TIME event: Change ID '{change_control_id}' at '{event_time}' for status '{TARGET_STATUS}' and device_ids: {device_ids_in_event}")
                        f.write(response_json_str)
                        f.write("\n---\n")
                        completed_change_control_ids_written.add(change_control_id) # Mark as written

        except grpc.RpcError as e:
            print(f"Error during real-time processing: {e}")
        except KeyboardInterrupt:
            print("Subscription interrupted by user.")
        finally:
            print(f"Script finished. Check '{output_file_path}' for recorded real-time events.")


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
