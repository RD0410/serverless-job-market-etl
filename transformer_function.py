import json
import boto3
import urllib.parse
import re

s3 = boto3.client('s3')

# 1. Our NLP Dictionary: Add or remove skills as needed
SKILLS_DB = [
    "python", "sql", "aws", "azure", "gcp", "spark", "hadoop", 
    "snowflake", "databricks", "kafka", "airflow", "terraform", 
    "docker", "kubernetes", "scala", "java", "nosql", "redshift",
    "machine learning", "nlp", "tableau", "power bi", "dbt"
]

def clean_html(raw_html):
    """Removes HTML tags from the raw Adzuna description."""
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def extract_skills(description):
    """Scans the text for specific tech skills using word boundaries."""
    if not description: return []
    
    # Convert text to lowercase for uniform matching
    text = description.lower()
    found_skills = []
    
    for skill in SKILLS_DB:
        # \b ensures we only match whole words. 
        # re.escape ensures multi-word skills like "power bi" are treated literally.
        pattern = r'\b' + re.escape(skill) + r'\b'
        
        if re.search(pattern, text):
            found_skills.append(skill)
            
    return found_skills

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        raw_data = json.loads(response['Body'].read().decode('utf-8'))
        
        processed_jobs = []
        
        for job in raw_data.get('results', []):
            raw_desc = job.get('description', '')
            cleaned_desc = clean_html(raw_desc)
            
            # 2. Fire the NLP extraction
            extracted_skills = extract_skills(cleaned_desc)
            
            processed_jobs.append({
                "title": job.get('title'),
                "company": job.get('company', {}).get('display_name'),
                "location": job.get('location', {}).get('display_name'),
                "description": cleaned_desc,
                "extracted_skills": extracted_skills,  # 3. Add to the final payload
                "url": job.get('redirect_url'),
                "created": job.get('created')
            })
        
        json_lines = "\n".join([json.dumps(job) for job in processed_jobs])
        
        new_key = key.replace('inbox/', 'processed/').replace('raw_', 'clean_')
        s3.put_object(
            Bucket=bucket,
            Key=new_key,
            Body=json_lines, 
            ContentType='application/json'
        )
        
        return {"statusCode": 200, "body": f"Successfully processed {key} and extracted skills"}
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise e