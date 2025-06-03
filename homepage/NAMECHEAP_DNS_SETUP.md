# Namecheap DNS Configuration for hirecj.ai

## Overview
This guide will help you configure Namecheap DNS to point hirecj.ai to your Heroku app, with www.hirecj.ai redirecting to the root domain.

## DNS Configuration Steps

### 1. Log into Namecheap
1. Go to https://www.namecheap.com
2. Sign in to your account
3. Go to "Domain List" in your dashboard
4. Find `hirecj.ai` and click "Manage"

### 2. Configure DNS Records
In the "Advanced DNS" tab, add the following records:

#### Remove Default Records
First, delete any existing A records, CNAME records, or URL redirect records for @ and www.

#### Add New Records

1. **Root Domain (hirecj.ai) - ALIAS Record**
   - Type: `ALIAS Record` (or `ANAME` if ALIAS is not available)
   - Host: `@`
   - Value: `powerful-alpaca-3ee6da4ltgpmoj3az3auz8mo.herokudns.com`
   - TTL: `Automatic` or `300`

   **Note**: If Namecheap doesn't support ALIAS/ANAME records, use this alternative:
   - Type: `URL Redirect Record`
   - Host: `@`
   - Value: `https://www.hirecj.ai`
   - Select: `Permanent (301)`

2. **WWW Subdomain - CNAME Record**
   - Type: `CNAME Record`
   - Host: `www`
   - Value: `metaphysical-cassava-9h8f8b6c1jkmzxprh06gzwbs.herokudns.com`
   - TTL: `Automatic` or `300`

### 3. Configure Redirect (www to root)
Since you want www.hirecj.ai to redirect to hirecj.ai, we need to handle this at the application level.

#### Option A: If using ALIAS record for root domain
The redirect from www to root will be handled by your application code.

#### Option B: If Namecheap doesn't support ALIAS records
1. Use Namecheap's forwarding:
   - Type: `URL Redirect Record`
   - Host: `@`
   - Value: `https://www.hirecj.ai`
   - Select: `Permanent (301)`

2. Then point www to Heroku:
   - Type: `CNAME Record`
   - Host: `www`
   - Value: `metaphysical-cassava-9h8f8b6c1jkmzxprh06gzwbs.herokudns.com`

### 4. Wait for DNS Propagation
- DNS changes can take up to 48 hours to propagate globally
- Usually, it takes 15-30 minutes

### 5. Verify SSL Certificate
Once DNS is configured:
```bash
heroku certs:auto:enable -a hirecj-website
```

## Application-Level Redirect

To ensure www.hirecj.ai redirects to hirecj.ai, I'll add server-side redirect logic: