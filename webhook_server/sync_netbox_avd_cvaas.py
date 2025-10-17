import subprocess
import os
import hmac
import hashlib
import sys
import requests 
from flask import Flask, request, jsonify
from rich import print
from rich.console import Console
from datetime import datetime
import threading
import time
from waitress import serve
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv() 

# Flask app setup
app = Flask(__name__)
console = Console()

# --- CONFIGURATION ---
NETBOX_WEBHOOK_SECRET = os.environ.get("NETBOX_WEBHOOK_SECRET")
GITEA_WEBHOOK_SECRET = os.environ.get("GITEA_WEBHOOK_SECRET")

ENV_FILE = "/home/andreasm/environment/netbox-env.sh"
REPO_PATH = "/home/andreasm/avd_cv_deploy_cvaas"
ANTA_PLAYBOOK = f"{REPO_PATH}/anta.yml"
PLAYBOOKS = [
    f"{REPO_PATH}/1-playbook-update_inventory-dev-prod.yml",
    f"{REPO_PATH}/2-playbook-update_dc1_yml_according_to_inventory.yml",
    f"{REPO_PATH}/3-playbook-update_network_services.yml",
    f"{REPO_PATH}/4-playbook-update_connected_endpoints.yml"
]


def print_startup_sequence():
    """Prints a cool startup banner and status."""
    ascii_art = """
    [bold cyan]
        ____  ____  ____  ____  ____  ____
       /    \/    \/    \/    \/    \/    \\
      /__________/\__________/\__________/\\
      |  NETBOX-AVD SYNC WEBHOOK SERVER  |
      |__________________________________|
    [/bold cyan]
    """
    console.print(ascii_art)
    console.print("[bold yellow]Powered by Flask, Waitress, and Rich[/bold yellow]")
    for i in range(3):
        console.print(f"\r[bold magenta]Initializing systems {3 - i}...[/bold magenta]", end="")
        time.sleep(1)
    console.print("\r[bold green]🚀 SERVER ONLINE![/bold green]")
    console.print("[bold cyan]====================================[/bold cyan]")
    console.print("[bold white]🔥 Running on all addresses (0.0.0.0)[/bold white]")
    console.print(f"[bold white]🌍 Network: http://{os.environ.get('SERVER_IP', '10.100.5.11')}:5000[/bold white]")
    console.print("[bold cyan]====================================[/bold cyan]")
    console.print("[bold red]Press CTRL+C to shut down the galaxy![/bold red]")


def run_ansible_playbooks(vlan_tag_id=None):
    """Runs the list of Ansible playbooks, passing the VLAN Tag ID."""
    for playbook in PLAYBOOKS:
        try:
            playbook_name = os.path.basename(playbook)
            print(f"[bold blue]🚀 Running Ansible Playbook: {playbook_name} for VLAN Tag {vlan_tag_id or 'N/A'}[/bold blue]")
            
            extra_vars = f"-e 'netbox_vlan_id={vlan_tag_id}'" if vlan_tag_id else ""
            command = f"source {ENV_FILE} && ansible-playbook {playbook} {extra_vars}"
            
            result = subprocess.run(
                ["bash", "-c", command], cwd=REPO_PATH, capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"[bold green]✔️ Playbook {playbook_name} executed successfully[/bold green]")
                console.print(f"[bold green]📜 {playbook_name} Output:[/bold green]", style="green")
                console.print(result.stdout, style="cyan")
            else:
                print(f"[bold red]❌ Playbook {playbook_name} failed:[/bold red] {result.stderr}")
                return False
        except subprocess.CalledProcessError as e:
            print(f"[bold red]❌ Error executing playbook {playbook_name}:[/bold red] {e.stderr}")
            return False
    return True


def create_branch_and_push(vlan_data=None):
    """Creates a new branch, runs playbooks, commits with BOTH IDs, and pushes."""
    # Extract IDs from the dictionary if it exists
    vlan_db_id = vlan_data.get('vlan_db_id') if vlan_data else None
    vlan_tag_id = vlan_data.get('vlan_tag_id') if vlan_data else None

    branch_name = datetime.now().strftime("sync-%Y%m%d-%H%M%S")
    print(f"[bold blue]🔀 Preparing branch: {branch_name}[/bold blue]")
    try:
        os.chdir(REPO_PATH)
        status_result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )
        if status_result.stdout.strip():
            print("[bold red]❌ Main branch has uncommitted changes. Please commit or stash them manually.[/bold red]")
            return False
        subprocess.run(["git", "fetch", "origin"], check=True)
        print(f"[bold green]✔️ Creating new branch: {branch_name}[/bold green]")
        subprocess.run(["git", "checkout", "-b", branch_name, "origin/main"], check=True)
        
        # Pass the VLAN Tag (vid) to the playbook runner
        if not run_ansible_playbooks(vlan_tag_id=vlan_tag_id):
            print("[bold red]❌ One or more playbooks failed, aborting Git operations[/bold red]")
            subprocess.run(["git", "checkout", "main"], check=True)
            subprocess.run(["git", "branch", "-D", branch_name], check=True)
            return False
            
        subprocess.run(["git", "add", "."], check=True)
        
        # Commit message includes BOTH IDs for the Gitea pipeline
        commit_message = f"Auto-sync triggered at {branch_name}"
        if vlan_db_id and vlan_tag_id:
            commit_message += f" for VLAN Tag: {vlan_tag_id} (DB_ID: {vlan_db_id})"
            
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message], capture_output=True, text=True
        )
        if "nothing to commit" in commit_result.stdout.lower():
            print(f"[bold yellow]⚠️ No changes detected, skipping push.[/bold yellow]")
            subprocess.run(["git", "checkout", "main"], check=True)
            subprocess.run(["git", "branch", "-D", branch_name], check=True)
            print(f"[bold green]✔️ Deleted branch '{branch_name}'[/bold green]")
            return False
            
        print(f"[bold green]⬆️ Pushing branch: {branch_name} to remote[/bold green]")
        subprocess.run(["git", "push", "origin", branch_name], check=True)
        print(f"[bold green]✔️ Successfully pushed branch {branch_name}[/bold green]")
        subprocess.run(["git", "checkout", "main"], check=True)
        return True
    except Exception as e:
        print(f"[bold red]❌ Git/Ansible process failed: {e}[/bold red]")
        subprocess.run(["git", "checkout", "main"], check=True)
        return False


def run_anta_playbook():
    """Pulls changes, runs ANTA playbook, and conditionally commits/pushes results."""
    ALLOWED_PATHS_TO_COMMIT = ["reports/", "intended/test_catalogs/"]
    try:
        console.print(f"[bold blue]🔄 Pulling latest changes from git in {REPO_PATH}...[/bold blue]")
        subprocess.run(["git", "checkout", "main"], cwd=REPO_PATH, check=True, capture_output=True)
        subprocess.run(["git", "pull", "origin", "main"], cwd=REPO_PATH, check=True, capture_output=True)
        console.print("[bold green]✔️ Git pull successful on main branch.[/bold green]")
        playbook_name = os.path.basename(ANTA_PLAYBOOK)
        console.print(f"[bold blue]🚀 Running ANTA Playbook: {playbook_name}[/bold blue]")
        command = f"source {ENV_FILE} && ansible-playbook -i inventory.yml {ANTA_PLAYBOOK}"
        result = subprocess.run(["bash", "-c", command], cwd=REPO_PATH, capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"[bold green]✔️ Playbook {playbook_name} executed successfully[/bold green]")
        else:
            console.print(f"[bold red]❌ Playbook {playbook_name} failed. Aborting commit.[/bold red]")
            console.print(result.stderr)
            return
        console.print("[bold blue]🔎 Checking for changes in specified directories...[/bold blue]")
        status_result = subprocess.run(
            ["git", "status", "--porcelain"] + ALLOWED_PATHS_TO_COMMIT,
            cwd=REPO_PATH, capture_output=True, text=True, check=True
        )
        if not status_result.stdout.strip():
            console.print("[bold yellow]⚠️ No changes detected in reports/ or intended/test_catalogs/. Nothing to commit.[/bold yellow]")
            return
        console.print("[bold green]✔️ Relevant changes found. Proceeding with commit.[/bold green]")
        subprocess.run(["git", "add"] + ALLOWED_PATHS_TO_COMMIT, cwd=REPO_PATH, check=True)
        commit_message = f"Auto-commit ANTA reports at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_message], cwd=REPO_PATH, check=True)
        console.print(f"[bold green]✔️ Committed changes with message: '{commit_message}'[/bold green]")
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_PATH, check=True)
        console.print("[bold green]🚀 Successfully pushed changes to main branch.[/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ A git or ansible process failed:[/bold red]")
        console.print(e.stderr)
    except Exception as e:
        console.print(f"[bold red]❌ An unexpected error occurred:[/bold red] {str(e)}")


def get_file_hash(filepath):
    """Calculates and returns the SHA256 hash of a file's content."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def update_local_repo():
    """Checks out main and pulls the latest changes."""
    console.print("[bold blue]GIT_UPDATE: Gitea webhook received. Pulling latest changes...[/bold blue]")
    try:
        subprocess.run(["git", "checkout", "main"], cwd=REPO_PATH, check=True, capture_output=True)
        subprocess.run(["git", "pull", "origin", "main"], cwd=REPO_PATH, check=True, capture_output=True)
        console.print("[bold green]GIT_UPDATE: ✔️ Repository updated successfully.[/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]GIT_UPDATE: ❌ Git pull failed:[/bold red] {e.stderr}")
    except Exception as e:
        console.print(f"[bold red]GIT_UPDATE: ❌ An unexpected error occurred:[/bold red] {str(e)}")


@app.route('/status', methods=['GET'])
def get_status():
    """An endpoint for the NetBox plugin to query the real-time hash of the status file."""
    console.print("[bold cyan]ℹ️ Received status request from NetBox plugin...[/bold cyan]")
    status_file = f"{REPO_PATH}/status/latest_cvaas_cc_job.name"
    current_hash = get_file_hash(status_file)
    if current_hash:
        console.print(f"[bold green]✔️ Found file, hash: {current_hash}[/bold green]")
        return jsonify({"status": "ok", "file_hash": current_hash}), 200
    else:
        console.print(f"[bold red]❌ Status file not found at: {status_file}[/bold red]")
        return jsonify({"status": "error", "message": "Status file not found"}), 404


@app.route('/latest-report', methods=['GET'])
def get_latest_report():
    """An endpoint for the NetBox plugin to get the content of the latest report file."""
    console.print("[bold cyan]ℹ️ Received latest report request from NetBox plugin...[/bold cyan]")
    report_file_path = f"{REPO_PATH}/reports/ANDREAS_FABRIC-state.md"
    try:
        with open(report_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        console.print("[bold green]✔️ Found and returned report file content.[/bold green]")
        return jsonify({"status": "ok", "report_content": content}), 200
    except FileNotFoundError:
        console.print(f"[bold red]❌ Report file not found at: {report_file_path}[/bold red]")
        error_message = f"## Report Not Found\n\nThe report file (`{os.path.basename(report_file_path)}`) was not found on the server."
        return jsonify({"status": "ok", "report_content": error_message}), 200
    except Exception as e:
        console.print(f"[bold red]❌ Error reading report file: {str(e)}[/bold red]")
        return jsonify({"status": "error", "message": f"Server error reading file: {str(e)}"}), 500


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handles incoming webhooks from the NetBox Plugin."""
    console.print("[bold blue]ℹ️ NETBOX Webhook received...[/bold blue]")
    raw_data = request.get_data()

    # Validate webhook secret
    received_secret = request.headers.get('X-Hook-Signature')
    expected_secret = hmac.new(NETBOX_WEBHOOK_SECRET.encode('utf-8'), raw_data, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(received_secret or '', expected_secret):
        console.print("[bold red]❌ Invalid or missing NetBox webhook secret[/bold red]")
        return jsonify({"error": "Invalid or missing webhook secret"}), 403

    try:
        data = request.get_json()
    except Exception as e:
        console.print(f"[bold red]❌ Error parsing JSON:[/bold red] {str(e)}")
        return jsonify({"error": "Invalid JSON"}), 400

    event_type = data.get('event')
    console.print(f"[bold yellow]Received event type: {event_type}[/bold yellow]")

    if event_type == "vlan_created":
        vlan_data = data.get('data', {})
        if not vlan_data.get('vlan_db_id') or not vlan_data.get('vlan_tag_id'):
            console.print(f"[bold red]❌ Event '{event_type}' received without complete VLAN data.[/bold red]")
            return jsonify({"error": "Missing vlan_db_id or vlan_tag_id for this event"}), 400

        console.print(f"[bold blue]🔄 Processing VLAN creation for DB_ID: {vlan_data['vlan_db_id']}, Tag: {vlan_data['vlan_tag_id']}...[/bold blue]")
        thread = threading.Thread(target=create_branch_and_push, args=(vlan_data,))
        thread.start()
        return jsonify({"message": f"VLAN sync process started for DB_ID {vlan_data['vlan_db_id']}."}), 202

    elif event_type == "manual_sync":
        console.print(f"[bold blue]🔄 Processing generic manual sync triggered at {data.get('timestamp')}[/bold blue]")
        thread = threading.Thread(target=create_branch_and_push, args=(None,))
        thread.start()
        return jsonify({"message": "Generic manual sync process started in the background."}), 202

    elif event_type == "run_anta_test":
        console.print(f"[bold blue]🔬 Processing ANTA test triggered at {data.get('timestamp')}[/bold blue]")
        thread = threading.Thread(target=run_anta_playbook)
        thread.start()
        return jsonify({"message": "ANTA test started in the background"}), 202

    else:
        console.print(f"[bold red]❌ Unknown event type: {event_type}[/bold red]")
        return jsonify({"error": "Unknown event type"}), 400

@app.route('/gitea-webhook', methods=['POST'])
def handle_gitea_webhook():
    """Handles incoming webhooks from Gitea to trigger a git pull."""
    console.print("[bold blue]ℹ️ GITEA Webhook received...[/bold blue]")
    gitea_signature = request.headers.get('X-Gitea-Signature')
    if not gitea_signature:
        return jsonify({"error": "Missing signature"}), 403
    expected_signature = hmac.new(GITEA_WEBHOOK_SECRET.encode('utf-8'), request.get_data(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(gitea_signature, expected_signature):
        console.print("[bold red]GITEA_WEBHOOK: ❌ Invalid Gitea webhook secret[/bold red]")
        return jsonify({"error": "Invalid signature"}), 403

    data = request.get_json()
    if data.get('ref') != 'refs/heads/main':
        console.print(f"[bold yellow]GITEA_WEBHOOK: Ignoring push to non-main branch ({data.get('ref')})[/bold yellow]")
        return jsonify({"message": "Ignoring non-main branch push"}), 200

    thread = threading.Thread(target=update_local_repo)
    thread.start()
    return jsonify({"message": "Webhook received, update process started"}), 202


if __name__ == "__main__":
    if not NETBOX_WEBHOOK_SECRET or not GITEA_WEBHOOK_SECRET:
         console.print("[bold red]FATAL: NETBOX_WEBHOOK_SECRET or GITEA_WEBHOOK_SECRET environment variables are not set. Check your .env file.[/bold red]")
         sys.exit(1)
        
    print_startup_sequence()
    serve(app, host="0.0.0.0", port=5000)
