#!/usr/bin/env python3
"""
Clean up expired web sessions from the database.

This script should be run periodically (e.g., via cron) to remove
expired sessions and free up database space.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete
from app.utils.supabase_util import get_db_session
from shared.db_models import WebSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_expired_sessions():
    """Remove all expired sessions from the database."""
    try:
        with get_db_session() as db:
            # Delete all sessions where expires_at is in the past
            result = db.execute(
                delete(WebSession)
                .where(WebSession.expires_at < datetime.utcnow())
            )
            db.commit()
            
            count = result.rowcount
            logger.info(f"[CLEANUP] Removed {count} expired sessions")
            
            # Also log some statistics
            active_count = db.query(WebSession).count()
            logger.info(f"[CLEANUP] {active_count} active sessions remaining")
            
            return count
            
    except Exception as e:
        logger.error(f"[CLEANUP] Error during session cleanup: {e}", exc_info=True)
        return 0


def cleanup_orphaned_sessions(older_than_hours=48):
    """
    Remove sessions that haven't been accessed in a long time,
    even if they haven't technically expired yet.
    
    This handles edge cases where sessions might have very long
    expiration times but are clearly abandoned.
    """
    try:
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        with get_db_session() as db:
            result = db.execute(
                delete(WebSession)
                .where(WebSession.last_accessed_at < cutoff_time)
            )
            db.commit()
            
            count = result.rowcount
            if count > 0:
                logger.info(f"[CLEANUP] Removed {count} orphaned sessions "
                           f"(not accessed in {older_than_hours} hours)")
            
            return count
            
    except Exception as e:
        logger.error(f"[CLEANUP] Error during orphaned session cleanup: {e}", exc_info=True)
        return 0


def main():
    """Run session cleanup."""
    logger.info("[CLEANUP] Starting session cleanup job")
    
    # Clean up expired sessions
    expired_count = cleanup_expired_sessions()
    
    # Clean up orphaned sessions (optional, more aggressive)
    orphaned_count = cleanup_orphaned_sessions()
    
    total_count = expired_count + orphaned_count
    logger.info(f"[CLEANUP] Session cleanup complete - removed {total_count} total sessions")


if __name__ == "__main__":
    main()