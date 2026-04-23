# Local Development Setup Guide

This guide will help you set up the AI Virtual Coach project for local development without Docker.

## Prerequisites

- Python 3.9+ 
- Node.js 16+
- PostgreSQL 13+ (installed locally)
- Git

## Database Setup

### 1. Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE ai_virtual_coach;

# Create user (optional, you can use postgres)
CREATE USER ai_coach_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ai_virtual_coach TO ai_coach_user;

# Exit
\q
```

### 2. Alternative: Use pgAdmin

If you prefer a GUI, use pgAdmin to create a database named `ai_virtual_coach`.

## Backend Setup

### 1. Create and Activate Python Virtual Environment

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# If requirements.txt doesn't exist, install from setup.py or individual packages
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic python-jose[cryptography] passlib[bcrypt] python-multipart python-dotenv litellm PyPDF2
```

### 3. Environment Configuration

```bash
# Copy the local environment template
cp ../.env.local ../.env

# Edit the .env file with your settings
# At minimum, update these values:
# - DATABASE_URL (your PostgreSQL connection)
# - GOOGLE_API_KEY (your Gemini API key)
# - JWT_SECRET_KEY (generate a strong secret)
# - ADMIN_EMAIL and ADMIN_PASSWORD
```

### 4. Run Database Migrations

```bash
# If you have Alembic setup
alembic upgrade head

# Alternative: Create tables directly (for development)
python -c "
from database import engine, Base
Base.metadata.create_all(bind=engine)
print('Database tables created successfully!')
"
```

### 5. Start the FastAPI Server

```bash
# Run the development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or with more verbose output
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

The backend will be available at: `http://localhost:8000`

## Frontend Setup

### 1. Navigate to Frontend Directory

```bash
# From project root
cd frontend

# Or from backend
cd ../frontend
```

### 2. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Or if you prefer yarn
yarn install
```

### 3. Environment Configuration

```bash
# Create frontend environment file
echo "VITE_API_URL=http://localhost:8000" > .env.local

# Or edit existing .env file
# Make sure VITE_API_URL points to your backend
```

### 4. Start the Development Server

```bash
# Start Vite development server
npm run dev

# Or with yarn
yarn dev
```

The frontend will be available at: `http://localhost:5173`

## Quick Start Commands

### Backend (Terminal 1)
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.local ../.env
# Edit .env with your settings
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Terminal 2)
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
```

## Verification

### 1. Check Backend Health

Visit `http://localhost:8000` - you should see:
```json
{"message": "Neural Core Synced with Engine v3.0"}
```

### 2. Check API Documentation

Visit `http://localhost:8000/docs` - you should see the FastAPI documentation.

### 3. Check Frontend

Visit `http://localhost:5173` - you should see the AI Virtual Coach interface.

### 4. Test Database Connection

```bash
# In backend terminal with activated venv
python -c "
from database import engine
try:
    with engine.connect() as conn:
        result = conn.execute('SELECT 1').fetchone()
        print('✅ Database connection successful!')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

## Common Issues & Solutions

### Database Connection Issues

**Problem**: `could not connect to server: Connection refused`
**Solution**: 
- Ensure PostgreSQL is running
- Check your DATABASE_URL format: `postgresql+psycopg2://user:password@localhost:5432/dbname`
- Verify database name and credentials

**Problem**: `FATAL: database "ai_virtual_coach" does not exist`
**Solution**: Create the database first using `createdb ai_virtual_coach` or pgAdmin

### Port Conflicts

**Problem**: `Address already in use`
**Solution**: 
- Kill the process using the port: `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`
- Or use a different port: `uvicorn main:app --port 8001`

### CORS Issues

**Problem**: CORS errors in browser console
**Solution**: 
- Ensure your .env has correct CORS_ORIGINS
- Check that VITE_API_URL in frontend matches backend URL

### Missing Dependencies

**Problem**: ModuleNotFoundError
**Solution**: 
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check Python version compatibility

## Development Tips

### 1. Enable SQL Debugging
Set `SQL_DEBUG=true` in your .env to see SQL queries.

### 2. Hot Reload
Both frontend and backend support hot reload. Changes will automatically refresh.

### 3. Database Resets
For fresh database during development:
```bash
# Drop and recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS ai_virtual_coach;"
psql -U postgres -c "CREATE DATABASE ai_virtual_coach;"
# Then run migrations again
```

### 4. Environment Variables
Keep your .env file out of version control. Use .env.local for local development only.

## Production Considerations

When moving to production:
- Use stronger passwords and secrets
- Set `SQL_DEBUG=false`
- Use environment-specific configuration
- Set up proper database migrations
- Configure reverse proxy (nginx/apache)
- Set up SSL certificates

## Need Help?

If you encounter issues:
1. Check the terminal logs for detailed error messages
2. Verify all environment variables are set correctly
3. Ensure PostgreSQL is running and accessible
4. Check that all dependencies are installed

Happy coding! 🚀
