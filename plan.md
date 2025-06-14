
# Phase-5  –  Deterministic Shopify OAuth handshake

Goal

────

Single, loss-proof source of truth for Shopify-OAuth state while removing
PII from URLs and eliminating timing windows between the four “sessions”.

Principles

──────────
1.  Only the **HTTP cookie session** (`web_sessions` row) is authoritative.  
2.  Web-socket and runtime `Session` *mirror* that data; they never invent it.  
3.  Front-end is “dumb”: it just notifies `oauth_complete` with an empty body.  
4.  Every step is idempotent; a reconnect or page refresh cannot lose state.  
5.  Fail fast – missing metadata raises, does **not** fall back silently.

Data structure stored in DB:

```json
{
  "oauth_metadata": {
    "provider": "shopify",
    "shop_domain": "foo.myshopify.com",
    "merchant_id": 42,
    "is_new": true
  },
  "next_workflow": "shopify_post_auth"
}
```

Complete control-flow

─────────────────────
1.  (User clicks **Connect Shopify**)  
    • Front-end fetches `/state` JWT → builds Shopify redirect.

2.  (Shopify redirects to `/callback`)  
    • Token exchange succeeds.  
    • `issue_session(user_id)` → sets `hirecj_session` cookie.  
    • **NEW:** `oauth_metadata` JSON is written into
      `web_sessions.data` together with `"next_workflow":"shopify_post_auth"`.

3.  Browser lands back on `/chat?oauth=complete`  
    • `useOAuthCallback` immediately sends  
      `{type:"oauth_complete",data:{}}`.  (No URL parsing, no localStorage.)

4.  WebSocket connect  
    a.  Handler loads the DB row for the cookie.  
    b.  Copies `session.data` into fresh `ws_session["data"]`.  
    c.  If `oauth_metadata` present, also seeds  
        `ws_session["oauth_metadata"]`, `shop_domain`, `merchant_id`.

5.  `handle_oauth_complete` (now idempotent)  
    • Re-computes `oauth_metadata` (falls back to DB row if payload empty).  
    • Writes it to **all three layers**:  
      – ws_session  
      – live Session (if exists)  
      – DB (`update web_sessions set data->'oauth_metadata' = …`).  
    • Sends `oauth_processed` ack (success/fail).  
    • Hard `RuntimeError` if metadata still missing.

6.  `start_conversation` → `SessionManager.create_session`  
    • New arg `ws_session` passed in.  
    • If `ws_session["oauth_metadata"]` exists, copy into
      `session.oauth_metadata` **before** CJ agent creation.

7.  CJ agent creation always receives non-None `oauth_metadata` ⇒
    Shopify tools load deterministically.

Front-end clean-up

──────────────────
* Remove all URL-param parsing & `userSession.setMerchant`.  
* Remove `localStorage` dependency entirely (may keep hook for UI toggles).

Hard-fail guarantees

────────────────────
* Any missing token/shop_domain raises `RuntimeError` in
  `handle_oauth_complete` → WebSocket error envelope → visible to user/dev.  
* Silent DB lookup fall-backs are deleted.

Migration steps

───────────────
1. SQL: `alter table web_sessions alter column data set default '{}'::jsonb;`
2. Deploy auth-service change first (starts writing metadata).  
3. Deploy agents-service (reads new column, implements copy logic).  
4. Remove legacy URL/LocalStorage code from homepage.

Expected outcome

────────────────
• 0 % tool-hallucination.  
• OAuth flow works across refreshes and multi-tab.  
• Secrets never travel through URLs.  
• One unified debugging point: `web_sessions.data`.
