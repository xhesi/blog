from flask import Flask, jsonify
import psycopg2
import boto3
import json
from botocore.exceptions import ClientError

app = Flask(__name__)

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
    <p><a href="/health">Health Check</a></p>
    <p><a href="/db-test">Test Database</a></p>
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
