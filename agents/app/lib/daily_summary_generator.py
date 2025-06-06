"""Daily summary generator that coordinates all components."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from .daily_summary_db import DailySummaryDB


class DailySummaryGenerator:
    """Orchestrates the generation of daily support summaries."""
    
    def __init__(self, db_session: Session):
        """
        Initialize the generator with all components.
        
        Args:
            db_session: Database session for operations
        """
        self.db = DailySummaryDB(db_session)
        self.session = db_session
    
    def generate_summary(self, merchant_id: int, date: datetime, force: bool = False) -> Dict[str, Any]:
        """
        Generate a complete daily summary for a merchant.
        
        Args:
            merchant_id: Merchant ID
            date: Date to generate summary for
            force: Force regeneration even if summary exists
            
        Returns:
            Dictionary with summary details and status
        """
        try:
            # Check if summary already exists (unless force is True)
            if not force:
                existing = self.db.get_existing_summary(merchant_id, date)
                if existing:
                    return {
                        'status': 'exists',
                        'summary': existing,
                        'message': existing['message']
                    }
            
            # Get tickets for the day
            daily_tickets = self.db.get_tickets_for_date(merchant_id, date)
            
            if not daily_tickets:
                # No tickets for this day
                return {
                    'status': 'no_data',
                    'message': None,
                    'reason': 'No tickets found for this date'
                }
            
            # Get tickets for CSAT comparison (30 days)
            comparison_start = date - timedelta(days=30)
            all_tickets = self.db.get_tickets_for_date_range(
                merchant_id, comparison_start, date + timedelta(days=1)
            )
            
            # TODO: Replace with new summary generation logic
            message = ""  # Empty string for now since DB requires non-null
            context = {}
            
            # Save to database
            summary_id = self.db.save_summary(
                merchant_id, date, message, context
            )
            
            return {
                'status': 'created',
                'summary_id': summary_id,
                'message': message,
                'context': context
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': None,
                'error': str(e)
            }
    
    def generate_for_date_range(self, merchant_id: int, 
                               start_date: datetime,
                               end_date: datetime) -> List[Dict[str, Any]]:
        """
        Generate summaries for a range of dates.
        
        Args:
            merchant_id: Merchant ID
            start_date: Start of range
            end_date: End of range
            
        Returns:
            List of generation results
        """
        # Get dates needing summaries
        dates_needed = self.db.get_completed_days_needing_summaries(
            merchant_id, start_date, end_date
        )
        
        results = []
        for date in dates_needed:
            result = self.generate_summary(merchant_id, date)
            result['date'] = date.isoformat()
            results.append(result)
        
        return results
    
    def generate_for_all_merchants(self, date: datetime) -> Dict[str, Any]:
        """
        Generate summaries for all merchants for a specific date.
        
        Args:
            date: Date to generate summaries for
            
        Returns:
            Summary of generation results
        """
        # Get merchants needing summaries
        merchants = self.db.get_merchants_needing_summaries(date)
        
        results = {
            'total_merchants': len(merchants),
            'successful': 0,
            'failed': 0,
            'no_data': 0,
            'details': []
        }
        
        for merchant_id, merchant_name in merchants:
            result = self.generate_summary(merchant_id, date)
            result['merchant_id'] = merchant_id
            result['merchant_name'] = merchant_name
            
            # Update counters
            if result['status'] == 'created':
                results['successful'] += 1
            elif result['status'] == 'no_data':
                results['no_data'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append(result)
        
        return results
    
    def preview_summary(self, merchant_id: int, date: datetime) -> Dict[str, Any]:
        """
        Generate a preview of what the summary would look like without saving.
        
        Args:
            merchant_id: Merchant ID
            date: Date to preview
            
        Returns:
            Preview data including formatted message
        """
        try:
            # Get tickets for the day
            daily_tickets = self.db.get_tickets_for_date(merchant_id, date)
            
            if not daily_tickets:
                return {
                    'status': 'no_data',
                    'message': None,
                    'reason': 'No tickets found for this date'
                }
            
            # Get tickets for comparison
            comparison_start = date - timedelta(days=30)
            all_tickets = self.db.get_tickets_for_date_range(
                merchant_id, comparison_start, date + timedelta(days=1)
            )
            
            # TODO: Replace with new summary generation logic
            message = ""  # Empty string for now since DB requires non-null
            context = {}
            
            return {
                'status': 'preview',
                'message': message,
                'preview': None,
                'context': context,
                'metrics': {},
                'issues': []
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': None,
                'error': str(e)
            }
    
    def backfill_summaries(self, merchant_id: int, days_back: int = 7) -> Dict[str, Any]:
        """
        Backfill missing summaries for past days.
        
        Args:
            merchant_id: Merchant ID
            days_back: Number of days to go back
            
        Returns:
            Summary of backfill results
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        
        results = self.generate_for_date_range(merchant_id, start_date, end_date)
        
        summary = {
            'total_days': len(results),
            'created': sum(1 for r in results if r['status'] == 'created'),
            'skipped': sum(1 for r in results if r['status'] == 'exists'),
            'no_data': sum(1 for r in results if r['status'] == 'no_data'),
            'errors': sum(1 for r in results if r['status'] == 'error'),
            'details': results
        }
        
        return summary