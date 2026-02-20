# Stripe Tool

Interact with Stripe customers, payments, and invoices within the Aden agent framework.

## Installation

The Stripe tool uses `httpx` which is already included in the base dependencies. No additional installation required.

## Setup

You need a Stripe Secret Key to use this tool.

### Getting a Stripe Key

1. Go to [https://dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys)
2. Copy your **Secret key** (starts with `sk_`). You may need to create one if you haven't already.

**Important:** Use a test mode key (`sk_test_...`) for development and testing.

### Configuration

Set the key as an environment variable:

```bash
export STRIPE_SECRET_KEY=sk_test_your_key_here
```

Or configure via the credential store.

## Available Functions

### `stripe_list_customers`

List your Stripe customers.

**Parameters:**
- `limit` (int, optional): Maximum number of customers (1-100, default 10)

### `stripe_create_customer`

Create a new customer in your Stripe account.

**Parameters:**
- `email` (str): Customer's email address
- `name` (str, optional): Customer's full name

### `stripe_list_payments`

List recent Stripe payment intents.

**Parameters:**
- `limit` (int, optional): Maximum number of payments (1-100, default 10)

### `stripe_create_payment_link`

Create a public Stripe payment link for a specific price.

**Parameters:**
- `price_id` (str): ID of the Stripe Price object
- `quantity` (int, optional): Quantity of the item (default 1)

### `stripe_list_invoices`

List your Stripe invoices.

**Parameters:**
- `limit` (int, optional): Maximum number of invoices (1-100, default 10)
