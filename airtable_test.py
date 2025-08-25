import requests

api_key = "pat2NtBJgSVD9M7bO.c42c7944b0f2d187ec8ad8200c503ab31c4021fae05603bd860ca1fd8f6c33ff"
base_id = "appQpDYR8ZukjJnTX"

table_names = ["Job Seekers", "Job%20Seekers", "tblOndk2X10XpQLhF"]

for table_name in table_names:
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}?maxRecords=3"
    headers = {"Authorization": f"Bearer {api_key}"}
    print(f"\n--- Testing table name: {table_name} ---")
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        records = data.get("records", [])
        print(f"Found {len(records)} records")
        if records:
            print(f"Available fields: {list(records[0].get('fields', {}).keys())}")
            print(f"Sample record: {records[0].get('fields', {})}")
        break
    else:
        print(f"Error: {response.text}")
