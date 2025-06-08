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
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return None
        try:
            # Handle both formats: with 'Z' suffix and with '+00:00'
            if timestamp_str.endswith('Z'):
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, AttributeError):
            return None
    
    def _convert_rating_scale(self, rating_value: Optional[int]) -> Optional[int]:
        """Pass through rating values without conversion.
        
        Freshdesk Rating Scale (stored as-is):
        103 = Extremely Happy
        102 = Very Happy
        101 = Happy
        100 = Neutral
        -101 = Unhappy
        -102 = Very Unhappy
        -103 = Extremely Unhappy
        """
        return rating_value
    
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
    
    def sync_ticket_data(self, since: Optional[datetime] = None, max_pages: Optional[int] = None, force_reparse: bool = False) -> Dict[str, Any]:
        """Sync ONLY Freshdesk ticket data (without conversations).
        
        This method fetches and stores core ticket data only. Conversations
        should be synced separately using sync_conversation_data().
        
        Args:
            since: Sync tickets updated since this datetime
            max_pages: Maximum number of pages to fetch (for testing)
            force_reparse: Force re-parsing of all fields
            
        Returns:
            Dict containing:
                - status: "success" or "failed"
                - total_synced: Number of tickets synced
                - total_errors: Number of errors
                - last_ticket_id: Last ticket ID processed
                - updated_ticket_ids: List of ticket IDs that were updated
        """
        print(f"🎫 Starting Freshdesk ticket data sync for merchant {self.merchant_id}")
        print("   📝 Syncing ticket data only (no conversations)")
        
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
        updated_ticket_ids = []  # Track which tickets were updated
        
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
                        include="requester,stats"  # Include contact data and stats
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
                                # Store stats data for resolution times
                                'stats': ticket.get('stats'),  # Contains resolved_at, closed_at, first_responded_at, etc.
                                # Store complete ticket data
                                '_raw_data': ticket
                            }
                            
                            # Show progress for large batches
                            if len(tickets) > 20 and idx % 10 == 0:
                                print(f"    Processing ticket {idx}/{len(tickets)}...")
                            
                            # Parse fields for quick access
                            parsed_created_at = self._parse_timestamp(ticket.get('created_at'))
                            parsed_updated_at = self._parse_timestamp(ticket.get('updated_at'))
                            parsed_email = None
                            if ticket.get('requester') and isinstance(ticket['requester'], dict):
                                parsed_email = ticket['requester'].get('email')
                            parsed_status = ticket.get('status')  # Status code: 2=Open, 3=Pending, 4=Resolved, 5=Closed
                            
                            # Upsert the ticket (without conversations)
                            stmt = insert(FreshdeskTicket).values(
                                freshdesk_ticket_id=ticket_id,
                                merchant_id=self.merchant_id,
                                data=ticket_data,
                                parsed_created_at=parsed_created_at,
                                parsed_updated_at=parsed_updated_at,
                                parsed_email=parsed_email,
                                parsed_status=parsed_status
                            )
                            
                            if not force_reparse:
                                stmt = stmt.on_conflict_do_update(
                                    index_elements=['merchant_id', 'freshdesk_ticket_id'],
                                    set_={
                                        'data': stmt.excluded.data,
                                        'parsed_created_at': stmt.excluded.parsed_created_at,
                                        'parsed_updated_at': stmt.excluded.parsed_updated_at,
                                        'parsed_email': stmt.excluded.parsed_email,
                                        'parsed_status': stmt.excluded.parsed_status
                                    },
                                    where=(FreshdeskTicket.data != stmt.excluded.data)  # Only update if data differs
                                )
                            else:
                                stmt = stmt.on_conflict_do_update(
                                    index_elements=['merchant_id', 'freshdesk_ticket_id'],
                                    set_={
                                        'data': stmt.excluded.data,
                                        'parsed_created_at': stmt.excluded.parsed_created_at,
                                        'parsed_updated_at': stmt.excluded.parsed_updated_at,
                                        'parsed_email': stmt.excluded.parsed_email,
                                        'parsed_status': stmt.excluded.parsed_status
                                    }
                                )
                            
                            result = session.execute(stmt)
                            # Track if this ticket was actually updated
                            if result.rowcount > 0:
                                updated_ticket_ids.append(ticket_id)
                            
                            total_synced += 1
                            last_ticket_id = ticket_id
                            
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
            
            print(f"\n✅ Ticket data sync completed:")
            print(f"   Total synced: {total_synced}")
            print(f"   Tickets updated: {len(updated_ticket_ids)}")
            print(f"   Errors: {total_errors}")
            
            return {
                "status": "success",
                "total_synced": total_synced,
                "total_errors": total_errors,
                "last_ticket_id": last_ticket_id,
                "updated_ticket_ids": updated_ticket_ids
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
                "total_errors": total_errors,
                "updated_ticket_ids": updated_ticket_ids
            }
    
    def sync_conversations_for_tickets(self, ticket_ids: List[str], force_reparse: bool = False) -> Dict[str, Any]:
        """Sync conversations for specific tickets.
        
        This method fetches and stores conversations for the provided ticket IDs.
        Useful for updating conversations after ticket data has been synced.
        
        Args:
            ticket_ids: List of Freshdesk ticket IDs to sync conversations for
            force_reparse: Force re-parsing of all fields
            
        Returns:
            Dict containing:
                - status: "success" or "failed"
                - total_synced: Number of conversations synced
                - total_errors: Number of errors
        """
        if not ticket_ids:
            return {
                "status": "success",
                "total_synced": 0,
                "total_errors": 0
            }
            
        print(f"💬 Starting conversation sync for {len(ticket_ids)} tickets")
        
        # Mark sync as in progress
        self.update_sync_metadata("freshdesk_conversations", "in_progress")
        
        total_synced = 0
        total_errors = 0
        
        try:
            with get_db_session() as session:
                # Process tickets in batches to avoid too many commits
                batch_size = 50
                for i in range(0, len(ticket_ids), batch_size):
                    batch = ticket_ids[i:i + batch_size]
                    print(f"  Processing batch {i//batch_size + 1} ({len(batch)} tickets)...")
                    
                    for ticket_id in batch:
                        try:
                            # Fetch all conversations for this ticket
                            all_conversations = []
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
                            
                            # Store conversations if we got any
                            if all_conversations:
                                # Parse first and last message timestamps
                                parsed_created_at = None
                                parsed_updated_at = None
                                
                                # First message created_at
                                if all_conversations[0] and isinstance(all_conversations[0], dict):
                                    parsed_created_at = self._parse_timestamp(all_conversations[0].get('created_at'))
                                # Last message created_at
                                if all_conversations[-1] and isinstance(all_conversations[-1], dict):
                                    parsed_updated_at = self._parse_timestamp(all_conversations[-1].get('created_at'))
                                
                                conv_stmt = insert(FreshdeskConversation).values(
                                    freshdesk_ticket_id=ticket_id,
                                    data=all_conversations,  # Store as array
                                    parsed_created_at=parsed_created_at,
                                    parsed_updated_at=parsed_updated_at
                                )
                                
                                if not force_reparse:
                                    conv_stmt = conv_stmt.on_conflict_do_update(
                                        index_elements=['freshdesk_ticket_id'],
                                        set_={
                                            'data': conv_stmt.excluded.data,
                                            'parsed_created_at': conv_stmt.excluded.parsed_created_at,
                                            'parsed_updated_at': conv_stmt.excluded.parsed_updated_at
                                        },
                                        where=(FreshdeskConversation.data != conv_stmt.excluded.data)  # Only update if data differs
                                    )
                                else:
                                    conv_stmt = conv_stmt.on_conflict_do_update(
                                        index_elements=['freshdesk_ticket_id'],
                                        set_={
                                            'data': conv_stmt.excluded.data,
                                            'parsed_created_at': conv_stmt.excluded.parsed_created_at,
                                            'parsed_updated_at': conv_stmt.excluded.parsed_updated_at
                                        }
                                    )
                                
                                session.execute(conv_stmt)
                                total_synced += 1
                            else:
                                print(f"    ⚠️  No conversations found for ticket {ticket_id}")
                                
                        except Exception as e:
                            print(f"    ❌ Error syncing conversations for ticket {ticket_id}: {e}")
                            total_errors += 1
                    
                    # Commit batch
                    session.commit()
                    
            # Update sync metadata on success
            self.update_sync_metadata("freshdesk_conversations", "success")
            
            print(f"\n✅ Conversation sync completed:")
            print(f"   Total synced: {total_synced}")
            print(f"   Errors: {total_errors}")
            
            return {
                "status": "success",
                "total_synced": total_synced,
                "total_errors": total_errors
            }
            
        except Exception as e:
            # Update sync metadata on failure
            self.update_sync_metadata(
                "freshdesk_conversations",
                "failed",
                error_message=str(e)
            )
            
            print(f"\n❌ Conversation sync failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "total_synced": total_synced,
                "total_errors": total_errors
            }
    
    def sync_tickets(self, since: Optional[datetime] = None, max_pages: Optional[int] = None, force_reparse: bool = False) -> Dict[str, Any]:
        """Sync Freshdesk tickets with conversations using two-phase approach.
        
        Phase 1: Sync all ticket data that has been updated since last sync
        Phase 2: Sync conversations for tickets that were updated
        
        This method combines sync_ticket_data and sync_conversations_for_tickets
        for backward compatibility.
        
        Args:
            since: Sync tickets updated since this datetime
            max_pages: Maximum number of pages to fetch (for testing)
            force_reparse: Force re-parsing of all fields
            
        Returns:
            Combined results from both phases
        """
        print(f"🎫 Starting two-phase Freshdesk sync for merchant {self.merchant_id}")
        print("=" * 60)
        print("PHASE 1: SYNCING TICKET DATA")
        print("=" * 60)
        
        # Phase 1: Sync ticket data
        ticket_result = self.sync_ticket_data(since=since, max_pages=max_pages, force_reparse=force_reparse)
        
        if ticket_result['status'] != 'success':
            return ticket_result
        
        updated_ticket_ids = ticket_result.get('updated_ticket_ids', [])
        
        if not updated_ticket_ids:
            print("\n✅ No tickets were updated, skipping conversation sync")
            return ticket_result
        
        print("\n" + "=" * 60)
        print("PHASE 2: SYNCING CONVERSATIONS FOR UPDATED TICKETS")
        print("=" * 60)
        
        # Phase 2: Sync conversations for updated tickets
        conv_result = self.sync_conversations_for_tickets(
            ticket_ids=updated_ticket_ids,
            force_reparse=force_reparse
        )
        
        # Combine results
        return {
            "status": "success" if conv_result['status'] == 'success' else "partial",
            "total_synced": ticket_result['total_synced'],
            "total_errors": ticket_result['total_errors'] + conv_result.get('total_errors', 0),
            "tickets_updated": len(updated_ticket_ids),
            "conversations_synced": conv_result.get('total_synced', 0),
            "last_ticket_id": ticket_result.get('last_ticket_id')
        }
    
    def sync_satisfaction_ratings(self, since: Optional[datetime] = None, max_pages: Optional[int] = None, force_reparse: bool = False) -> Dict[str, Any]:
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
                                # Extract rating value (stored as-is, no conversion)
                                parsed_rating = None
                                if rating.get('ratings') and isinstance(rating['ratings'], dict):
                                    rating_value = rating['ratings'].get('default_question')
                                    parsed_rating = self._convert_rating_scale(rating_value)  # Pass-through, no conversion
                                
                                # Store rating in separate table
                                rating_stmt = insert(FreshdeskRating).values(
                                    freshdesk_ticket_id=ticket_id,
                                    data=rating,  # Store the rating data
                                    parsed_rating=parsed_rating
                                )
                                
                                if not force_reparse:
                                    rating_stmt = rating_stmt.on_conflict_do_update(
                                        index_elements=['freshdesk_ticket_id'],
                                        set_={
                                            'data': rating_stmt.excluded.data,
                                            'parsed_rating': rating_stmt.excluded.parsed_rating
                                        },
                                        where=(FreshdeskRating.data != rating_stmt.excluded.data)  # Only update if data differs
                                    )
                                else:
                                    rating_stmt = rating_stmt.on_conflict_do_update(
                                        index_elements=['freshdesk_ticket_id'],
                                        set_={
                                            'data': rating_stmt.excluded.data,
                                            'parsed_rating': rating_stmt.excluded.parsed_rating
                                        }
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
                SyncMetadata.resource_type.in_(['freshdesk_tickets', 'freshdesk_conversations', 'freshdesk_contacts', 'freshdesk_satisfaction_ratings'])
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