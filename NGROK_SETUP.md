# Ngrok Setup for HireCJ Development

This guide explains how to set up ngrok for HTTPS development with HireCJ.

## Why Ngrok?

- **HTTPS in development** - Test OAuth flows and secure features locally
- **Public URLs** - Share your local development with others
- **WebSocket support** - Full duplex communication over secure tunnels
- **Reserved domains** - Consistent URLs for team members

## Initial Setup

### 1. Get Your Ngrok Authtoken

1. Sign up at [ngrok.com](https://dashboard.ngrok.com/signup) if you haven't already
2. Get your authtoken from [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)

### 2. Configure Your Authtoken

```bash
# Copy the example configuration
cp .env.ngrok.example .env.ngrok

# Edit .env.ngrok and replace 'your_authtoken_here' with your actual token
# The file should look like:
# NGROK_AUTHTOKEN=2qR9b0s...your_actual_token_here
```

### 3. Choose Your Configuration

**For Amir (with reserved domains):**
```bash
cp ngrok.yml.amir ngrok.yml
```

**For other developers:**
```bash
cp ngrok.yml.example ngrok.yml
```

## Running with Ngrok

### Quick Start (Recommended)

```bash
# Start everything with tunnels in tmux
make dev-tunnels-tmux
```

This command will:
1. Start ngrok tunnels for all services
2. Detect and configure tunnel URLs automatically
3. Start all development services
4. Open tmux with organized windows

### Manual Start

If you prefer to run things separately:

```bash
# Terminal 1: Start tunnels
make tunnels

# Terminal 2: Detect URLs (wait for tunnels to start)
make detect-tunnels

# Terminal 3: Start services
make dev-all
```

## Your URLs

### With Reserved Domains (Amir)
- Homepage: https://amir.hirecj.ai
- Auth: https://amir-auth.hirecj.ai
- Other services: https://[random].ngrok-free.app

### Without Reserved Domains
All services get random ngrok URLs like:
- https://abc123.ngrok-free.app
- https://def456.ngrok-free.app
- etc.

The exact URLs are automatically detected and configured.

## How It Works

1. **Ngrok starts** with your configuration
2. **Tunnel detector** finds all running tunnels via ngrok API
3. **Services** auto-detect their public URLs from `.env.tunnel` files
4. **CORS** dynamically allows detected URLs
5. **Frontend** uses public URLs for API and WebSocket connections
6. **HMR** works via secure WebSocket (wss://)

## Troubleshooting

### "Error: .env.ngrok file not found"
```bash
cp .env.ngrok.example .env.ngrok
# Edit the file and add your authtoken
```

### "Authentication failed"
- Check your authtoken in `.env.ngrok` is correct
- Ensure you're not using placeholder text
- Get a fresh token from https://dashboard.ngrok.com/get-started/your-authtoken

### CORS errors
- Run `make detect-tunnels` after tunnels start
- Check `.env.tunnel` files exist in service directories
- Restart services after tunnel detection

### Can't access URLs
- Check ngrok dashboard: http://localhost:4040
- Ensure all services are running
- Try `curl https://your-url/health` to test

## Security Notes

- **Never commit `.env.ngrok`** - It contains your personal authtoken
- **Don't share authtokens** - Each developer should use their own
- **Use reserved domains** for production-like testing
- **Free tier works fine** for most development needs

## Next Steps

- Read the [full test guide](NGROK_TEST_GUIDE.md) for detailed testing instructions
- Set up reserved domains if you need consistent URLs
- Configure your IDE to use HTTPS URLs for debugging