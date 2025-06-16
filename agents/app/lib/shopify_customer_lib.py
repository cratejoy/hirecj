"""Shopify customer lookup and order history library.

This module provides customer search functionality using GraphQL with intelligent fallbacks:
- Direct email lookup
- Fuzzy search by name/phone if email fails
- Order history retrieval for identified customers
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.utils.shopify_util import ShopifyGraphQL
from shared.env_loader import get_env

logger = logging.getLogger(__name__)


def find_shopify_customer_by_email(email: str) -> Dict[str, Any]:
    """
    Find a Shopify customer by email address with fuzzy fallback.
    
    Uses GraphQL for efficient customer search with the following strategy:
    1. Exact email match (case-insensitive)
    2. If no exact match, try partial email search
    3. Return formatted customer data or not found response
    
    Args:
        email: Customer email address to search for
        
    Returns:
        Dict with structure:
        {
            "found": True/False,
            "customer": {...} or None,
            "message": "Status message",
            "search_method": "exact_email" or "partial_email"
        }
    """
    logger.info(f"Searching for customer by email: {email}")
    
    try:
        # ShopifyGraphQL will get credentials from environment
        shop_domain = get_env("SHOPIFY_SHOP_DOMAIN")
        access_token = get_env("SHOPIFY_API_TOKEN")
        client = ShopifyGraphQL(shop_domain, access_token)
        
        # First try exact email match
        exact_query = """
        query CustomerByEmail($query: String!) {
            customers(first: 1, query: $query) {
                edges {
                    node {
                        id
                        email
                        firstName
                        lastName
                        createdAt
                        updatedAt
                        numberOfOrders
                        amountSpent {
                            amount
                            currencyCode
                        }
                        tags
                        verifiedEmail
                        emailMarketingConsent {
                            marketingState
                        }
                        phone
                        note
                        addresses(first: 1) {
                            address1
                            city
                            province
                            country
                            zip
                        }
                        lastOrder {
                            id
                            name
                            createdAt
                        }
                    }
                }
            }
        }
        """
        
        # Search for exact email match
        variables = {"query": f"email:{email}"}
        result = client.execute(exact_query, variables)
        
        customers = result.get("customers", {}).get("edges", [])
        if customers:
            customer_data = customers[0]["node"]
            return _format_customer_response(customer_data, "exact_email")
        
        # If no exact match, try partial email search
        logger.info(f"No exact email match, trying partial search for: {email}")
        
        # Extract username part for fuzzy search
        username = email.split('@')[0] if '@' in email else email
        
        # Try partial match on email
        partial_variables = {"query": f"email:{username}*"}
        result = client.execute(exact_query, partial_variables)
        
        customers = result.get("customers", {}).get("edges", [])
        if customers:
            # Find best match by checking if the domain matches
            domain = email.split('@')[1] if '@' in email else ""
            best_match = None
            
            for customer_edge in customers:
                customer = customer_edge["node"]
                customer_email = customer.get("email", "").lower()
                
                # Exact match found in partial results
                if customer_email == email.lower():
                    return _format_customer_response(customer, "partial_email")
                
                # If domain matches, consider it a good candidate
                if domain and domain in customer_email:
                    best_match = customer
            
            if best_match:
                return _format_customer_response(best_match, "partial_email")
        
        # No matches found
        return {
            "found": False,
            "customer": None,
            "message": f"No customer found with email: {email}",
            "search_method": None
        }
        
    except Exception as e:
        logger.error(f"Error searching for customer: {str(e)}")
        return {
            "found": False,
            "customer": None,
            "message": f"Error searching for customer: {str(e)}",
            "search_method": None
        }


def search_customers_fuzzy(search_term: str, search_fields: List[str] = None) -> Dict[str, Any]:
    """
    Perform fuzzy customer search across multiple fields.
    
    Args:
        search_term: Term to search for
        search_fields: Fields to search in (default: ["email", "first_name", "last_name", "phone"])
        
    Returns:
        Dict with found customers and search metadata
    """
    logger.info(f"Fuzzy search for: {search_term} in fields: {search_fields}")
    
    if search_fields is None:
        search_fields = ["email", "first_name", "last_name", "phone"]
    
    try:
        shop_domain = get_env("SHOPIFY_SHOP_DOMAIN")
        access_token = get_env("SHOPIFY_API_TOKEN")
        client = ShopifyGraphQL(shop_domain, access_token)
        
        query = """
        query FuzzyCustomerSearch($query: String!) {
            customers(first: 10, query: $query) {
                edges {
                    node {
                        id
                        email
                        firstName
                        lastName
                        phone
                        numberOfOrders
                        amountSpent {
                            amount
                            currencyCode
                        }
                        createdAt
                        tags
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
        """
        
        all_customers = []
        search_queries = []
        
        # Build search queries for each field
        for field in search_fields:
            if field == "email":
                search_queries.append(f"email:{search_term}*")
            elif field == "first_name":
                search_queries.append(f"first_name:{search_term}*")
            elif field == "last_name":
                search_queries.append(f"last_name:{search_term}*")
            elif field == "phone":
                # Remove common phone formatting
                clean_phone = search_term.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                search_queries.append(f"phone:{clean_phone}*")
        
        # Also try general search
        search_queries.append(search_term)
        
        # Execute searches and collect unique results
        seen_ids = set()
        
        for search_query in search_queries:
            try:
                variables = {"query": search_query}
                result = client.execute(query, variables)
                
                customers = result.get("customers", {}).get("edges", [])
                for customer_edge in customers:
                    customer = customer_edge["node"]
                    customer_id = customer["id"]
                    
                    if customer_id not in seen_ids:
                        seen_ids.add(customer_id)
                        all_customers.append(_format_customer_summary(customer))
                        
            except Exception as e:
                logger.warning(f"Search query '{search_query}' failed: {str(e)}")
                continue
        
        if all_customers:
            return {
                "found": True,
                "customers": all_customers,
                "message": f"Found {len(all_customers)} customer(s) matching '{search_term}'",
                "total_count": len(all_customers)
            }
        else:
            return {
                "found": False,
                "customers": [],
                "message": f"No customers found matching '{search_term}'",
                "total_count": 0
            }
            
    except Exception as e:
        logger.error(f"Error in fuzzy customer search: {str(e)}")
        return {
            "found": False,
            "customers": [],
            "message": f"Error searching customers: {str(e)}",
            "total_count": 0
        }


def get_customer_order_history(customer_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    Get order history for a specific customer using GraphQL.
    
    Args:
        customer_id: Shopify customer ID (can be numeric or GID)
        limit: Maximum number of orders to return (default 10, max 50)
        
    Returns:
        Dict with order history and summary
    """
    logger.info(f"Fetching order history for customer {customer_id}")
    
    # Ensure limit is reasonable
    limit = min(limit, 50)
    
    try:
        shop_domain = get_env("SHOPIFY_SHOP_DOMAIN")
        access_token = get_env("SHOPIFY_API_TOKEN")
        client = ShopifyGraphQL(shop_domain, access_token)
        
        # Convert numeric ID to GID if needed
        if not customer_id.startswith("gid://"):
            customer_gid = f"gid://shopify/Customer/{customer_id}"
        else:
            customer_gid = customer_id
        
        query = """
        query CustomerOrderHistory($customerId: ID!, $limit: Int!) {
            customer(id: $customerId) {
                id
                email
                firstName
                lastName
                numberOfOrders
                orders(first: $limit, sortKey: CREATED_AT, reverse: true) {
                    edges {
                        node {
                            id
                            name
                            createdAt
                            updatedAt
                            displayFinancialStatus
                            displayFulfillmentStatus
                            totalPriceSet {
                                shopMoney {
                                    amount
                                    currencyCode
                                }
                            }
                            subtotalPriceSet {
                                shopMoney {
                                    amount
                                }
                            }
                            totalShippingPriceSet {
                                shopMoney {
                                    amount
                                }
                            }
                            totalTaxSet {
                                shopMoney {
                                    amount
                                }
                            }
                            shippingAddress {
                                address1
                                address2
                                city
                                province
                                provinceCode
                                country
                                countryCode
                                zip
                            }
                            lineItems(first: 10) {
                                edges {
                                    node {
                                        title
                                        quantity
                                        variant {
                                            price
                                        }
                                        originalTotalSet {
                                            shopMoney {
                                                amount
                                            }
                                        }
                                    }
                                }
                            }
                            note
                            tags
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            "customerId": customer_gid,
            "limit": limit
        }
        
        result = client.execute(query, variables)
        
        customer = result.get("customer")
        if not customer:
            return {
                "customer_id": customer_id,
                "orders": [],
                "total_orders": 0,
                "orders_returned": 0,
                "message": f"Customer not found: {customer_id}"
            }
        
        # Format orders
        orders = []
        order_edges = customer.get("orders", {}).get("edges", [])
        
        for order_edge in order_edges:
            order = order_edge["node"]
            orders.append(_format_order_summary(order))
        
        return {
            "customer_id": customer_id,
            "customer_email": customer.get("email"),
            "customer_name": f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
            "orders": orders,
            "total_orders": customer.get("numberOfOrders", 0),
            "orders_returned": len(orders),
            "message": f"Retrieved {len(orders)} orders for customer"
        }
        
    except Exception as e:
        logger.error(f"Error fetching customer order history: {str(e)}")
        return {
            "customer_id": customer_id,
            "orders": [],
            "total_orders": 0,
            "orders_returned": 0,
            "message": f"Error fetching orders: {str(e)}"
        }


def _format_customer_response(customer_data: Dict[str, Any], search_method: str) -> Dict[str, Any]:
    """Format customer data into standard response structure."""
    # Extract numeric ID from GID
    customer_id = customer_data["id"]
    if customer_id.startswith("gid://"):
        customer_id = int(customer_id.split("/")[-1])
    
    # Format addresses
    addresses = customer_data.get("addresses", [])
    primary_address = addresses[0] if addresses else {}
    
    # Format monetary values
    amount_spent = customer_data.get("amountSpent", {})
    spent_amount = amount_spent.get("amount", "0")
    currency = amount_spent.get("currencyCode", "USD")
    
    # Format last order
    last_order = customer_data.get("lastOrder", {})
    last_order_id = None
    last_order_name = None
    
    if last_order:
        last_order_id_gid = last_order.get("id", "")
        if last_order_id_gid.startswith("gid://"):
            last_order_id = int(last_order_id_gid.split("/")[-1])
        last_order_name = last_order.get("name")
    
    # Handle marketing consent
    email_marketing = customer_data.get("emailMarketingConsent", {})
    accepts_marketing = email_marketing.get("marketingState", "NOT_SUBSCRIBED") == "SUBSCRIBED"
    
    formatted = {
        "id": customer_id,
        "email": customer_data.get("email"),
        "first_name": customer_data.get("firstName"),
        "last_name": customer_data.get("lastName"),
        "created_at": customer_data.get("createdAt"),
        "orders_count": customer_data.get("numberOfOrders", 0),
        "total_spent": spent_amount,
        "currency": currency,
        "tags": customer_data.get("tags", []),
        "verified_email": customer_data.get("verifiedEmail", False),
        "accepts_marketing": accepts_marketing,
        "phone": customer_data.get("phone"),
        "last_order_id": last_order_id,
        "last_order_name": last_order_name,
        "note": customer_data.get("note")
    }
    
    # Add address if available
    if primary_address:
        formatted["primary_address"] = {
            "address1": primary_address.get("address1"),
            "city": primary_address.get("city"),
            "province": primary_address.get("province"),
            "country": primary_address.get("country"),
            "zip": primary_address.get("zip")
        }
    
    return {
        "found": True,
        "customer": formatted,
        "message": "Customer found",
        "search_method": search_method
    }


def _format_customer_summary(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format customer data for summary listing."""
    customer_id = customer_data["id"]
    if customer_id.startswith("gid://"):
        customer_id = int(customer_id.split("/")[-1])
    
    amount_spent = customer_data.get("amountSpent", {})
    spent_amount = amount_spent.get("amount", "0")
    currency = amount_spent.get("currencyCode", "USD")
    
    return {
        "id": customer_id,
        "email": customer_data.get("email"),
        "first_name": customer_data.get("firstName"),
        "last_name": customer_data.get("lastName"),
        "phone": customer_data.get("phone"),
        "orders_count": customer_data.get("numberOfOrders", 0),
        "total_spent": f"{spent_amount} {currency}",
        "created_at": customer_data.get("createdAt"),
        "tags": customer_data.get("tags", [])
    }


def _format_order_summary(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format order data for history listing."""
    order_id = order_data["id"]
    if order_id.startswith("gid://"):
        order_id = int(order_id.split("/")[-1])
    
    total_price = order_data.get("totalPriceSet", {}).get("shopMoney", {})
    currency = total_price.get("currencyCode", "USD")
    
    # Format line items
    line_items = []
    for item_edge in order_data.get("lineItems", {}).get("edges", []):
        item = item_edge["node"]
        line_items.append({
            "title": item.get("title"),
            "quantity": item.get("quantity"),
            "price": item.get("variant", {}).get("price")
        })
    
    # Format address
    shipping_address = order_data.get("shippingAddress", {})
    if shipping_address:
        formatted_address = {
            "address1": shipping_address.get("address1"),
            "address2": shipping_address.get("address2"),
            "city": shipping_address.get("city"),
            "province": shipping_address.get("province"),
            "country": shipping_address.get("country"),
            "zip": shipping_address.get("zip")
        }
    else:
        formatted_address = None
    
    return {
        "id": order_id,
        "name": order_data.get("name"),
        "created_at": order_data.get("createdAt"),
        "financial_status": order_data.get("displayFinancialStatus"),
        "fulfillment_status": order_data.get("displayFulfillmentStatus"),
        "total_price": total_price.get("amount", "0"),
        "currency": currency,
        "line_items_count": len(line_items),
        "line_items": line_items[:3],  # First 3 items only for summary
        "shipping_address": formatted_address,
        "note": order_data.get("note"),
        "tags": order_data.get("tags", [])
    }