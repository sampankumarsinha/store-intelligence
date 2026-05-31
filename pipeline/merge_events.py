import glob

output_file = "data/all_detected_events.jsonl"

event_files = glob.glob("data/CAM *_events.jsonl")

with open(output_file, "w") as outfile:
    for file in event_files:
        with open(file, "r") as infile:
            for line in infile:
                if line.strip():
                    outfile.write(line)

print(f"Merged {len(event_files)} files into {output_file}")