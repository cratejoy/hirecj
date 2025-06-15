"""
Simplified user identity for HireCJ - Phase 4.5

Just 6 functions, ~140 lines. No over-engineering.
Direct PostgreSQL connection for full control.
Includes fact storage as JSONB documents.

CRITICAL: This is the AUTHORITATIVE source for user identity generation.
All user IDs MUST be generated through this module's functions.
Frontend should NEVER attempt to generate user IDs.

User ID Format: usr_xxxxxxxx (8 character hex from SHA256 of normalized domain)
Example: cratejoy-dev.myshopify.com → usr_2230c443
"""

import hashlib
import json
import os
import logging
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from contextlib import contextmanager

# Simple logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@contextmanager
def get_db_connection():
    """Get PostgreSQL connection using context manager."""
    # Use the single, authoritative env loader
    db_url = os.getenv("SUPABASE_CONNECTION_STRING")
    
    if not db_url:
        logger.error("SUPABASE_CONNECTION_STRING not set")
        raise ValueError("Database connection not configured")
    
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def generate_user_id(shop_domain: str) -> str:
    """Generate consistent user ID from shop domain."""
    # Normalize domain
    domain = shop_domain.lower().strip()
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.replace("www.", "").rstrip("/")
    
    # Generate ID
    hash_obj = hashlib.sha256(domain.encode('utf-8'))
    short_hash = hash_obj.hexdigest()[:8]
    return f"usr_{short_hash}"


def get_or_create_user(shop_domain: str, email: Optional[str] = None) -> Tuple[str, bool]:
    """Get existing user or create new one. Returns (user_id, is_new)."""
    user_id = generate_user_id(shop_domain)
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Try to get existing user
            cur.execute(
                "SELECT id FROM users WHERE id = %s OR shop_domain = %s",
                (user_id, shop_domain)
            )
            existing = cur.fetchone()
            
            if existing:
                logger.debug(f"Found existing user: {existing['id']}")
                return existing['id'], False
            
            # Create new user
            try:
                cur.execute(
                    """
                    INSERT INTO users (id, shop_domain, email, created_at)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, shop_domain, email, datetime.utcnow())
                )
                conn.commit()
                logger.info(f"Created new user: {user_id}")
                return user_id, True
            except psycopg2.IntegrityError:
                # Race condition - user was created by another process
                conn.rollback()
                cur.execute("SELECT id FROM users WHERE shop_domain = %s", (shop_domain,))
                existing = cur.fetchone()
                return existing['id'], False


def save_conversation_message(user_id: str, message: Dict[str, Any]) -> None:
    """Save a single message to conversations table."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (user_id, message, created_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, Json(message), datetime.utcnow())
            )
            conn.commit()
            logger.debug(f"Saved message for user {user_id}")


def get_user_conversations(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent conversations for a user."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, message, created_at
                FROM conversations
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            results = cur.fetchall()
            
            # Convert to list of dicts
            conversations = []
            for row in results:
                conv = dict(row)
                conv['created_at'] = conv['created_at'].isoformat()
                conversations.append(conv)
            
            return conversations


def append_fact(user_id: str, fact: str, source: str) -> None:
    """Append a fact to user's fact array."""
    fact_obj = {
        "fact": fact,
        "source": source,
        "learned_at": datetime.utcnow().isoformat()
    }
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Use JSONB array append - creates row if doesn't exist
            cur.execute(
                """
                INSERT INTO user_facts (user_id, facts, updated_at)
                VALUES (%s, %s::jsonb, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET 
                    facts = user_facts.facts || %s::jsonb,
                    updated_at = EXCLUDED.updated_at
                """,
                (user_id, Json([fact_obj]), datetime.utcnow(), Json([fact_obj]))
            )
            conn.commit()
            logger.debug(f"Appended fact for user {user_id}")


def get_user_facts(user_id: str) -> List[Dict[str, Any]]:
    """Get all facts for a user."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT facts FROM user_facts WHERE user_id = %s",
                (user_id,)
            )
            result = cur.fetchone()
            
            if result and result['facts']:
                return result['facts']
            return []
