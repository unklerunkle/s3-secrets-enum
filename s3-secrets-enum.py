import boto3
import json
import os
from datetime import datetime
import argparse
from tqdm import tqdm

# Parse arguments BEFORE using them
parser = argparse.ArgumentParser()
parser.add_argument("--profile", required=True, help="AWS CLI profile name")
parser.add_argument("--bucket", required=True, help="S3 Bucket (e.g. hl-data-download)")
args = parser.parse_args()

# Now they're available
profile = args.profile
bucket = args.bucket

# AWS session setup
session = boto3.Session(profile_name=profile)
s3_client = session.client("s3")
sts_client = session.client("sts")
secrets_client = session.client("secretsmanager")
iam_client = session.client("iam")

def custom_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()

print("Here is STS Info on the Profile!\n")

sts_caller_info = sts_client.get_caller_identity()
if sts_caller_info:
    print(f"UserId: {sts_caller_info['UserId']}")
    print(f"Account: {sts_caller_info['Account']}")
    print(f"ARN: {sts_caller_info['Arn']}")

print("-" * 80)
print("S3 Bucket Download\n")

bucket_objects = s3_client.list_objects_v2(Bucket=bucket)
if "Contents" not in bucket_objects:
    print(f"\033[93m[~]\033[0m No files found in bucket: {bucket}")
else:
    contents = bucket_objects["Contents"]
    total_files = len(contents)
    print(f"\033[96m[i]\033[0m Found \033[1m{total_files}\033[0m file(s) in bucket: '{bucket}'\n")
    
    for bucket_contents in tqdm(contents, desc=f"Downloading from {bucket}", unit="file"):
        file_name = bucket_contents["Key"]
        file_path = os.path.join(bucket, file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as file:
            s3_client.download_fileobj(bucket, file_name, file)

    print(f"\033[92m[+]\033[0m Created directory '{bucket}' and downloaded all files inside!")

print("-" * 80)
print("Secrets Manager Enumeration\n")

secrets_list = secrets_client.list_secrets()
if secrets_list:
    if "SecretList" in secrets_list:
        for secret in secrets_list["SecretList"]:
            print(f"\033[94m[i]\033[0m Name: {secret['Name']}")
            print(f"\033[94m[i]\033[0m ARN: {secret['ARN']}")
            print(f"\033[94m[i]\033[0m Description: {secret['Description']}")
            print("-" * 40)

    for secret in secrets_list.get("SecretList", []):
        name = secret["Name"]
        try:
            secret_dump = secrets_client.get_secret_value(SecretId=name)
            secret_string = secret_dump.get("SecretString")
            if secret_string:
                print(f"\033[92m[+]\033[0m Secret found for: \033[1m{name}\033[0m")
                print(f"SecretString: {secret_string}")
            else:
                print(f"\033[93m[~]\033[0m No SecretString found for: {name}")
        except Exception as e:
            print(f"\033[91m[!]\033[0m Could not retrieve secret '{name}': {e}")
        print("-" * 40)
