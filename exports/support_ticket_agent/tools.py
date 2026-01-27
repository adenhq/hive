"""
Custom tools for the Support Ticket Agent.
Add your Python functions here and they will be auto-discovered by the framework.
"""

def lookup_customer(customer_id: str) -> dict:
    """
    Look up customer information by ID.
    
    Args:
        customer_id: The unique ID of the customer.
        
    Returns:
        dict: Customer metadata including name and status.
    """
    # This is a dummy implementation for verification.
    # In a real agent, this would call a database or CRM API.
    customers = {
        "CUST-123": {"name": "Alice Smith", "account_status": "Premium"},
        "CUST-456": {"name": "Bob Jones", "account_status": "Standard"},
    }
    return customers.get(customer_id, {"name": "Unknown", "account_status": "Guest"})
