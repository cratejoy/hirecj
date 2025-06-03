# Heroku Setup for HireCJ Auth Service

## 1. Create GitHub Repository

First, create the repository on GitHub:
```bash
# Navigate to the auth directory
cd /Users/aelaguiz/workspace/hirecj/hirecj-auth

# Initialize git if not already done
git init

# Create initial commit
git add .
git commit -m "Initial commit: HireCJ Auth Service"

# Create repository on GitHub (using GitHub CLI)
gh repo create cratejoy/hirecj-auth --private --source=. --remote=origin --push
```

## 2. Create Heroku App

```bash
# Login to Heroku (if not already logged in)
heroku login

# Create the Heroku app on the cratejoy account
heroku create hirecj-auth --team cratejoy

# Set the stack to heroku-22 (supports Python 3.11)
heroku stack:set heroku-22 -a hirecj-auth

# Connect to GitHub repository
heroku git:remote -a hirecj-auth
```

## 3. Configure Heroku Environment

Set the required environment variables:
```bash
# Basic configuration
heroku config:set APP_HOST=0.0.0.0 -a hirecj-auth
heroku config:set APP_PORT=\$PORT -a hirecj-auth
heroku config:set DEBUG=False -a hirecj-auth
heroku config:set LOG_LEVEL=INFO -a hirecj-auth

# Security keys (generate secure values for production)
heroku config:set JWT_SECRET=$(openssl rand -hex 32) -a hirecj-auth
heroku config:set ENCRYPTION_KEY=$(openssl rand -hex 32) -a hirecj-auth

# OAuth redirect configuration (port 8103 for local dev)
heroku config:set OAUTH_REDIRECT_BASE_URL=https://auth.hirecj.ai -a hirecj-auth
heroku config:set FRONTEND_URL=https://hirecj.ai -a hirecj-auth

# Database (using Heroku Postgres)
heroku addons:create heroku-postgresql:mini -a hirecj-auth

# CORS configuration
heroku config:set ALLOWED_ORIGINS='["https://hirecj.ai","https://www.hirecj.ai","https://app.hirecj.ai"]' -a hirecj-auth
```

## 4. Set Up Custom Domain with SSL

```bash
# Add custom domain to Heroku
heroku domains:add auth.hirecj.ai -a hirecj-auth

# Get the DNS target
heroku domains -a hirecj-auth
```

## 5. Namecheap DNS Configuration

After running the above command, you'll get a DNS target like `shiny-example-1234.herokudns.com`. 

Add these records in Namecheap:

### For auth.hirecj.ai:

**Type:** CNAME
**Host:** auth
**Value:** [Your Heroku DNS target, e.g., shiny-example-1234.herokudns.com]
**TTL:** Automatic

### Complete DNS Setup for hirecj.ai domain:

If you haven't already set up the main domain, here's the complete configuration:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | @ | 76.76.21.21 | Automatic |
| CNAME | www | cname.vercel-dns.com | Automatic |
| CNAME | auth | [Your Heroku DNS target] | Automatic |
| CNAME | api | [Your API Heroku DNS target] | Automatic |

## 6. Enable SSL

Once DNS propagates (can take up to 48 hours, usually faster):
```bash
# Enable Automated Certificate Management (ACM)
heroku certs:auto:enable -a hirecj-auth
```

## 7. Deploy

```bash
# Deploy via Git
git push heroku main

# Or if using GitHub integration
# Go to Heroku Dashboard > Deploy > Connect to GitHub
# Select cratejoy/hirecj-auth repository
# Enable automatic deploys from main branch
```

## 8. Verify Deployment

```bash
# Check app status
heroku ps -a hirecj-auth

# View logs
heroku logs --tail -a hirecj-auth

# Test the endpoints
curl https://auth.hirecj.ai/health
curl https://auth.hirecj.ai/ping
```

## 9. Set OAuth Provider Credentials

Once you have OAuth app credentials:
```bash
# Shopify OAuth
heroku config:set SHOPIFY_CLIENT_ID=your_client_id -a hirecj-auth
heroku config:set SHOPIFY_CLIENT_SECRET=your_client_secret -a hirecj-auth

# Add other providers as needed...
```

## Monitoring

```bash
# View metrics
heroku metrics -a hirecj-auth

# View database info
heroku pg:info -a hirecj-auth
```