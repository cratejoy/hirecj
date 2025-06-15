# Editor Tunnels Integration

The editor is now fully integrated into the main HireCJ tunnels workflow.

## What's Included

1. **Ngrok Tunnel** - Editor frontend gets its own HTTPS tunnel on port 5173
2. **Tmux Window** - Editor runs in window 6 of the hirecj-tunnels session
3. **Logs** - Editor logs are included in the combined logs window

## Usage

From the project root:

```bash
# Start everything with tunnels
make dev-tunnels-tmux

# This creates:
# Window 0: URL list (shows all tunnel URLs)
# Window 1: Ngrok tunnels
# Window 2: Agents service (editor backend + main API)
# Window 3: Auth service
# Window 4: Database service
# Window 5: Homepage
# Window 6: Editor frontend ← NEW
# Window 7: Combined logs

# Stop everything
make stop-tunnels
```

## Accessing the Editor

After running `make dev-tunnels-tmux`:

1. Switch to window 0 to see all tunnel URLs
2. Find the editor URL (will be something like `https://xxx.ngrok.io`)
3. Access the editor via HTTPS for testing

## Notes

- Editor backend API is served by the agents service (window 2)
- Editor frontend runs independently in window 6
- Both services get ngrok tunnels for HTTPS development
- The setup follows the exact same pattern as other HireCJ services