# Docker Deployment for Kurin Telegram Bot

This directory contains Docker configuration for the Kurin Telegram Bot with automated deployment via GitHub Actions.

## Files Overview

- `Dockerfile` - Main Docker image configuration
- `docker-compose.yml` - Local development and testing setup
- `.dockerignore` - Files to exclude from Docker build context
- `env.example` - Example environment variables configuration

## Prerequisites

1. **Docker** installed on your system
2. **Google Service Account** credentials (as JSON file or environment variable)
3. **Telegram Bot Token** from BotFather
4. **Environment Variables** configured

## Local Development

### 1. Setup Environment Variables

Copy the example environment file and configure it:

```bash
cp env.example .env
```

Edit `.env` with your actual values:
- `BOT_TOKEN` - Your Telegram bot token
- `ADMIN_IDS` - Comma-separated list of admin user IDs
- `GOOGLE_SHEETS_URL` - Your Google Sheets URL
- Other configuration as needed

### 2. Setup Google Credentials

You have two options for providing Google Service Account credentials:

#### Option A: Environment Variable (Recommended)
Add your Google Service Account JSON content to the `.env` file:
```bash
GOOGLE_CREDENTIALS_JSON='{"type":"service_account","project_id":"your-project-id",...}'
```

#### Option B: Mount Credentials File
Place your Google Service Account credentials file and uncomment the volume mount in `docker-compose.yml`:
```bash
mkdir -p credentials
# Copy your credentials.json file to credentials/credentials.json
```

### 3. Run with Docker Compose

```bash
# Build and run the bot
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop the bot
docker-compose down
```

## Production Deployment with GitHub Actions

### 1. Setup GitHub Secrets

Go to your repository Settings → Secrets and variables → Actions, and add:

**Required Secrets:**
- `BOT_TOKEN` - Your Telegram bot token
- `ADMIN_IDS` - Comma-separated admin user IDs
- `GOOGLE_SHEETS_URL` - Your Google Sheets URL
- `GOOGLE_CREDENTIALS_JSON` - Your Google Service Account JSON content (entire JSON as string)

**Optional Secrets:**
- `GOOGLE_SHEET_NAME` - Sheet name (default: "Books")
- `ALLOWED_TIME_TO_READ_THE_BOOK` - Days allowed (default: 14)
- `RULES_TEXT` - Bot rules text

**For Server Deployment (if using SSH):**
- `HOST` - Your server IP/hostname
- `USERNAME` - SSH username
- `SSH_KEY` - Your private SSH key

#### Adding Google Credentials JSON Secret

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `GOOGLE_CREDENTIALS_JSON`
5. Value: Copy and paste the entire content of your `credentials.json` file
6. Click "Add secret"

### 2. Deploy

The GitHub Action will automatically:
1. **Build** the Docker image when you push to main/master branch
2. **Push** to GitHub Container Registry (ghcr.io)
3. **Deploy** to your server (if configured)

#### Manual Trigger
You can also trigger deployment manually:
1. Go to Actions tab in your GitHub repository
2. Select "Deploy Telegram Bot" workflow
3. Click "Run workflow"

### 3. Server Setup (Optional)

If you want to deploy to a server, uncomment the SSH deployment section in `.github/workflows/deploy-telegram-bot.yml` and:

1. Ensure Docker is installed on your server
2. Add the required SSH secrets to GitHub
3. Update the server configuration in the workflow file

## Manual Docker Commands

### Build Image
```bash
cd telegram-bot
docker build -t kurin-telegram-bot .
```

### Run Container

#### With Environment Variable Credentials (Recommended)
```bash
docker run -d \
  --name kurin-telegram-bot \
  --restart unless-stopped \
  --env-file .env \
  kurin-telegram-bot
```

#### With Mounted Credentials File
```bash
docker run -d \
  --name kurin-telegram-bot \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/credentials/credentials.json:/app/credentials/credentials.json:ro \
  kurin-telegram-bot
```

### View Logs
```bash
docker logs -f kurin-telegram-bot
```

### Stop Container
```bash
docker stop kurin-telegram-bot
docker rm kurin-telegram-bot
```

## Troubleshooting

1. **Credentials Issues**: 
   - Ensure `GOOGLE_CREDENTIALS_JSON` environment variable is set with valid JSON content
   - Or ensure `credentials.json` file is properly mounted and accessible
2. **Environment Variables**: Check that all required environment variables are set
3. **Google Sheets Access**: Verify the service account has access to your Google Sheet
4. **Bot Token**: Ensure the Telegram bot token is valid and active
5. **JSON Format**: When using `GOOGLE_CREDENTIALS_JSON`, ensure the JSON is properly formatted and escaped

## Health Checks

The Docker container includes health checks that verify the Python environment. You can check the health status:

```bash
docker inspect --format='{{.State.Health.Status}}' kurin-telegram-bot
```

## Security Notes

- **Never commit credentials or API tokens to git**
- **Use GitHub Secrets for all sensitive data**
- **The Docker container runs as a non-root user for security**
- **Google credentials are created at runtime from environment variables**
- **Credentials file is created with restricted permissions inside the container** 