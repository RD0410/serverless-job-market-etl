# Serverless Job Market ETL Pipeline (AWS & Terraform)

## 📌 Overview
An automated, serverless ETL (Extract, Transform, Load) pipeline built on AWS to extract, clean, and store job market data. Currently configured to track Data Science, Machine Learning, and Data Engineering roles across the US. The infrastructure is entirely codified and provisioned using Terraform.

## 🏗 Architecture
This project utilizes an event-driven serverless architecture:
1. **Extraction (EventBridge & Lambda):** An Amazon EventBridge scheduler triggers a Python Lambda function (`job_fetcher`) daily. This function hits the Adzuna API to pull raw job postings and lands the JSON data into an S3 "Inbox" bucket.
2. **Transformation (S3 Event & Lambda):** An S3 event notification acts as a tripwire. When new raw data lands in S3, it instantly triggers a second Lambda function (`job_transformer`). 
3. **Load (S3 & JSONL):** The transformer cleans HTML tags, extracts critical fields (title, company, location, description, URL), and writes the data back to an S3 "Processed" prefix in JSON Lines format, optimizing it for downstream querying (e.g., AWS Athena) and ML tasks.

## 🛠 Tech Stack
* **Cloud:** AWS (S3, Lambda, EventBridge, IAM)
* **Infrastructure as Code (IaC):** Terraform
* **Language:** Python 3.9 (Requests, Boto3, JSON, Regex)
* **Data Format:** JSON Lines (JSONL)

## 🚀 Future Roadmap
* **Natural Language Processing (NLP):** Implement an NLP module to parse job descriptions and extract the most frequently demanded skills and technologies.
* **CI/CD Integration:** Set up GitHub Actions to automatically deploy Terraform changes and update Lambda zip packages upon code push.
* **Data Visualization:** Connect AWS Athena and a BI tool (like QuickSight or Power BI) to visualize market trends over time.