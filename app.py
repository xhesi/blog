from flask import Flask, jsonify, request
import psycopg2
import boto3
import json
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)

# S3 Configuration
S3_BUCKET = 'training-flask-app-files-xh-2026'
S3_REGION = 'eu-north-1'

# Initialize S3 client
s3_client = boto3.client('s3', region_name=S3_REGION)

def get_secret():
    """Fetch database credentials from AWS Secrets Manager"""
    secret_name = "training/db/credentials"
    region_name = "eu-north-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    # Parse the secret string
    secret = json.loads(get_secret_value_response['SecretString'])
    return secret

def get_db_connection():
    """Create database connection using credentials from Secrets Manager"""
    secret = get_secret()

    conn = psycopg2.connect(
        host=secret['host'],
        database=secret['dbname'],
        user=secret['username'],
        password=secret['password'],
        port=secret.get('port', 5432),
        sslmode='require'
    )
    return conn

@app.route('/')
def index():
  return '''
  <h1>Hello from Python Flask on EC2!</h1>
  <p>Connected to RDS PostgreSQL via Secrets Manager 🔒</p>
  <p>Integrated with S3 for file storage 📦</p>
  <hr>
  <h2>Endpoints:</h2>
  <ul>
      <li><a href="/health">Health Check</a></li>
      <li><a href="/db-test">Test Database Connection</a></li>
      <li><a href="/upload">Upload File to S3</a></li>
      <li><a href="/list-files">List S3 Files</a></li>
  </ul>
  '''

@app.route('/health')
def health():
    """Health check endpoint for ALB"""
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@app.route('/db-test')
def db_test():
    """Test database connection and query"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT version();')
        db_version = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({
            "status": "success",
            "database_version": db_version[0],
            "security": "Credentials from AWS Secrets Manager"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
  """Upload file to S3"""
  if request.method == 'POST':
      # Check if file was uploaded
      if 'file' not in request.files:
          return jsonify({"error": "No file provided"}), 400

      file = request.files['file']

      if file.filename == '':
          return jsonify({"error": "No file selected"}), 400

      if file:
          # Secure the filename
          filename = secure_filename(file.filename)
          # Add timestamp to make it unique
          timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
          s3_key = f"uploads/{timestamp}-{filename}"

          try:
              # Upload to S3
              s3_client.upload_fileobj(
                  file,
                  S3_BUCKET,
                  s3_key,
                  ExtraArgs={'ContentType': file.content_type}
              )

              return jsonify({
                  "status": "success",
                  "message": "File uploaded successfully",
                  "filename": filename,
                  "s3_key": s3_key
              }), 200
          except Exception as e:
              return jsonify({"status": "error", "message": str(e)}), 500

  # GET request - show upload form
  return '''
  <!DOCTYPE html>
  <html>
  <head><title>S3 File Upload</title></head>
  <body>
      <h1>Upload File to S3</h1>
      <form method="post" enctype="multipart/form-data">
          <input type="file" name="file" required>
          <button type="submit">Upload</button>
      </form>
      <br>
      <a href="/">Back to Home</a> | <a href="/list-files">View Uploaded Files</a>
  </body>
  </html>
  '''

@app.route('/list-files')
def list_files():
  """List all files in S3 bucket"""
  try:
      response = s3_client.list_objects_v2(
          Bucket=S3_BUCKET,
          Prefix='uploads/'
      )

      files = []
      if 'Contents' in response:
          for obj in response['Contents']:
              files.append({
                  'key': obj['Key'],
                  'size': obj['Size'],
                  'last_modified': obj['LastModified'].isoformat()
              })

      return jsonify({
          "status": "success",
          "bucket": S3_BUCKET,
          "file_count": len(files),
          "files": files
      })
  except Exception as e:
      return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<path:key>')
def download_file(key):
  """Download file from S3"""
  try:
      # Generate presigned URL (valid for 1 hour)
      url = s3_client.generate_presigned_url(
          'get_object',
          Params={'Bucket': S3_BUCKET, 'Key': key},
          ExpiresIn=3600
      )

      return jsonify({
          "status": "success",
          "download_url": url,
          "expires_in": "1 hour"
      })
  except Exception as e:
      return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
