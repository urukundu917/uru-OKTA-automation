import os
import json
import requests
import argparse
from datetime import datetime

# 🔹 Okta Configuration
OKTA_DOMAIN = "https://dev-14159127-admin.okta.com"  # Replace with your Okta domain
API_TOKEN = os.getenv("OKTA_API_TOKEN")  # API token from environment variable

if not API_TOKEN:
    print("❌ Error: API token is missing. Please set the OKTA_API_TOKEN environment variable.")
    exit(1)

# 🔹 API Headers
headers = {
    "Authorization": f"SSWS {API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# 🔹 Function: Load JSON File
def load_json(file_path):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}

# 🔹 Function: Save Details to `okta_summary.json`
def save_summary(action, entity_type, name, entity_id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_file = "okta_summary.json"
    
    # Load existing summary data if available
    summary_data = []
    if os.path.exists(summary_file) and os.path.getsize(summary_file) > 0:
        try:
            with open(summary_file, "r") as file:
                summary_data = json.load(file)
        except json.JSONDecodeError:
            summary_data = []

    # Append new entry
    summary_data.append({
        "action": action,
        f"{entity_type}_name": name,
        f"{entity_type}_id": entity_id,
        "timestamp": timestamp
    })

    # Save back to file
    with open(summary_file, "w") as file:
        json.dump(summary_data, file, indent=4)

    # Print the configuration details
    print(f"✅ Configuration saved successfully:\n{{\n  \"action\": \"{action}\",\n  \"{entity_type}_name\": \"{name}\",\n  \"{entity_type}_id\": \"{entity_id}\",\n  \"timestamp\": \"{timestamp}\"\n}}")

# 🔹 Function: Create a Group Rule
def create_group_rule(rule_name, attribute, value, group_ids):
    url = f"{OKTA_DOMAIN}/api/v1/groups/rules"
    data = {
        "type": "group_rule",
        "name": rule_name,
        "status": "ACTIVE",
        "conditions": {
            "people": {"users": {"exclude": []}, "groups": {"exclude": []}},
            "expression": {
                "value": f"Arrays.contains(user.{attribute}, \"{value}\")",  # Ensure correct property
                "type": "urn:okta:expression:1.0"
            }
        },
        "actions": {"assignUserToGroups": {"groupIds": group_ids}}
    }
    
    # Print out for debugging purposes
    print(f"Creating group rule with expression: {data['conditions']['expression']['value']}")
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        rule_id = response.json()["id"]
        save_summary("create", "group-rule", rule_name, rule_id)
    else:
        print(f"❌ Failed to create rule: {response.text}")

# 🔹 Main Function to Process Okta Config Based on Action & Type
def process_okta_config(file_path, action, entity_type):
    config = load_json(file_path)

    if action == "create" and entity_type == "group-rule":
        for rule in config.get("create", {}).get("group_rules", []):
            create_group_rule(rule["name"], rule["attribute"], rule["value"], rule["groupIds"])

# 🔹 Run Script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Okta Group Rules")
    parser.add_argument("--action", choices=["create", "update", "delete"], required=True, help="Specify action to perform.")
    parser.add_argument("--type", choices=["group-rule"], required=True, help="Specify type of entity (group-rule).")
    parser.add_argument("--input-file", default="okta_config.json", help="Input JSON file with Okta configurations.")
    
    args = parser.parse_args()
    process_okta_config(args.input_file, args.action, args.type)
