from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import boto3
import os
import json
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from datetime import timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  
app.permanent_session_lifetime = timedelta(minutes=30)
app.config['USERS_JSON_PATH'] = os.path.join(os.path.dirname(__file__), 'config', 'users.json')


# AWS Credentials
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_REGION = ""

# Initialize Boto3 clients
iam_client = boto3.client(
    'iam',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def load_users():
    file_path = app.config['USERS_JSON_PATH']
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return []

def save_users(users):
    file_path = app.config['USERS_JSON_PATH']  # Use the file path from app config
    with open(file_path, 'w') as file:
        json.dump(users, file, indent=4)


def create_iam_user(username):
    try:
        # Tạo IAM User
        user = iam_client.create_user(UserName=username)
        # Tạo Access Key
        access_key_pair = iam_client.create_access_key(UserName=username)

        # Gán chính sách IAM cho User
        policy_arn = 'arn:aws:iam::aws:policy/AmazonS3FullAccess'
        iam_client.attach_user_policy(UserName=username, PolicyArn=policy_arn)

        return {
            "user_name": username,
            "access_key_id": access_key_pair['AccessKey']['AccessKeyId'],
            "secret_access_key": access_key_pair['AccessKey']['SecretAccessKey']
        }
    except Exception as e:
        return str(e)

def create_s3_bucket(bucket_name):
    try:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': AWS_REGION
            }
        )
        return {"bucket_name": bucket_name}
    except Exception as e:
        return str(e)
    
def save_user_to_file(user_data):
    file_path = app.config['USERS_JSON_PATH']
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                users = json.load(file)
        else:
            users = []

        users.append(user_data)

        with open(file_path, 'w') as file:
            json.dump(users, file, indent=4)
    except Exception as e:
        return str(e)

@app.route('/create-iam-user', methods=['POST'])
def create_iam_user_route():
    username = request.form.get('username')
    password = request.form.get('password')
    bucketname = request.form.get('bucketname')

    if not username or not bucketname:
        return jsonify({"error": "Username and Bucket Name are required"}), 400

    user_result = create_iam_user(username)
    if isinstance(user_result, str):
        return jsonify({"error": "Failed to create IAM user", "details": user_result}), 500

    bucket_result = create_s3_bucket(bucketname)
    if isinstance(bucket_result, str):
        return jsonify({"error": "Failed to create S3 bucket", "details": bucket_result}), 500

    user_data = {
        "user_name": user_result["user_name"],
        "password": password,
        "access_key_id": user_result["access_key_id"],
        "secret_access_key": user_result["secret_access_key"],
        "bucket_name": bucket_result["bucket_name"]
    }

    save_result = save_user_to_file(user_data)
    if isinstance(save_result, str):
        return jsonify({"error": "Failed to save user data", "details": save_result}), 500

    return jsonify({
        "message": "IAM User and S3 Bucket created successfully",
        "user_name": user_result["user_name"],
        "access_key_id": user_result["access_key_id"],
        "secret_access_key": user_result["secret_access_key"],
        "bucket_name": bucket_result["bucket_name"]
    }), 200

@app.route('/')
def index():
    return render_template('login1.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    users = load_users()

    for user in users:
        if user['user_name'] == username and user['password'] == password:
            session['username'] = username
            session['bucket_name'] = user['bucket_name']
            session.permanent = True  # Duy trì phiên lâu hơn
            return redirect(url_for('home'))

    flash("Thông tin đăng nhập không chính xác!")
    return redirect(url_for('index'))

@app.route('/home')
@app.route('/home/<path:folder>')
def home(folder=""):
    if 'username' not in session:
        # Nếu người dùng chưa đăng nhập, chuyển hướng về trang đăng nhập
        return redirect(url_for('index'))

    # Phần còn lại của mã để hiển thị tệp và thư mục
    username = session['username']
    bucket_name = session['bucket_name']
    
    if not bucket_name:
        return "No bucket found for user."

    try:
        if folder and not folder.endswith('/'):
            folder += '/'
        
        objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder).get('Contents', [])
        
        folders = set()
        files = []
        sizes = {}
        last_modified = {}
        icons = {}

        for obj in objects:
            key = obj['Key']
            relative_key = key[len(folder):] if folder else key

            if '/' in relative_key:
                folder_name = relative_key.split('/')[0]
                if folder_name and folder_name not in folders and relative_key.count('/') == 1:
                    folders.add(folder_name)
            else:
                if obj['Size'] > 0:
                    files.append(relative_key)
                    sizes[relative_key] = format_size(obj['Size'])
                    last_modified[relative_key] = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                    icons[relative_key] = get_icon_for_file(relative_key)

        return render_template('index1.html', files=files, sizes=sizes, last_modified=last_modified, icons=icons, folders=folders, current_folder=folder)
    except s3_client.exceptions.NoSuchBucket:
        return "Bucket does not exist"
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/upload', methods=['POST'])
def upload():
    bucket_name = session['bucket_name']
    file = request.files['file']
    file_name = secure_filename(file.filename)
    current_folder = request.form.get('current_folder', '').strip()

    print(current_folder)
    
    if current_folder.startswith('/home'):
        current_folder = current_folder[len('/home'):]
    if current_folder and not current_folder.endswith('/'):
        current_folder += '/'
    
    full_path = os.path.join(current_folder, file_name).replace('\\', '/').strip('/')

    try:
        s3_client.put_object(Bucket=bucket_name, Key=full_path, Body=file)
        
        file_info = s3_client.head_object(Bucket=bucket_name, Key=full_path)
        last_modified = file_info['LastModified']
        file_size_bytes = file_info['ContentLength']
        
        file_size = file_size_bytes / (1024 * 1024 * 1024) 
        if file_size >= 1:
            file_size_str = f"{file_size:.2f} GB"
        else:
            file_size = file_size_bytes / (1024 * 1024) 
            if file_size >= 1:
                file_size_str = f"{file_size:.2f} MB"
            else:
                file_size = file_size_bytes / 1024  
                file_size_str = f"{file_size:.2f} KB"

        return jsonify({
            'status': 'success',
            'message': f'File {file_name} uploaded successfully!',
            'last_modified': last_modified.strftime('%Y-%m-%d %H:%M:%S'),
            'file_size': file_size_str
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/create_folder', methods=['POST'])
def create_folder():
    bucket_name = session['bucket_name']
    folder_name = request.form.get('folder_name', '').strip()
    current_folder = request.form.get('current_folder', '').strip()
    
    if folder_name:
        if current_folder and not current_folder.endswith('/'):
            current_folder += '/'
        full_path = os.path.join(current_folder, folder_name).rstrip('/') + '/'
        
        try:
            s3_client.put_object(Bucket=bucket_name, Key=full_path)
            
            # Tạo URL cho thư mục mới
            folder_url = url_for('home', folder=full_path, _external=True)
            
            return jsonify({
                'status': 'success',
                'folder_name': folder_name,
                'folder_url': folder_url
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Folder name cannot be empty'}), 400

@app.route('/delete_file', methods=['POST'])
def delete_file():
    bucket_name = session['bucket_name']
    file_name = request.form.get('file')
    current_folder = request.form.get('current_folder', '').strip()

    # Xử lý current_folder để tạo đường dẫn đầy đủ
    if current_folder.startswith('/home'):
        current_folder = current_folder[len('/home'):]
    if current_folder and not current_folder.endswith('/'):
        current_folder += '/'

    # Xây dựng đường dẫn file đầy đủ
    full_path = os.path.join(current_folder, file_name).replace('\\', '/').strip('/')

    try:
        # Kiểm tra xem file có tồn tại không trước khi xóa
        s3_client.head_object(Bucket=bucket_name, Key=full_path)
        
        # Xóa file từ S3
        s3_client.delete_object(Bucket=bucket_name, Key=full_path)
        
        return jsonify({
            'status': 'success',
            'message': f'File {file_name} đã được xóa thành công!'
        })
    except s3_client.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            return jsonify({'status': 'error', 'message': 'File không tồn tại!'}), 404
        else:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete_folder', methods=['POST'])
def delete_folder():
    bucket_name = session['bucket_name']
    folder_name = request.form.get('folder')
    current_folder = request.form.get('current_folder', '').strip()

    # Xử lý current_folder để tạo đường dẫn đầy đủ
    if current_folder.startswith('/home'):
        current_folder = current_folder[len('/home'):]
    if current_folder and not current_folder.endswith('/'):
        current_folder += '/'

    # Xây dựng đường dẫn thư mục đầy đủ
    folder_path = os.path.join(current_folder, folder_name).replace('\\', '/').strip('/') + '/'

    try:
        # Liệt kê tất cả các tệp trong thư mục
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_path)
        if 'Contents' in response:
            for obj in response['Contents']:
                s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
        
        return jsonify({
            'status': 'success',
            'message': f'Thư mục {folder_name} đã được xóa thành công!'
        })
    except s3_client.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            return jsonify({'status': 'error', 'message': 'Thư mục không tồn tại!'}), 404
        else:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download/<path:filename>')
def download(filename):
    bucket_name = session['bucket_name']
    try:
        # Tạo pre-signed URL để tải xuống file
        file_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': filename},
            ExpiresIn=3600  # URL có hiệu lực trong 1 giờ
        )
        return redirect(file_url)
    except s3_client.exceptions.NoSuchKey:
        return "File does not exist"
    except Exception as e:
        return f'Error: {str(e)}'
    
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('bucket_name', None)
    flash("You have been logged out.", 'info')
    return redirect(url_for('index'))
    
def get_icon_for_file(file_name):
    ext = file_name.split('.')[-1].lower()
    icons = {
        'ppt': 'fa-solid fa-file-powerpoint',
        'pptx': 'fa-solid fa-file-powerpoint',
        'xlsx': 'fa-solid fa-file-excel',
        'xls': 'fa-solid fa-file-excel',
        'docx': 'fa-solid fa-file-word',
        'doc': 'fa-solid fa-file-word',
        'jpg': 'fa-solid fa-file-image',
        'jpeg': 'fa-solid fa-file-image',
        'png': 'fa-solid fa-file-image',
        'gif': 'fa-solid fa-file-image',
        'bmp': 'fa-solid fa-file-image',
    }
    return icons.get(ext, 'fas fa-file-alt')

def format_size(size_in_bytes):
    if size_in_bytes >= 1073741824:
        size = round(size_in_bytes / 1073741824, 2)
        return f"{size} GB"
    elif size_in_bytes >= 1048576:
        size = round(size_in_bytes / 1048576, 2)
        return f"{size} MB"
    else:
        size = round(size_in_bytes / 1024, 2)
        return f"{size} KB"

@app.route('/share_file', methods=['POST'])
def share_file():
    data = request.get_json()
    username = data.get('username')
    file_name = data.get('file')
    
    # Use app.config to get the path to users.json
    file_path = app.config['USERS_JSON_PATH']
    
    # Load the users from the configured users.json file
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            users = json.load(f)
    else:
        return jsonify({'status': 'error', 'message': 'File users.json không tồn tại!'}), 500

    # Find the user by username
    user = next((u for u in users if u['user_name'] == username), None)
    
    if user:
        bucket_name = user['bucket_name']
        access_key_id = user['access_key_id']
        secret_access_key = user['secret_access_key']
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )

        # Move file from current user's bucket to the recipient's bucket
        current_bucket = session['bucket_name']
        current_folder = ''  # Optionally, this could come from session or form data
        full_path = os.path.join(current_folder, file_name).replace('\\', '/').strip('/')
        
        try:
            # Download file from the current bucket
            file_content = s3_client.get_object(Bucket=current_bucket, Key=full_path)['Body'].read()
            
            # Upload file to the recipient's bucket
            s3_client.put_object(Bucket=bucket_name, Key=full_path, Body=file_content)
            
            return jsonify({'status': 'success', 'message': 'File đã được chia sẻ thành công!'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Người dùng không tồn tại!'}), 400



if __name__ == "__main__":
    app.run(debug=True)
