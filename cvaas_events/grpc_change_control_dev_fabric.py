import argparse
import grpc
import json
import arista.changecontrol.v1
from google.protobuf.json_format import Parse

RPC_TIMEOUT = 30  # in seconds

# List of device IDs to filter
DEVICE_IDS = {
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

def main(args):
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
        # Iterate through the stream and filter responses
        for response in tag_stub.GetAll(req, timeout=RPC_TIMEOUT):
            # Check if the response has a value and the required fields
            if hasattr(response, 'value') and hasattr(response.value, 'status') and hasattr(response.value, 'device_id'):
                # Filter for COMPLETED status and matching device ID
                if (response.value.status == arista.changecontrol.v1.CHANGE_CONTROL_STATUS_COMPLETED and
                    response.value.device_id.value in DEVICE_IDS):
                    print(response)

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
