#!/bin/bash
# Test cookie flow with WebSocket proxy

echo "=== Cookie Flow Test ==="
echo

# Create a test session in the database
echo "1. Creating test session..."
python -c "
import sys
sys.path.insert(0, '.')
from agents.app.utils.supabase_util import get_db_session
from shared.db_models import WebSession, User
from datetime import datetime, timedelta
import secrets

with get_db_session() as db:
    # Create test user first
    test_user = db.query(User).filter(User.id == 'usr_test_cookie').first()
    if not test_user:
        test_user = User(
            id='usr_test_cookie',
            shop_domain='test-cookie.myshopify.com',
            email='test@example.com'
        )
        db.add(test_user)
        db.commit()
    
    # Create session
    session_id = f'sess_{secrets.token_hex(16)}'
    session = WebSession(
        session_id=session_id,
        user_id='usr_test_cookie',
        expires_at=datetime.utcnow() + timedelta(hours=24),
        data={'test': True}
    )
    db.add(session)
    db.commit()
    
    print(f'Created session: {session_id}')
"

SESSION_ID=$(python -c "
import sys
sys.path.insert(0, '.')
from agents.app.utils.supabase_util import get_db_session
from shared.db_models import WebSession
from datetime import datetime

with get_db_session() as db:
    session = db.query(WebSession).filter(
        WebSession.user_id == 'usr_test_cookie'
    ).order_by(WebSession.created_at.desc()).first()
    if session:
        print(session.session_id)
")

echo "Session ID: $SESSION_ID"
echo

# Test API with cookie
echo "2. Testing API with session cookie..."
curl -s \
  -H "Cookie: hirecj_session=$SESSION_ID" \
  https://amir.hirecj.ai/api/v1/test-cors | jq .

echo
echo "3. Check agents service logs for:"
echo "   - [MIDDLEWARE] Found session cookie"
echo "   - [MIDDLEWARE] Loaded user usr_test_cookie from session"

echo
echo "4. Cleaning up test data..."
python -c "
import sys
sys.path.insert(0, '.')
from agents.app.utils.supabase_util import get_db_session
from shared.db_models import WebSession

with get_db_session() as db:
    db.query(WebSession).filter(WebSession.user_id == 'usr_test_cookie').delete()
    db.commit()
    print('Cleaned up test session')
"