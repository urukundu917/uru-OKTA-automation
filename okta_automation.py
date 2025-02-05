import os
import json
import requests
import argparse
from datetime import datetime

# 🔹 Okta Configuration
OKTA_DOMAIN = "https://dev-14159127-admin.okta.com"
API_TOKEN = os.getenv("OKTA_API_TOKEN")

if not API_TOKEN:
    print("❌ Error: API token is missing. Please set the OKTA_API_TOKEN environment variable.")
    exit(1)

# 🔹 API Headers
headers = {
    "Authorization": f"SSWS {API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# 🔹 Load JSON File
def load_json(file_path):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}

# 🔹 Save Summary to `okta_summary.json`
def save_summary(action, entity_type, name, entity_id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_file = "okta_summary.json"
    
    summary_data = []
    if os.path.exists(summary_file) and os.path.getsize(summary_file) > 0:
        try:
            with open(summary_file, "r") as file:
                summary_data = json.load(file)
        except json.JSONDecodeError:
            summary_data = []

    summary_data.append({
        "action": action,
        f"{entity_type}_name": name,
        f"{entity_type}_id": entity_id,
        "timestamp": timestamp
    })

    with open(summary_file, "w") as file:
        json.dump(summary_data, file, indent=4)

    print(f"✅ Configuration saved:\n{json.dumps(summary_data[-1], indent=4)}")

# 🔹 Group Functions
def create_group(name, description):
    url = f"{OKTA_DOMAIN}/api/v1/groups"
    data = {"type": "OKTA_GROUP", "profile": {"name": name, "description": description}}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        group_id = response.json()["id"]
        save_summary("create", "group", name, group_id)
    else:
        print(f"❌ Failed to create group: {response.text}")

def update_group(group_id, new_name, new_description):
    if not group_id:
        print("⚠️ Skipping update: Missing `group_id`")
        return
    url = f"{OKTA_DOMAIN}/api/v1/groups/{group_id}"
    data = {"profile": {"name": new_name, "description": new_description}}
    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        save_summary("update", "group", new_name, group_id)
    else:
        print(f"❌ Failed to update group: {response.text}")

def delete_group(group_id):
    if not group_id:
        print("⚠️ Skipping delete: Missing `group_id`")
        return
    url = f"{OKTA_DOMAIN}/api/v1/groups/{group_id}"
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        save_summary("delete", "group", group_id, group_id)
    else:
        print(f"❌ Failed to delete group: {response.text}")

# 🔹 Group Rule Functions
def create_group_rule(name, attribute, value, group_ids):
    url = f"{OKTA_DOMAIN}/api/v1/groups/rules"
    data = {
        "type": "group_rule",
        "name": name,
        "status": "ACTIVE",
        "conditions": {"expression": {"value": f"Arrays.contains(user.{attribute}, \"{value}\")", "type": "urn:okta:expression:1.0"}},
        "actions": {"assignUserToGroups": {"groupIds": group_ids}}
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        rule_id = response.json()["id"]
        save_summary("create", "group-rule", name, rule_id)
    else:
        print(f"❌ Failed to create rule: {response.text}")

def update_group_rule(rule_id, name, attribute, value, group_ids):
    if not rule_id:
        print("⚠️ Skipping update: Missing `rule_id`")
        return
    url = f"{OKTA_DOMAIN}/api/v1/groups/rules/{rule_id}"
    data = {
        "name": name,
        "status": "ACTIVE",
        "conditions": {"expression": {"value": f"Arrays.contains(user.{attribute}, \"{value}\")", "type": "urn:okta:expression:1.0"}},
        "actions": {"assignUserToGroups": {"groupIds": group_ids}}
    }
    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        save_summary("update", "group-rule", name, rule_id)
    else:
        print(f"❌ Failed to update rule: {response.text}")

def delete_group_rule(rule_id):
    if not rule_id:
        print("⚠️ Skipping delete: Missing `rule_id`")
        return
    url = f"{OKTA_DOMAIN}/api/v1/groups/rules/{rule_id}"
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        save_summary("delete", "group-rule", rule_id, rule_id)
    else:
        print(f"❌ Failed to delete rule: {response.text}")

# 🔹 Process Okta Configuration
def process_okta_config(file_path, action, entity_type):
    config = load_json(file_path)

    if action == "create":
        if entity_type == "group":
            for group in config.get("create", {}).get("groups", []):
                name = group.get("name") or group.get("group_name")
                description = group.get("description") or group.get("group_description")

                if not name or not description:
                    print(f"⚠️ Skipping invalid group entry: {group}")
                    continue

                create_group(name, description)

        elif entity_type == "group-rule":
            for rule in config.get("create", {}).get("group_rules", []):
                create_group_rule(rule["name"], rule["attribute"], rule["value"], rule["groupIds"])

    elif action == "update":
        if entity_type == "group":
            for group in config.get("update", {}).get("groups", []):
                update_group(group.get("group_id"), group.get("name"), group.get("description"))

        elif entity_type == "group-rule":
            for rule in config.get("update", {}).get("group_rules", []):
                update_group_rule(rule.get("rule_id"), rule.get("name"), rule.get("attribute"), rule.get("value"), rule.get("groupIds"))

    elif action == "delete":
        if entity_type == "group":
            for group in config.get("delete", {}).get("groups", []):
                delete_group(group.get("group_id"))

        elif entity_type == "group-rule":
            for rule in config.get("delete", {}).get("group_rules", []):
                delete_group_rule(rule.get("rule_id"))

# 🔹 Run Script
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["create", "update", "delete"], required=True)
    parser.add_argument("--type", choices=["group", "group-rule"], required=True)
    parser.add_argument("--input-file", default="okta_config.json")
    args = parser.parse_args()
    process_okta_config(args.input_file, args.action, args.type)
