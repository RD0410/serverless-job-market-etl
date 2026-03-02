import json
import boto3
import urllib.parse
import re
import html  

s3 = boto3.client('s3')

def clean_text(raw_text):
    if not raw_text: return ""
    # 1. Strip HTML tags
    cleanr = re.compile('<.*?>')
    text_no_tags = re.sub(cleanr, '', raw_text)
    # 2. Decode HTML entities (e.g., &amp; -> &)
    clean_text = html.unescape(text_no_tags)
    # 3. Clean up extra whitespace/newlines that might break visualization later
    return " ".join(clean_text.split())

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        raw_data = json.loads(response['Body'].read().decode('utf-8'))
        
        processed_jobs = []
        for job in raw_data.get('results', []):
            processed_jobs.append({
                "title": job.get('title'),
                "company": job.get('company', {}).get('display_name'),
                "location": job.get('location', {}).get('display_name'),
                "description": clean_text(job.get('description')), 
                "url": job.get('redirect_url'),
                "created": job.get('created')
            })
            
        # Guard clause to prevent writing empty files to Athena
        if not processed_jobs:
            return {"statusCode": 200, "body": "No jobs to process. Skipped writing."}
        
        json_lines = "\n".join([json.dumps(job) for job in processed_jobs])
        
        new_key = key.replace('inbox/', 'processed/').replace('raw_', 'clean_')
        s3.put_object(
            Bucket=bucket,
            Key=new_key,
            Body=json_lines, 
            ContentType='application/json'
        )
        
        return {"statusCode": 200, "body": f"Successfully processed {len(processed_jobs)} jobs into {new_key}"}
        
    except Exception as e:
        print(f"Error processing {key}: {str(e)}")
        raise e