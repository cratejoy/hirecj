"""Shopify Custom App API routes."""

import logging
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, Query, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from urllib.parse import urlencode

from app.config import settings
from app.services.merchant_storage import merchant_storage

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/connected")
async def handle_shopify_redirect(
    shop: str = Query(..., description="Shop domain"),
    hmac: Optional[str] = Query(None, description="HMAC for verification"),
    host: Optional[str] = Query(None, description="Base64 encoded host"),
    timestamp: Optional[str] = Query(None, description="Timestamp"),
    conversation_id: Optional[str] = Query(None, description="Original conversation ID")
):
    """
    Handle redirect from Shopify after custom app installation.
    
    For custom distribution apps, Shopify doesn't provide OAuth tokens.
    Instead, merchants must manually generate and share the access token.
    """
    logger.info(f"[SHOPIFY_CONNECTED] App installed for shop: {shop}")
    
    # TODO: Verify HMAC to ensure request is from Shopify
    
    # Generate HTML form for token entry
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Complete HireCJ Setup</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                max-width: 600px;
                margin: 40px auto;
                padding: 20px;
                background: #f9f9f9;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                margin-bottom: 10px;
            }}
            .shop-name {{
                color: #666;
                font-size: 14px;
                margin-bottom: 20px;
            }}
            ol {{
                line-height: 1.8;
                color: #555;
            }}
            .form-group {{
                margin-top: 30px;
            }}
            label {{
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: #333;
            }}
            input[type="password"] {{
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
                box-sizing: border-box;
            }}
            button {{
                background: #5c6ac4;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 15px;
            }}
            button:hover {{
                background: #4a5ab3;
            }}
            .warning {{
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                padding: 12px;
                border-radius: 4px;
                margin-top: 20px;
                color: #856404;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Complete HireCJ Setup</h1>
            <div class="shop-name">Shop: {shop}</div>
            
            <div style="background: #e3f2fd; border: 1px solid #1976d2; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                <strong style="color: #1976d2;">🚀 Beta Testing Note:</strong>
                <p style="margin: 5px 0 0 0; color: #1565c0;">
                    Thank you for being a beta tester! During our beta phase, there's one extra manual step 
                    to complete the setup. This will be automated in the full release.
                </p>
            </div>
            
            <p>Thanks for installing HireCJ! To complete the setup, you'll need to provide your Admin API access token.</p>
            
            <h3>How to get your access token:</h3>
            <ol>
                <li>Go to your <strong>Shopify Admin</strong></li>
                <li>Navigate to <strong>Settings → Apps and sales channels</strong></li>
                <li>Find and click on <strong>HireCJ</strong></li>
                <li>Click on <strong>API credentials</strong></li>
                <li>Click <strong>"Reveal token once"</strong> and copy the Admin API access token</li>
                <li>Paste it below</li>
            </ol>
            
            <form action="/api/v1/shopify/save-token" method="POST" class="form-group">
                <input type="hidden" name="shop" value="{shop}" />
                <input type="hidden" name="conversation_id" value="{conversation_id or ''}" />
                
                <label for="token">Admin API Access Token:</label>
                <input type="password" name="token" id="token" required 
                       placeholder="shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
                
                <button type="submit">Complete Setup</button>
            </form>
            
            <div class="warning">
                <strong>Important:</strong> The access token is shown only once in Shopify. 
                Make sure to copy it before leaving the page.
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.post("/save-token")
async def save_merchant_token(
    shop: str = Form(...),
    token: str = Form(...),
    conversation_id: Optional[str] = Form(None)
):
    """
    Save the manually-provided access token after validating it.
    """
    logger.info(f"[SAVE_TOKEN] Attempting to save token for shop: {shop}")
    
    # Validate the token by making a test API call
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{shop}/admin/api/2024-01/shop.json",
                headers={
                    "X-Shopify-Access-Token": token,
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"[SAVE_TOKEN] Invalid token for shop {shop}: {response.status_code}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid access token. Please check and try again."
                )
        
        # Token is valid! Check if merchant exists
        merchant = await merchant_storage.get_merchant(shop)
        is_new = merchant is None
        
        if is_new:
            # Create new merchant record
            merchant_id = f"merchant_{shop.replace('.myshopify.com', '')}"
            await merchant_storage.create_merchant({
                "merchant_id": merchant_id,
                "shop_domain": shop,
                "access_token": token,
                "created_at": datetime.utcnow()
            })
            logger.info(f"[SAVE_TOKEN] New merchant created: {shop}")
        else:
            # Update existing merchant
            await merchant_storage.update_token(shop, token)
            merchant_id = merchant.get("merchant_id", f"merchant_{shop.replace('.myshopify.com', '')}")
            logger.info(f"[SAVE_TOKEN] Existing merchant updated: {shop}")
        
        # Redirect to chat with success parameters
        redirect_params = {
            "oauth": "complete",
            "is_new": str(is_new).lower(),
            "merchant_id": merchant_id,
            "shop": shop
        }
        
        if conversation_id:
            redirect_params["conversation_id"] = conversation_id
        
        redirect_url = f"{settings.frontend_url}/chat?{urlencode(redirect_params)}"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except httpx.RequestError as e:
        logger.error(f"[SAVE_TOKEN] Network error validating token: {e}")
        return HTMLResponse(
            content=f"""
            <html>
            <body style="font-family: sans-serif; padding: 20px;">
                <h2>Connection Error</h2>
                <p>Unable to connect to Shopify. Please try again.</p>
                <p>Error: {str(e)}</p>
                <a href="javascript:history.back()">Go Back</a>
            </body>
            </html>
            """,
            status_code=500
        )
    except HTTPException:
        return HTMLResponse(
            content="""
            <html>
            <body style="font-family: sans-serif; padding: 20px;">
                <h2>Invalid Token</h2>
                <p>The access token appears to be invalid. Please make sure you:</p>
                <ol>
                    <li>Copied the entire token including the "shpat_" prefix</li>
                    <li>The token has the necessary permissions</li>
                    <li>The token hasn't expired</li>
                </ol>
                <a href="javascript:history.back()">Go Back and Try Again</a>
            </body>
            </html>
            """,
            status_code=400
        )