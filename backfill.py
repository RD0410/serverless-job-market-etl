import requests
import json
import boto3
import time
from datetime import datetime
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
# --- CONFIGURATION ---
APP_ID = os.environ.get('ADZUNA_APP_ID')
APP_KEY = os.environ.get('ADZUNA_APP_KEY')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'ralph-job-market-lake-2026')
PAGES_TO_FETCH = 50  
print(f"Verified ID loaded: {str(APP_ID)[:4]}...")
s3 = boto3.client('s3')

print("Starting Data Lake Backfill...")

for page in range(21, 41):
    url = f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": 50, # Max allowed by Adzuna
        "what": "data engineer",
        "content-type": "application/json"
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        job_count = len(data.get('results', []))
        
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        file_name = f"raw_jobs_page_{page}_{timestamp}.json"
        
        # Upload directly to the S3 inbox to trigger your pipeline
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"inbox/{file_name}",
            Body=json.dumps(data)
        )
        print(f"Page {page}: Successfully sent {job_count} jobs to S3 inbox.")
    else:
        print(f"Page {page}: Failed! Status code {response.status_code}")
        
    # Sleep for 3 seconds to avoid the 25 requests/minute rate limit
    time.sleep(3) 

print("Backfill complete! Your AWS pipeline is processing the data right now.")