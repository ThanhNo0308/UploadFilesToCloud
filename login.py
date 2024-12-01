from flask import Flask, render_template, request, jsonify
import boto3
import json
import os

app = Flask(__name__)

# AWS setup
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_REGION = ""

iam_client = boto3.client('iam', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)
s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

# Load users from JSON file
def load_users(file_path="users.json"):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return []

# Save user to JSON file
def save_user_to_file(user_data, file_path="users.json"):
    try:
        users = load_users(file_path)
        users.append(user_data)
        with open(file_path, 'w') as file:
            json.dump(users, file, indent=4)
    except Exception as e:
        return str(e)

# Create IAM user and S3 bucket
def create_iam_user_and_bucket(username, password, bucketname):
    try:
        iam_client.create_user(UserName=username)
        s3_client.create_bucket(Bucket=bucketname, CreateBucketConfiguration={'LocationConstraint': AWS_REGION})

        user_data = {
            "username": username,
            "password": password,
            "bucket_name": bucketname
        }
        save_user_to_file(user_data)
        return user_data
    except Exception as e:
        return str(e)

# Login user and check access
def login_user(username, password):
    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            return user  # Return the user if credentials are correct
    return None

# Flask routes
@app.route('/')
def index():
    return render_template('create_user.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    bucketname = request.form.get('bucketname')

    if not username or not bucketname or not password:
        return jsonify({"error": "All fields are required"}), 400

    result = create_iam_user_and_bucket(username, password, bucketname)
    if isinstance(result, str):
        return jsonify({"error": "Error creating user or bucket", "details": result}), 500

    return jsonify({"message": "User and bucket created successfully", "user": result}), 200

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = login_user(username, password)
    if user:
        bucket_name = user['bucket_name']
        # Logic to list files from the user's bucket
        objects = s3_client.list_objects_v2(Bucket=bucket_name)
        files = [obj['Key'] for obj in objects.get('Contents', [])]

        return jsonify({"message": "Login successful", "bucket_name": bucket_name, "files": files}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

if __name__ == '__main__':
    app.run(debug=True)
