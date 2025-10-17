# netbox_env.sh
export NETBOX_URL="https://"
export NETBOX_TOKEN=""
export NETBOX_CERT="certs/netbox_cert.pem"
export CVP_HOST="URL"
export CVP_USER="cvaas"
export CVP_PASSWORD=$(cat /home/andreasm/cvaas_token/cvaas.token)
