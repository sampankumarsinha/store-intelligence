import json
import requests

events = []

with open("data/enriched_events.jsonl", "r") as f:
    for line in f:
        events.append(json.loads(line))

response = requests.post(
    "http://127.0.0.1:8000/events/ingest",
    json=events
)

print(response.status_code)
print(response.json())
