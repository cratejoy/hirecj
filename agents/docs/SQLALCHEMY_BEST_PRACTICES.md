# SQLAlchemy Best Practices Guide

This guide provides comprehensive best practices for using SQLAlchemy in the HireCJ agents codebase.

## Core Principles

1. **Models are data containers, not business logic centers**
2. **Sessions are passed down, never created in lib functions**
3. **Database does the heavy lifting, not Python**
4. **Explicit is better than implicit**

## Model Design

### The Golden Rule: Keep Models Thin

Models should only contain:
- Column definitions
- Relationships
- Simple computed properties
- Basic validation

### Good Model Example

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.dbmodels.base import Base

class FreshdeskUnifiedTicketView(Base):
    """
    Good example: A thin model that only defines data structure.
    """
    __tablename__ = 'freshdesk_unified_ticket_view'
    
    # Columns
    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, nullable=False, index=True)
    freshdesk_ticket_id = Column(String, nullable=False, index=True)
    status = Column(Integer, nullable=False, index=True)
    priority = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), index=True)
    updated_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    
    # JSON columns for flexible data
    tags = Column(JSONB, default=list)
    custom_fields = Column(JSONB, default=dict)
    
    # Relationships
    conversations = relationship("FreshdeskConversation", back_populates="ticket")
    ratings = relationship("FreshdeskRating", back_populates="ticket")
    
    # Simple properties only
    @property
    def is_open(self):
        """Simple status check - no business logic."""
        return self.status in [2, 3, 6, 7]
    
    @property
    def is_resolved(self):
        """Simple status check."""
        return self.status in [4, 5]
    
    @property
    def age_hours(self):
        """Simple calculation based on model data."""
        if self.created_at:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            return (now - self.created_at).total_seconds() / 3600
        return 0
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_merchant_status', 'merchant_id', 'status'),
        Index('idx_merchant_created', 'merchant_id', 'created_at'),
    )
```

### Bad Model Example (Anti-patterns)

```python
class FreshdeskTicket(Base):
    """
    BAD example: Model with too much business logic.
    """
    __tablename__ = 'freshdesk_tickets'
    
    # ❌ Importing business logic modules
    from app.lib.sla_calculator import calculate_breach
    from app.lib.analytics import analyze_trends
    
    # ❌ Complex business logic method
    def check_sla_breach(self):
        """This belongs in a service/lib, not the model!"""
        from app.lib.sla_calculator import SLACalculator
        calculator = SLACalculator()
        return calculator.check_breach(self)
    
    # ❌ Creating its own database session
    def get_similar_tickets(self):
        """Models should never create sessions!"""
        from app.utils.supabase_util import get_db_session
        with get_db_session() as session:
            return session.query(FreshdeskTicket).filter(
                FreshdeskTicket.tags.overlap(self.tags)
            ).all()
    
    # ❌ External API calls
    def sync_with_freshdesk(self):
        """Models should not make external calls!"""
        import requests
        response = requests.get(f"https://api.freshdesk.com/tickets/{self.id}")
        self.data = response.json()
    
    # ❌ Complex aggregations
    def calculate_team_metrics(self):
        """This is analytics logic, not model responsibility!"""
        from app.lib.analytics import TeamAnalytics
        return TeamAnalytics.calculate_for_ticket(self)
```

## Session Management

### The Cardinal Rule: Pass Sessions Down

Sessions should be created at the entry point (API endpoint, script main, etc.) and passed down through all function calls.

### Good Session Patterns

```python
# ✅ Entry point creates session
@router.get("/analytics/daily-snapshot")
async def get_daily_snapshot(merchant_id: int):
    with get_db_session() as session:
        # Pass session to service layer
        snapshot = AnalyticsService.get_daily_snapshot(session, merchant_id)
        return {"data": snapshot}

# ✅ Service layer receives session
class AnalyticsService:
    @staticmethod
    def get_daily_snapshot(session: Session, merchant_id: int, date: date):
        # Pass session to data access layer
        tickets = TicketRepository.get_tickets_for_date(session, merchant_id, date)
        metrics = MetricsCalculator.calculate(session, tickets)
        return metrics

# ✅ Repository layer receives session
class TicketRepository:
    @staticmethod
    def get_tickets_for_date(session: Session, merchant_id: int, date: date):
        return session.query(FreshdeskTicket).filter(
            FreshdeskTicket.merchant_id == merchant_id,
            func.date(FreshdeskTicket.created_at) == date
        ).all()

# ✅ Bulk operations in single transaction
def migrate_merchant_data(session: Session, old_id: int, new_id: int):
    try:
        # Update all tickets
        session.query(FreshdeskTicket).filter(
            FreshdeskTicket.merchant_id == old_id
        ).update({"merchant_id": new_id})
        
        # Update all conversations
        session.query(FreshdeskConversation).filter(
            FreshdeskConversation.merchant_id == old_id
        ).update({"merchant_id": new_id})
        
        session.commit()
        logger.info(f"Migrated merchant {old_id} to {new_id}")
    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {e}")
        raise
```

### Bad Session Patterns

```python
# ❌ Creating session in library function
def calculate_metrics(merchant_id: int):
    with get_db_session() as session:  # NO! Should receive session
        tickets = session.query(FreshdeskTicket).all()
        return process(tickets)

# ❌ Multiple sessions for one operation
def process_tickets(ticket_ids: List[int]):
    results = []
    for ticket_id in ticket_ids:
        with get_db_session() as session:  # NO! N sessions
            ticket = session.query(FreshdeskTicket).get(ticket_id)
            ticket.processed = True
            session.commit()  # N commits!
            results.append(ticket.id)
    return results

# ❌ Session in model instance method
class Ticket(Base):
    def mark_as_processed(self):
        with get_db_session() as session:  # NO! Model creating session
            session.add(self)
            self.processed = True
            session.commit()

# ❌ Implicit session access
from sqlalchemy import inspect

class Ticket(Base):
    def get_related(self):
        session = inspect(self).session  # NO! Implicit session access
        return session.query(Ticket).filter(...)
```

## Query Optimization

### 1. Merchant Isolation is Non-Negotiable

```python
# ✅ ALWAYS filter by merchant_id first
def get_open_tickets(session: Session, merchant_id: int):
    return session.query(FreshdeskTicket).filter(
        FreshdeskTicket.merchant_id == merchant_id,  # FIRST filter
        FreshdeskTicket.status.in_([2, 3, 6, 7])
    ).all()

# ✅ Even in complex queries
def get_ticket_stats(session: Session, merchant_id: int):
    return session.query(
        func.date(FreshdeskTicket.created_at).label('date'),
        func.count(FreshdeskTicket.id).label('count')
    ).filter(
        FreshdeskTicket.merchant_id == merchant_id  # ALWAYS first
    ).group_by(
        func.date(FreshdeskTicket.created_at)
    ).all()
```

### 2. Prevent N+1 Queries

```python
# ❌ BAD: N+1 query problem
tickets = session.query(FreshdeskTicket).all()
for ticket in tickets:
    # Each access triggers a new query!
    print(f"Ticket has {len(ticket.conversations)} conversations")

# ✅ GOOD: Eager loading
from sqlalchemy.orm import joinedload, selectinload

# Use joinedload for one-to-one or small one-to-many
tickets = session.query(FreshdeskTicket).options(
    joinedload(FreshdeskTicket.assignee),
    joinedload(FreshdeskTicket.requester)
).all()

# Use selectinload for larger one-to-many
tickets = session.query(FreshdeskTicket).options(
    selectinload(FreshdeskTicket.conversations),
    selectinload(FreshdeskTicket.attachments)
).all()

# Now this doesn't trigger new queries
for ticket in tickets:
    print(f"Ticket has {len(ticket.conversations)} conversations")
```

### 3. Use Database Aggregations

```python
# ❌ BAD: Loading all data to Python
tickets = session.query(FreshdeskTicket).filter(
    FreshdeskTicket.merchant_id == merchant_id
).all()
avg_response_time = sum(t.first_response_time for t in tickets) / len(tickets)

# ✅ GOOD: Let database calculate
from sqlalchemy import func

result = session.query(
    func.avg(FreshdeskTicket.first_response_time).label('avg_response'),
    func.count(FreshdeskTicket.id).label('total'),
    func.min(FreshdeskTicket.first_response_time).label('min_response'),
    func.max(FreshdeskTicket.first_response_time).label('max_response')
).filter(
    FreshdeskTicket.merchant_id == merchant_id
).first()

avg_response_time = result.avg_response
```

### 4. Efficient Filtering

```python
# ❌ BAD: Loading then filtering in Python
all_tickets = session.query(FreshdeskTicket).all()
open_tickets = [t for t in all_tickets if t.status in [2, 3, 6, 7]]

# ✅ GOOD: Filter in database
open_tickets = session.query(FreshdeskTicket).filter(
    FreshdeskTicket.status.in_([2, 3, 6, 7])
).all()

# ✅ GOOD: Complex filters
from sqlalchemy import and_, or_

urgent_or_high_priority = session.query(FreshdeskTicket).filter(
    and_(
        FreshdeskTicket.merchant_id == merchant_id,
        or_(
            FreshdeskTicket.priority == 4,  # Urgent
            and_(
                FreshdeskTicket.priority == 3,  # High
                FreshdeskTicket.created_at < datetime.now() - timedelta(hours=24)
            )
        )
    )
).all()
```

### 5. Pagination for Large Results

```python
# ❌ BAD: Loading thousands of records
all_tickets = session.query(FreshdeskTicket).filter(
    FreshdeskTicket.merchant_id == merchant_id
).all()  # Could be thousands!

# ✅ GOOD: Paginate results
def get_tickets_paginated(session: Session, merchant_id: int, page: int = 1, per_page: int = 100):
    query = session.query(FreshdeskTicket).filter(
        FreshdeskTicket.merchant_id == merchant_id
    ).order_by(FreshdeskTicket.created_at.desc())
    
    total = query.count()
    tickets = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "tickets": tickets,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page
    }

# ✅ GOOD: Or use yield for streaming
def stream_all_tickets(session: Session, merchant_id: int, batch_size: int = 1000):
    offset = 0
    while True:
        batch = session.query(FreshdeskTicket).filter(
            FreshdeskTicket.merchant_id == merchant_id
        ).offset(offset).limit(batch_size).all()
        
        if not batch:
            break
            
        yield from batch
        offset += batch_size
```

## Performance Patterns

### 1. Bulk Operations

```python
# ❌ BAD: Individual inserts
for ticket_data in ticket_list:
    ticket = FreshdeskTicket(**ticket_data)
    session.add(ticket)
    session.commit()  # Commit per record!

# ✅ GOOD: Bulk insert
session.bulk_insert_mappings(FreshdeskTicket, ticket_list)
session.commit()  # Single commit

# ✅ GOOD: Bulk update
session.query(FreshdeskTicket).filter(
    FreshdeskTicket.merchant_id == merchant_id,
    FreshdeskTicket.status == 2
).update({"status": 3, "updated_at": datetime.utcnow()})
session.commit()
```

### 2. Query Only What You Need

```python
# ❌ BAD: Loading full objects for single field
tickets = session.query(FreshdeskTicket).all()
ticket_ids = [t.id for t in tickets]

# ✅ GOOD: Query specific columns
ticket_ids = session.query(FreshdeskTicket.id).all()
ticket_ids = [id[0] for id in ticket_ids]

# ✅ BETTER: Use scalars for single column
ticket_ids = session.query(FreshdeskTicket.id).scalars().all()

# ✅ GOOD: Named tuples for multiple columns
from sqlalchemy import select

result = session.execute(
    select(
        FreshdeskTicket.id,
        FreshdeskTicket.subject,
        FreshdeskTicket.status
    ).where(FreshdeskTicket.merchant_id == merchant_id)
).all()

for ticket_id, subject, status in result:
    print(f"Ticket {ticket_id}: {subject} (status: {status})")
```

### 3. Connection Pool Configuration

```python
# Configure in your database URL or engine creation
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Number of connections to maintain
    max_overflow=40,     # Maximum overflow connections
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
)
```

## Testing Patterns

### 1. Transaction Rollback Pattern

```python
import pytest
from app.utils.supabase_util import get_db_session

class TestTicketAnalytics:
    @pytest.fixture
    def db_session(self):
        """Provides a session that rolls back after each test."""
        session = get_db_session()
        session.begin_nested()  # Start savepoint
        
        yield session
        
        session.rollback()  # Rollback to savepoint
        session.close()
    
    def test_calculate_metrics(self, db_session):
        # Create test data
        ticket = FreshdeskTicket(
            merchant_id=1,
            status=2,
            subject="Test Ticket"
        )
        db_session.add(ticket)
        db_session.flush()  # Get ID without committing
        
        # Test your function
        metrics = calculate_metrics(db_session, merchant_id=1)
        
        assert metrics['total_tickets'] == 1
        # Data is automatically rolled back after test
```

### 2. Factory Pattern for Test Data

```python
from datetime import datetime, timedelta
import factory
from factory.alchemy import SQLAlchemyModelFactory

class TicketFactory(SQLAlchemyModelFactory):
    class Meta:
        model = FreshdeskTicket
        sqlalchemy_session_persistence = 'flush'
    
    merchant_id = 1
    status = 2
    priority = 2
    subject = factory.Faker('sentence')
    created_at = factory.Faker('date_time_between', start_date='-30d', end_date='now')
    
    @factory.lazy_attribute
    def resolved_at(self):
        if self.status in [4, 5]:
            return self.created_at + timedelta(hours=24)
        return None

# Usage in tests
def test_sla_breach(db_session):
    # Create tickets with specific attributes
    urgent_ticket = TicketFactory.create(
        priority=4,
        created_at=datetime.now() - timedelta(hours=2),
        first_responded_at=None  # No response yet
    )
    
    breaches = get_sla_breaches(db_session, merchant_id=1)
    assert len(breaches) == 1
    assert breaches[0].id == urgent_ticket.id
```

## Common Mistakes and Solutions

### 1. Detached Instance Error

```python
# ❌ Problem: Using object after session closes
def get_ticket():
    with get_db_session() as session:
        return session.query(FreshdeskTicket).first()

ticket = get_ticket()
print(ticket.conversations)  # Error! Session closed

# ✅ Solution 1: Keep session open
def process_ticket(ticket_id: int):
    with get_db_session() as session:
        ticket = session.query(FreshdeskTicket).get(ticket_id)
        # Do all work within session context
        conversations = ticket.conversations
        return {"id": ticket.id, "conversation_count": len(conversations)}

# ✅ Solution 2: Eager load and convert to dict
def get_ticket_data(ticket_id: int):
    with get_db_session() as session:
        ticket = session.query(FreshdeskTicket).options(
            joinedload(FreshdeskTicket.conversations)
        ).get(ticket_id)
        
        return {
            "id": ticket.id,
            "conversations": [
                {"id": c.id, "body": c.body} 
                for c in ticket.conversations
            ]
        }
```

### 2. Circular Imports

```python
# ❌ Problem: Model importing from lib
# models/ticket.py
from app.lib.analytics import calculate_score  # Circular!

class Ticket(Base):
    def get_score(self):
        return calculate_score(self)

# ✅ Solution: Keep logic in lib, models stay thin
# lib/analytics.py
def calculate_ticket_score(session: Session, ticket_id: int):
    ticket = session.query(Ticket).get(ticket_id)
    # Calculate score here
    return score

# models/ticket.py - No imports from lib!
class Ticket(Base):
    # Just data definition
    pass
```

### 3. Memory Issues with Large Queries

```python
# ❌ Problem: Loading millions of records
all_tickets = session.query(FreshdeskTicket).all()  # OOM!

# ✅ Solution 1: Use yield_per for streaming
for ticket in session.query(FreshdeskTicket).yield_per(1000):
    process_ticket(ticket)

# ✅ Solution 2: Process in batches
def process_all_tickets(session: Session, merchant_id: int):
    batch_size = 1000
    offset = 0
    
    while True:
        batch = session.query(FreshdeskTicket).filter(
            FreshdeskTicket.merchant_id == merchant_id
        ).offset(offset).limit(batch_size).all()
        
        if not batch:
            break
        
        for ticket in batch:
            process_ticket(ticket)
        
        offset += batch_size
        session.expire_all()  # Clear session cache
```

## Summary Checklist

✅ **DO:**
- Keep models thin - data definition only
- Pass sessions down from entry points
- Filter by merchant_id first in every query
- Use database aggregations, not Python
- Eager load relationships to prevent N+1
- Handle transactions explicitly
- Return data dictionaries, not model instances
- Use bulk operations for multiple records

❌ **DON'T:**
- Put business logic in models
- Create sessions in library functions
- Import lib modules in models
- Use implicit session access (inspect)
- Load all data then filter in Python
- Commit inside loops
- Make external API calls from models
- Forget to handle transaction rollbacks

Following these practices ensures maintainable, performant, and secure database operations.