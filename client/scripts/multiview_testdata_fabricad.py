#standard imports
import json

#third party imports
from pathlib import Path
import pandas as pd

#custom imports
from client.client import CADConverterClient

# setup
OUTPUT_DIR = Path(r"mv_times_testdata")
MODE = "shaded" # render mode "shaded"  #"shaded_with_edges"
TOTAL_TO_PROCESS = 128  # max number of samples to process
path_to_fabricad = Path(r"/fabricad-10k")

#initialize client
try:
    client = CADConverterClient()
except Exception as e:
    print(f"ERROR: Failed to initialize client: {e}")

#load Fabricad samples


#load all samples
samples = list(path_to_fabricad.iterdir())

print(f"Loaded {len(samples)} Fabricad samples for multiview testing.")

# Dictionary to store timing results
timing_results = {}

cnt = 0 # successfully processed counter
for sample in samples:
    print(f"Processing sample: {sample.name}")

    #load plan
    try:
        plan = pd.read_csv(sample / "plan.csv", sep=";")
    except Exception as e:
        print(f"Failed to load plan for sample {sample.name}: {e}")
        continue

    #skip if drehen in steps
    if "drehen" in plan['Schritt'].values:
        print(f"Skipping sample {sample.name} due to 'drehen in steps' operation.")
        continue 

    #get path step file
    path_step_file = sample / f"geometry_{sample.name}.STEP"
    output_subdir = OUTPUT_DIR / sample.name / MODE

    # generate multiview images
    result = client.to_multiview(path_step_file, output_subdir, render_mode=MODE, total_imgs=16)

    if not result['success']:
        continue

    #sum up time
    total_time = plan['Dauer[min]'].sum()
    print(f"Total manufacturing time for {sample.name}: {total_time} minutes.")

    # Store timing result
    timing_results[sample.name] = {
        "total_time_minutes": float(total_time),
        "steps": len(plan)
    }

    cnt +=1

    if cnt == TOTAL_TO_PROCESS:
        break

# Write results to JSON file
output_file = OUTPUT_DIR / "multiview_timing_results.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(timing_results, f, indent=2, ensure_ascii=False)

print(f"\nTiming results written to {output_file}")
print(f"Successfully processed samples: {len(timing_results)}")
