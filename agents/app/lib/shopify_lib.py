"""Shopify ETL library for syncing data to database."""

import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select

from app.utils.shopify_util import ShopifyAPI
from app.utils.supabase_util import get_db_session
from app.dbmodels.base import Merchant, SyncMetadata
from app.dbmodels.etl_tables import ShopifyCustomer


class ShopifyETL:
    """Orchestrates Shopify data sync to database."""
    
    def __init__(self, merchant_id: int):
        self.merchant_id = merchant_id
        self.api = ShopifyAPI()
        self._customer_cache = {}  # Cache customer IDs
    
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
    
    def _ensure_customer_exists(self, session, customer_data: Dict[str, Any]) -> Optional[str]:
        """Ensure a customer exists in the database and return its UUID."""
        if not customer_data:
            return None
        
        customer_id = str(customer_data.get('id'))
        
        # Check cache first
        if customer_id in self._customer_cache:
            return self._customer_cache[customer_id]
        
        # Prepare customer data with all Shopify fields
        db_customer_data = {
            'shopify_customer_id': customer_id,
            'email': customer_data.get('email'),
            'first_name': customer_data.get('first_name'),
            'last_name': customer_data.get('last_name'),
            'phone': customer_data.get('phone'),
            'orders_count': customer_data.get('orders_count', 0),
            'total_spent': float(customer_data.get('total_spent', 0)),
            'currency': customer_data.get('currency'),
            'accepts_marketing': customer_data.get('accepts_marketing'),
            'tags': customer_data.get('tags', '').split(',') if customer_data.get('tags') else [],
            'created_at': customer_data.get('created_at'),
            'updated_at': customer_data.get('updated_at'),
            'state': customer_data.get('state'),
            'verified_email': customer_data.get('verified_email'),
            'default_address': customer_data.get('default_address'),
            # Store complete customer data
            '_raw_data': customer_data
        }
        
        # Upsert the customer
        stmt = insert(ShopifyCustomer).values(
            shopify_customer_id=customer_id,
            merchant_id=self.merchant_id,
            data=db_customer_data
        )
        
        stmt = stmt.on_conflict_do_update(
            index_elements=['merchant_id', 'shopify_customer_id'],
            set_={
                'data': stmt.excluded.data
            }
        )
        
        session.execute(stmt)
        
        # Return the customer ID itself since we're using it as primary key
        return customer_id
    
    def sync_customers(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Sync Shopify customers to database."""
        print(f"👥 Starting Shopify customer sync for merchant {self.merchant_id}")
        
        # Mark sync as in progress
        self.update_sync_metadata("shopify_customers", "in_progress")
        
        # Use last sync timestamp if not provided
        if not since:
            since = self.get_last_sync_timestamp("shopify_customers")
        
        # Format timestamp for Shopify API
        updated_at_min = since.isoformat() if since else None
        
        total_synced = 0
        total_errors = 0
        last_customer_id = None
        
        try:
            with get_db_session() as session:
                page_info = None
                page_num = 1
                
                while True:
                    print(f"  Fetching page {page_num}...")
                    
                    # Get customers from API
                    customers, next_page_info = self.api.get_customers(
                        updated_at_min=updated_at_min if not page_info else None,  # Can't use with pagination
                        page_info=page_info
                    )
                    
                    if not customers:
                        break
                    
                    # Process each customer
                    for customer in customers:
                        try:
                            customer_id = str(customer.get('id'))
                            
                            # Ensure customer exists
                            self._ensure_customer_exists(session, customer)
                            
                            total_synced += 1
                            last_customer_id = customer_id
                            
                        except Exception as e:
                            print(f"  ❌ Error syncing customer {customer.get('id')}: {e}")
                            total_errors += 1
                    
                    # Commit batch
                    session.commit()
                    print(f"  ✅ Synced {len(customers)} customers from page {page_num}")
                    
                    # Check for more pages
                    if not next_page_info:
                        break
                    
                    page_info = next_page_info
                    page_num += 1
            
            # Update sync metadata on success
            self.update_sync_metadata(
                "shopify_customers",
                "success",
                last_successful_id=last_customer_id
            )
            
            print(f"\n✅ Customer sync completed:")
            print(f"   Total synced: {total_synced}")
            print(f"   Errors: {total_errors}")
            
            return {
                "status": "success",
                "total_synced": total_synced,
                "total_errors": total_errors,
                "last_customer_id": last_customer_id
            }
            
        except Exception as e:
            # Update sync metadata on failure
            self.update_sync_metadata(
                "shopify_customers",
                "failed",
                error_message=str(e)
            )
            
            print(f"\n❌ Customer sync failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "total_synced": total_synced,
                "total_errors": total_errors
            }
    
    def sync_orders(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """DEPRECATED: Orders should not be synced to the database."""
        print(f"⚠️  Shopify order sync is disabled")
        print(f"   Orders should not be stored in the Freshdesk tickets table")
        print(f"   This method is kept for backwards compatibility only")
        
        return {
            "status": "skipped",
            "message": "Shopify order sync is disabled - orders should not be stored as tickets"
        }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status for all Shopify resources."""
        with get_db_session() as session:
            statuses = session.query(SyncMetadata).filter_by(
                merchant_id=self.merchant_id
            ).filter(
                SyncMetadata.resource_type.in_(['shopify_customers'])
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
