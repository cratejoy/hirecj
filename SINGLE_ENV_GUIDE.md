# Single .env File Management - HireCJ

## 🎯 The ONE Rule

**You only edit ONE file: `.env` in the root directory**

That's it. No exceptions. No service-specific .env files. No .env.local files. Just ONE.

## 🚀 Quick Start

### 1. Initial Setup

```bash
# Create your .env file from the template
make env-setup

# Edit .env with your configuration
nano .env  # or use your favorite editor
```

### 2. Start Development

```bash
# This automatically distributes env vars to services
make dev

# Or with tmux
make dev-all
```

That's it! The system handles everything else automatically.

## 🔧 How It Works

1. **You edit `.env`** - All your configuration in one place
2. **Scripts distribute** - `distribute_env.py` copies relevant variables to each service
3. **Services read locally** - Each service reads from its auto-generated `.env`
4. **You never touch service files** - They're overwritten on each `make dev`

## 🌐 Using Tunnels (ngrok)

For tunnel development, add your ngrok authtoken to `.env`:

```bash
# In your .env file
NGROK_AUTHTOKEN=your-authtoken-here
```

Then use: `make dev-tunnels-tmux`

Tunnel URLs are auto-detected and written to `.env.tunnel`.

## 📝 Environment Variables

Your `.env` file contains ALL configuration:

- **Core Settings**: Environment, debug, logging
- **Service URLs & Ports**: All inter-service communication
- **Databases**: PostgreSQL, Redis, Supabase connections
- **API Keys**: OpenAI, Anthropic, OAuth credentials
- **Features**: All feature flags
- **Everything else**: Cache settings, timeouts, etc.

See `.env.master.example` for the complete template.

## 🛠️ Common Tasks

### Adding a New Variable

1. Add to `.env.master.example` with a descriptive comment
2. Add to your `.env` file
3. Update `scripts/distribute_env.py` to include it in the relevant service's `SERVICE_VARS`
4. Run `make dev` - it auto-distributes

### Checking What Variables a Service Gets

```bash
# Run distribution and see what each service receives
python scripts/distribute_env.py

# Check a specific service's generated .env
cat agents/.env  # DO NOT EDIT THIS FILE
```

### Verifying the Setup

```bash
# Check that single .env pattern is properly implemented
make env-verify
```

### Cleaning Up Old Files

```bash
# Remove old service-specific .env files
make env-cleanup
```

## ⚠️ Important Notes

1. **Service .env files are auto-generated** - Any edits will be lost
2. **Don't commit service .env files** - They're in .gitignore
3. **Tunnel URLs are special** - `.env.tunnel` is auto-generated and takes precedence
4. **One source of truth** - If services need different values, use different variable names

## 🔍 Troubleshooting

### "Environment variable not found"

The variable isn't being distributed to that service. Add it to `SERVICE_VARS` in `distribute_env.py`.

### "Service using old value"

Services auto-reload on file changes. If not, restart the service.

### "I see old .env files"

Run `make env-cleanup` to remove them.

### "Multiple values for same setting"

Use different variable names. Example:
- `AUTH_TIMEOUT=30` for auth service
- `AGENTS_TIMEOUT=60` for agents service

## 🎉 Benefits

1. **One file to rule them all** - No more hunting through directories
2. **No duplication** - Each variable defined once
3. **Clear source of truth** - Always know where to look
4. **Easy onboarding** - New developers edit one file
5. **Consistent deployment** - Same pattern for dev and production

## 📚 Architecture

```
.env (YOU EDIT THIS)
   ↓
distribute_env.py
   ↓
Service .env files (AUTO-GENERATED)
   ├── auth/.env
   ├── agents/.env
   ├── database/.env
   └── homepage/.env
```

The distribution script:
- Reads from master `.env`
- Filters variables each service needs
- Writes service-specific `.env` files
- Services read their local `.env` (but you never edit these)

## 🚫 What NOT to Do

1. **Don't edit service .env files** - They're overwritten automatically
2. **Don't create .env.local files** - Use the root `.env`
3. **Don't use load_dotenv() directly** - Use `shared.env_loader`
4. **Don't add service-specific .env.example files** - Update `.env.master.example`

---

Remember: **ONE .env file**. That's the entire system.