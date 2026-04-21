# Flask Database Application

A Flask web application that connects to PostgreSQL RDS with secure credential management via AWS Secrets Manager.

## Features

- **Secure Credential Management**: Retrieves database credentials from AWS Secrets Manager
- **PostgreSQL Integration**: Connects to RDS PostgreSQL database
- **Health Check Endpoint**: ALB-compatible health check at `/health`
- **Database Test Endpoint**: Test database connectivity at `/db-test`
- **Production Ready**: Configured for deployment on EC2 with gunicorn

## Prerequisites

- Python 3.8+
- AWS credentials configured (for Secrets Manager access)
- PostgreSQL database with credentials stored in AWS Secrets Manager

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd blog
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Before running the app, ensure your AWS Secrets Manager contains credentials at the path `training/db/credentials` with the following JSON structure:

```json
{
  "host": "your-rds-endpoint.amazonaws.com",
  "dbname": "your_database_name",
  "username": "db_user",
  "password": "secure_password",
  "port": 5432
}
```

## Usage

### Development

```bash
python app.py
```

The app will run on `http://0.0.0.0:5000`

### Production

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Endpoints

- **GET `/`** - Welcome page with links to health check and database test
- **GET `/health`** - Health check endpoint (returns 200 if DB connected, 503 if unhealthy)
- **GET `/db-test`** - Test database connection and retrieve PostgreSQL version

## Dependencies

- Flask 3.0.0 - Web framework
- psycopg2-binary 2.9.9 - PostgreSQL adapter
- gunicorn 21.2.0 - Production WSGI server
- boto3 1.34.0 - AWS SDK
