"""Mock backend functions the specialist agents can call as tools.

These are plain Python functions with type-hinted signatures. Agent Framework
inspects the signature + docstring to build the tool schema it hands to the
model, so no manual JSON schema is needed here.
"""

_CUSTOMERS = {
    "cust_1": {"name": "Alex Chen", "balance": 129.99, "last_charge": 64.99},
    "cust_2": {"name": "Priya Nair", "balance": 0.00, "last_charge": 19.99},
}

_SERVICES = {
    "email": "operational",
    "storage": "degraded",
    "vpn": "outage",
}


def check_balance(customer_id: str) -> str:
    """Look up a customer's current account balance.

    Args:
        customer_id: The customer's account id, e.g. "cust_1".
    """
    customer = _CUSTOMERS.get(customer_id)
    if not customer:
        return f"No customer found with id '{customer_id}'."
    return f"{customer['name']}'s current balance is ${customer['balance']:.2f}."


def issue_refund(customer_id: str, amount: float, partial: bool = False) -> str:
    """Issue a refund to a customer.

    Args:
        customer_id: The customer's account id, e.g. "cust_1".
        amount: The dollar amount to refund.
        partial: Whether this is a partial refund rather than a full refund.
    """
    customer = _CUSTOMERS.get(customer_id)
    if not customer:
        return f"No customer found with id '{customer_id}'."
    kind = "partial" if partial else "full"
    return f"Issued a {kind} refund of ${amount:.2f} to {customer['name']}."


def restart_service(service_name: str) -> str:
    """Restart a named backend service.

    Args:
        service_name: The service to restart, e.g. "email", "storage", "vpn".
    """
    if service_name not in _SERVICES:
        return f"Unknown service '{service_name}'."
    _SERVICES[service_name] = "operational"
    return f"Service '{service_name}' has been restarted and is now operational."


def check_system_status(service_name: str) -> str:
    """Check the current operational status of a named backend service.

    Args:
        service_name: The service to check, e.g. "email", "storage", "vpn".
    """
    status = _SERVICES.get(service_name)
    if not status:
        return f"Unknown service '{service_name}'."
    return f"Service '{service_name}' is currently: {status}."
