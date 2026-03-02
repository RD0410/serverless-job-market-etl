import json
import boto3
import os
import requests
from datetime import datetime

s3 = boto3.client('s3')

def lambda_handler(event, context):
    app_id = os.environ['ADZUNA_APP_ID']
    app_key = os.environ['ADZUNA_APP_KEY']
    bucket_name = os.environ['BUCKET_NAME']

    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": 10,
        "what": "data engineer",
        "content-type": "application/json",
        "sort_by": "date"  
    }
    
    try:
        response = requests.get(url, params=params)

        response.raise_for_status() 
        
        data = response.json()
        job_count = len(data.get('results', []))
        
        # Guard clause: Don't write empty files to S3 if no jobs are found
        if job_count == 0:
            print("No jobs found today.")
            return {'statusCode': 200, 'body': "0 jobs fetched."}
        
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        file_name = f"raw_jobs_{timestamp}.json"
        
        s3.put_object(
            Bucket=bucket_name,
            Key=f"inbox/{file_name}",
            Body=json.dumps(data)
        )
        
        return {
            'statusCode': 200,
            'body': f"Success! Fetched {job_count} fresh jobs from Adzuna."
        }
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return {'statusCode': 500, 'body': f"API HTTP Error: {http_err}"}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'body': "API Fetch Failed"}