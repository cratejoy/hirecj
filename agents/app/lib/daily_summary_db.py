"""Database operations for daily summary system."""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
import json
from sqlalchemy.dialects.postgresql import JSONB


class DailySummaryDB:
    """Handles all database operations for daily summaries."""
    
    def __init__(self, session: Session):
        """
        Initialize with database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    def get_tickets_for_date(self, merchant_id: int, date: datetime) -> List[Dict[str, Any]]:
        """
        Get all tickets for a specific merchant and date.
        
        Args:
            merchant_id: Merchant ID
            date: Date to get tickets for
            
        Returns:
            List of ticket dictionaries with data from JSONB
        """
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        result = self.session.execute(
            text("""
                SELECT 
                    freshdesk_ticket_id,
                    data,
                    created_at,
                    updated_at
                FROM etl_freshdesk_tickets
                WHERE merchant_id = :merchant_id
                AND created_at >= :start_date
                AND created_at < :end_date
                ORDER BY created_at DESC
            """),
            {
                'merchant_id': merchant_id,
                'start_date': start_of_day,
                'end_date': end_of_day
            }
        )
        
        tickets = []
        for row in result:
            ticket = {
                'freshdesk_ticket_id': row[0],
                'data': row[1] if isinstance(row[1], dict) else {},
                'created_at': row[2],
                'updated_at': row[3]
            }
            tickets.append(ticket)
        
        return tickets
    
    def get_tickets_for_date_range(self, merchant_id: int, 
                                  start_date: datetime, 
                                  end_date: datetime) -> List[Dict[str, Any]]:
        """
        Get all tickets for a merchant within a date range.
        
        Args:
            merchant_id: Merchant ID
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of ticket dictionaries
        """
        result = self.session.execute(
            text("""
                SELECT 
                    freshdesk_ticket_id,
                    data,
                    created_at,
                    updated_at
                FROM etl_freshdesk_tickets
                WHERE merchant_id = :merchant_id
                AND created_at >= :start_date
                AND created_at < :end_date
                ORDER BY created_at DESC
            """),
            {
                'merchant_id': merchant_id,
                'start_date': start_date,
                'end_date': end_date
            }
        )
        
        tickets = []
        for row in result:
            ticket = {
                'freshdesk_ticket_id': row[0],
                'data': row[1] if isinstance(row[1], dict) else {},
                'created_at': row[2],
                'updated_at': row[3]
            }
            tickets.append(ticket)
        
        return tickets
    
    def get_existing_summary(self, merchant_id: int, date: datetime) -> Optional[Dict[str, Any]]:
        """
        Check if a summary already exists for a merchant and date.
        
        Args:
            merchant_id: Merchant ID
            date: Date to check
            
        Returns:
            Summary data if exists, None otherwise
        """
        result = self.session.execute(
            text("""
                SELECT 
                    id,
                    message,
                    context,
                    created_at,
                    updated_at
                FROM daily_ticket_summaries
                WHERE merchant_id = :merchant_id
                AND date = :date
            """),
            {
                'merchant_id': merchant_id,
                'date': date.date()
            }
        ).fetchone()
        
        if result:
            return {
                'id': result[0],
                'message': result[1],
                'context': result[2] if isinstance(result[2], dict) else {},
                'created_at': result[3],
                'updated_at': result[4]
            }
        
        return None
    
    def save_summary(self, merchant_id: int, date: datetime, 
                    message: str, context: Dict[str, Any]) -> int:
        """
        Save or update a daily summary.
        
        Args:
            merchant_id: Merchant ID
            date: Date of summary
            message: Formatted summary message
            context: Context data (metrics, issues, etc.)
            
        Returns:
            ID of created/updated summary
        """
        # Check if summary exists
        existing = self.get_existing_summary(merchant_id, date)
        
        if existing:
            # Update existing
            result = self.session.execute(
                text("""
                    UPDATE daily_ticket_summaries
                    SET message = :message,
                        context = :context,
                        updated_at = NOW()
                    WHERE merchant_id = :merchant_id
                    AND date = :date
                    RETURNING id
                """),
                {
                    'merchant_id': merchant_id,
                    'date': date.date(),
                    'message': message,
                    'context': json.dumps(context)
                }
            )
            summary_id = result.scalar()
            self.session.commit()
            return summary_id
        else:
            # Insert new
            result = self.session.execute(
                text("""
                    INSERT INTO daily_ticket_summaries 
                    (merchant_id, date, message, context)
                    VALUES (:merchant_id, :date, :message, :context)
                    RETURNING id
                """),
                {
                    'merchant_id': merchant_id,
                    'date': date.date(),
                    'message': message,
                    'context': json.dumps(context)
                }
            )
            summary_id = result.scalar()
            self.session.commit()
            return summary_id
    
    def get_summaries_for_range(self, merchant_id: int,
                               start_date: datetime,
                               end_date: datetime) -> List[Dict[str, Any]]:
        """
        Get all summaries for a merchant within a date range.
        
        Args:
            merchant_id: Merchant ID
            start_date: Start of range
            end_date: End of range
            
        Returns:
            List of summary dictionaries
        """
        result = self.session.execute(
            text("""
                SELECT 
                    id,
                    date,
                    message,
                    context,
                    created_at,
                    updated_at
                FROM daily_ticket_summaries
                WHERE merchant_id = :merchant_id
                AND date >= :start_date
                AND date <= :end_date
                ORDER BY date DESC
            """),
            {
                'merchant_id': merchant_id,
                'start_date': start_date.date(),
                'end_date': end_date.date()
            }
        )
        
        summaries = []
        for row in result:
            summary = {
                'id': row[0],
                'date': row[1],
                'message': row[2],
                'context': row[3] if isinstance(row[3], dict) else {},
                'created_at': row[4],
                'updated_at': row[5]
            }
            summaries.append(summary)
        
        return summaries
    
    def get_merchants_needing_summaries(self, date: datetime) -> List[Tuple[int, str]]:
        """
        Get list of merchants that need summaries for a given date.
        
        Args:
            date: Date to check
            
        Returns:
            List of (merchant_id, merchant_name) tuples
        """
        # Get all non-test merchants that don't have a summary for this date
        result = self.session.execute(
            text("""
                SELECT DISTINCT m.id, m.name
                FROM merchants m
                LEFT JOIN daily_ticket_summaries dts 
                    ON m.id = dts.merchant_id 
                    AND dts.date = :date
                WHERE m.is_test = false
                AND dts.id IS NULL
                ORDER BY m.name
            """),
            {
                'date': date.date()
            }
        )
        
        return [(row[0], row[1]) for row in result]
    
    def get_completed_days_needing_summaries(self, merchant_id: int,
                                           start_date: datetime,
                                           end_date: datetime) -> List[datetime]:
        """
        Get list of completed days that need summaries for a merchant.
        
        Args:
            merchant_id: Merchant ID
            start_date: Start of range to check
            end_date: End of range to check
            
        Returns:
            List of dates needing summaries
        """
        # Get all dates in range
        all_dates = []
        current = start_date.date()
        today = datetime.now(timezone.utc).date()
        
        while current < min(end_date.date(), today):
            all_dates.append(current)
            current += timedelta(days=1)
        
        if not all_dates:
            return []
        
        # Check which dates have summaries
        date_strings = [d.isoformat() for d in all_dates]
        
        result = self.session.execute(
            text("""
                SELECT date 
                FROM daily_ticket_summaries 
                WHERE merchant_id = :merchant_id 
                AND date IN :dates
            """),
            {
                'merchant_id': merchant_id,
                'dates': tuple(date_strings) if date_strings else tuple()
            }
        )
        
        existing_dates = {row[0] for row in result}
        
        # Return dates that don't have summaries
        missing_dates = []
        for date in all_dates:
            if date not in existing_dates:
                missing_dates.append(
                    datetime.combine(date, datetime.min.time(), tzinfo=timezone.utc)
                )
        
        return missing_dates