"""Freshdesk ETL library for syncing data to database."""

import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.utils.freshdesk_util import FreshdeskAPI
from app.utils.supabase_util import get_db_session
from app.dbmodels.base import Merchant, FreshdeskTicket, FreshdeskConversation, FreshdeskRating, SyncMetadata


class FreshdeskETL:
    """Orchestrates Freshdesk data sync to database."""
    
    def __init__(self, merchant_id: int):
        self.merchant_id = merchant_id
        self.api = FreshdeskAPI()
    
    def get_last_sync_timestamp(self, resource_type: str) -> Optional[datetime]:
        """Get the last successful sync timestamp for a resource."""
        with get_db_session() as session:
            sync_meta = session.query(SyncMetadata).filter_by(
                merchant_id=self.merchant_id,
                resource_type=resource_type
            ).first()
            
            if sync_meta and sync_meta.last_sync_at:
                return sync_meta.last_sync_at
            return None
    
    def update_sync_metadata(self, resource_type: str, status: str, 
                           last_successful_id: Optional[str] = None,
                           error_message: Optional[str] = None):
        """Update sync metadata for tracking."""
        with get_db_session() as session:
            stmt = insert(SyncMetadata).values(
                merchant_id=self.merchant_id,
                resource_type=resource_type,
                sync_status=status,
                last_sync_at=datetime.now(timezone.utc) if status == "success" else None,
                last_successful_id=last_successful_id,
                error_message=error_message
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['merchant_id', 'resource_type'],
                set_={
                    'sync_status': stmt.excluded.sync_status,
                    'last_sync_at': stmt.excluded.last_sync_at,
                    'last_successful_id': stmt.excluded.last_successful_id,
                    'error_message': stmt.excluded.error_message
                }
            )
            
            session.execute(stmt)
    
    def sync_tickets(self, since: Optional[datetime] = None, max_pages: Optional[int] = None) -> Dict[str, Any]:
        """Sync Freshdesk tickets to database with conversations stored separately.
        
        Tickets are stored in etl_freshdesk_tickets table.
        Conversations are stored in etl_freshdesk_conversations table.
        
        Args:
            since: Sync tickets updated since this datetime
            max_pages: Maximum number of pages to fetch (for testing)
        """
        print(f"🎫 Starting Freshdesk ticket sync for merchant {self.merchant_id}")
        print("   📝 Storing tickets and conversations in separate tables")
        print("   ✅ Tickets will be saved even if conversation fetch fails")
        
        # Mark sync as in progress
        self.update_sync_metadata("freshdesk_tickets", "in_progress")
        
        # Use last sync timestamp if not provided
        if not since:
            since = self.get_last_sync_timestamp("freshdesk_tickets")
            if since:
                print(f"   Using last sync timestamp: {since}")
        else:
            print(f"   Using provided since date: {since}")
        
        # Format timestamp for Freshdesk API
        updated_since = since.isoformat() if since else None
        
        total_synced = 0
        total_errors = 0
        last_ticket_id = None
        
        try:
            with get_db_session() as session:
                page = 1
                has_more = True
                
                while has_more:
                    print(f"  Fetching page {page}...")
                    
                    # Get tickets from API
                    tickets, next_url = self.api.get_tickets(
                        updated_since=updated_since,
                        page=page,
                        include="requester"  # Include contact data
                    )
                    
                    
                    if not tickets:
                            break
                    
                    # Process each ticket
                    for idx, ticket in enumerate(tickets, 1):
                        try:
                            ticket_id = str(ticket.get('id'))
                            requester_id = ticket.get('requester_id')
                            
                            # Prepare ticket data (core data only, no conversations)
                            ticket_data = {
                                'freshdesk_id': ticket_id,
                                'subject': ticket.get('subject'),
                                'description': ticket.get('description_text'),
                                'status': ticket.get('status'),
                                'priority': ticket.get('priority'),
                                'type': ticket.get('type'),
                                'tags': ticket.get('tags', []),
                                'created_at': ticket.get('created_at'),
                                'updated_at': ticket.get('updated_at'),
                                'due_by': ticket.get('due_by'),
                                'fr_due_by': ticket.get('fr_due_by'),  # First response due
                                'is_escalated': ticket.get('is_escalated'),
                                'custom_fields': ticket.get('custom_fields', {}),
                                # Store requester info directly in ticket
                                'requester_id': requester_id,
                                'requester': ticket.get('requester'),  # This includes email, name, etc.
                                # Store complete ticket data
                                '_raw_data': ticket
                            }
                            
                            # Show progress for large batches
                            if len(tickets) > 20 and idx % 10 == 0:
                                print(f"    Processing ticket {idx}/{len(tickets)}...")
                            
                            # Upsert the ticket (without conversations)
                            stmt = insert(FreshdeskTicket).values(
                                freshdesk_ticket_id=ticket_id,
                                merchant_id=self.merchant_id,
                                data=ticket_data
                            )
                            
                            stmt = stmt.on_conflict_do_update(
                                index_elements=['merchant_id', 'freshdesk_ticket_id'],
                                set_={
                                    'data': stmt.excluded.data
                                },
                                where=(FreshdeskTicket.data != stmt.excluded.data)  # Only update if data differs
                            )
                            
                            session.execute(stmt)
                            total_synced += 1
                            last_ticket_id = ticket_id
                            
                            # Fetch and store conversations in separate table
                            all_conversations = []
                            try:
                                conv_page = 1
                                
                                while True:
                                    conversations, conv_next_url = self.api.get_conversations(
                                        ticket_id=int(ticket_id),
                                        page=conv_page
                                    )
                                    
                                    if not conversations:
                                        break
                                        
                                    all_conversations.extend(conversations)
                                    
                                    if not conv_next_url:
                                        break
                                    conv_page += 1
                                
                                # Store conversations in separate table if we got any
                                if all_conversations:
                                    conv_stmt = insert(FreshdeskConversation).values(
                                        freshdesk_ticket_id=ticket_id,
                                        data=all_conversations  # Store as array
                                    )
                                    
                                    conv_stmt = conv_stmt.on_conflict_do_update(
                                        index_elements=['freshdesk_ticket_id'],
                                        set_={
                                            'data': conv_stmt.excluded.data
                                        },
                                        where=(FreshdeskConversation.data != conv_stmt.excluded.data)  # Only update if data differs
                                    )
                                    
                                    session.execute(conv_stmt)
                                
                            except Exception as e:
                                print(f"    ⚠️  Failed to fetch conversations for ticket {ticket_id}: {e}")
                                # Continue - ticket is already saved
                            
                        except Exception as e:
                            print(f"  ❌ Error syncing ticket {ticket.get('id')}: {e}")
                            total_errors += 1
                    
                    # Commit batch
                    session.commit()
                    
                    # Get timestamp range for this batch
                    if tickets:
                        # Since tickets are ordered by updated_at desc, first is newest, last is oldest
                        newest_updated = tickets[0].get('updated_at', 'unknown')
                        oldest_updated = tickets[-1].get('updated_at', 'unknown')
                        print(f"  ✅ Synced {len(tickets)} tickets from page {page} (Total so far: {total_synced})")
                        print(f"     Updated range: {newest_updated} → {oldest_updated}")
                    
                    # Check for more pages
                    has_more = next_url is not None
                    
                    if has_more:
                        if max_pages and page >= max_pages:
                            print(f"  → Reached max pages limit ({max_pages}), stopping.")
                            break
                        print(f"  → More pages available, continuing to page {page + 1}...")
                    else:
                        print(f"  → No more pages, stopping.")
                    page += 1
            
            # Update sync metadata on success
            self.update_sync_metadata(
                "freshdesk_tickets", 
                "success",
                last_successful_id=last_ticket_id
            )
            
            print(f"\n✅ Ticket sync completed:")
            print(f"   Total synced: {total_synced}")
            print(f"   Errors: {total_errors}")
            
            return {
                "status": "success",
                "total_synced": total_synced,
                "total_errors": total_errors,
                "last_ticket_id": last_ticket_id
            }
            
        except Exception as e:
            # Update sync metadata on failure
            self.update_sync_metadata(
                "freshdesk_tickets",
                "failed",
                error_message=str(e)
            )
            
            print(f"\n❌ Ticket sync failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "total_synced": total_synced,
                "total_errors": total_errors
            }
    
    def sync_satisfaction_ratings(self, since: Optional[datetime] = None, max_pages: Optional[int] = None) -> Dict[str, Any]:
        """Sync ALL satisfaction ratings to separate ratings table.
        
        Ratings are stored in etl_freshdesk_ratings table with foreign key to tickets.
        Only syncs ratings for tickets that exist in the database.
        
        Args:
            since: DEPRECATED - kept for compatibility but should always be None
            max_pages: Maximum number of pages to fetch (for testing)
        """
        print(f"⭐ Starting satisfaction ratings sync for merchant {self.merchant_id}")
        print("   📊 Fetching ALL satisfaction ratings from Freshdesk")
        print("   💾 Storing ratings in etl_freshdesk_ratings table")
        
        # Mark sync as in progress
        self.update_sync_metadata("freshdesk_satisfaction_ratings", "in_progress")
        
        # Always fetch ALL ratings
        created_since = None  # Don't limit by date
        
        total_synced = 0
        total_errors = 0
        tickets_updated = 0
        
        try:
            with get_db_session() as session:
                page = 1
                has_more = True
                
                while has_more:
                    print(f"  Fetching page {page}...")
                    
                    # Get ratings from API
                    ratings, next_url = self.api.get_satisfaction_ratings(
                        created_since=created_since,
                        page=page
                    )
                    
                    if not ratings:
                        break
                    
                    # Process each rating
                    for rating in ratings:
                        try:
                            ticket_id = str(rating.get('ticket_id'))
                            
                            # Check if ticket exists
                            result = session.execute(
                                select(FreshdeskTicket).where(
                                    FreshdeskTicket.merchant_id == self.merchant_id,
                                    FreshdeskTicket.freshdesk_ticket_id == ticket_id
                                )
                            )
                            
                            ticket_record = result.scalar_one_or_none()
                            
                            if ticket_record:
                                # Store rating in separate table
                                rating_stmt = insert(FreshdeskRating).values(
                                    freshdesk_ticket_id=ticket_id,
                                    data=rating  # Store the rating data
                                )
                                
                                rating_stmt = rating_stmt.on_conflict_do_update(
                                    index_elements=['freshdesk_ticket_id'],
                                    set_={
                                        'data': rating_stmt.excluded.data
                                    },
                                    where=(FreshdeskRating.data != rating_stmt.excluded.data)  # Only update if data differs
                                )
                                
                                session.execute(rating_stmt)
                                tickets_updated += 1
                            else:
                                print(f"    ⚠️  Ticket {ticket_id} not found in database")
                            
                            total_synced += 1
                            
                        except Exception as e:
                            print(f"  ❌ Error syncing rating for ticket {rating.get('ticket_id')}: {e}")
                            total_errors += 1
                    
                    # Commit batch
                    session.commit()
                    
                    # Get timestamp range for this batch
                    if ratings:
                        # Since ratings are ordered by created_at desc, first is newest, last is oldest
                        newest_created = ratings[0].get('created_at', 'unknown')
                        oldest_created = ratings[-1].get('created_at', 'unknown')
                        print(f"  ✅ Synced {len(ratings)} ratings from page {page} (Tickets updated: {tickets_updated})")
                        print(f"     Created range: {newest_created} → {oldest_created}")
                    
                    # Check for more pages
                    has_more = next_url is not None
                    
                    if has_more:
                        if max_pages and page >= max_pages:
                            print(f"  → Reached max pages limit ({max_pages}), stopping.")
                            break
                        print(f"  → More pages available, continuing to page {page + 1}...")
                    else:
                        print(f"  → No more pages, stopping.")
                    page += 1
            
            # Update sync metadata on success
            self.update_sync_metadata(
                "freshdesk_satisfaction_ratings", 
                "success"
            )
            
            print(f"\n✅ Satisfaction ratings sync completed:")
            print(f"   Total ratings synced: {total_synced}")
            print(f"   Tickets updated: {tickets_updated}")
            print(f"   Errors: {total_errors}")
            
            return {
                "status": "success",
                "total_synced": total_synced,
                "tickets_updated": tickets_updated,
                "total_errors": total_errors
            }
            
        except Exception as e:
            # Update sync metadata on failure
            self.update_sync_metadata(
                "freshdesk_satisfaction_ratings",
                "failed",
                error_message=str(e)
            )
            
            print(f"\n❌ Satisfaction ratings sync failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "total_synced": total_synced,
                "tickets_updated": tickets_updated,
                "total_errors": total_errors
            }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status for all Freshdesk resources."""
        with get_db_session() as session:
            statuses = session.query(SyncMetadata).filter_by(
                merchant_id=self.merchant_id
            ).filter(
                SyncMetadata.resource_type.in_(['freshdesk_tickets', 'freshdesk_contacts', 'freshdesk_satisfaction_ratings'])
            ).all()
            
            result = {}
            for status in statuses:
                result[status.resource_type] = {
                    'status': status.sync_status,
                    'last_sync': status.last_sync_at.isoformat() if status.last_sync_at else None,
                    'last_id': status.last_successful_id,
                    'error': status.error_message
                }
            
            return result