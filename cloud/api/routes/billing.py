"""Billing and payment endpoints for hardware orders and subscriptions."""

import os
import uuid
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import stripe

from cloud.api.database import get_db, Organization, User, HardwareOrder
from cloud.api.auth.dependencies import get_current_user, get_current_org

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_6MONTH_PRICE_ID = os.getenv("STRIPE_6MONTH_PRICE_ID")  # One-time payment price
STRIPE_1MONTH_PRICE_ID = os.getenv("STRIPE_1MONTH_PRICE_ID")  # One-time payment price
STRIPE_MONTHLY_RECURRING_PRICE_ID = os.getenv("STRIPE_MONTHLY_RECURRING_PRICE_ID")  # $49.50/month recurring

router = APIRouter(tags=["Billing"])


# Request/Response Models
class CheckoutRequest(BaseModel):
    plan: str  # "6month" or "1month"

    class Config:
        json_schema_extra = {
            "example": {
                "plan": "6month"
            }
        }


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    portal_url: str


class ActivationRequest(BaseModel):
    activation_code: str

    class Config:
        json_schema_extra = {
            "example": {
                "activation_code": "VISANT-ABC123"
            }
        }


class ActivationResponse(BaseModel):
    success: bool
    message: str
    subscription_ends_at: Optional[str] = None
    plan_type: Optional[str] = None


def generate_order_number() -> str:
    """Generate unique order number like ORD-20241115-001."""
    today = datetime.utcnow().strftime("%Y%m%d")
    random_suffix = ''.join(secrets.choice(string.digits) for _ in range(3))
    return f"ORD-{today}-{random_suffix}"


def generate_activation_code() -> str:
    """Generate unique activation code like VISANT-ABC123."""
    chars = string.ascii_uppercase + string.digits
    code_part = ''.join(secrets.choice(chars) for _ in range(6))
    return f"VISANT-{code_part}"


@router.get("/checkout")
async def create_checkout_session(
    plan: str,
    db: Session = Depends(get_db)
):
    """
    Create Stripe Checkout session for hardware purchase.

    Query params:
    - plan: "6month" or "1month"

    Redirects to Stripe hosted checkout page.
    """
    # Validate plan
    if plan not in ["6month", "1month"]:
        raise HTTPException(status_code=400, detail="Invalid plan. Must be '6month' or '1month'")

    # Determine pricing
    if plan == "6month":
        amount = 29700  # $297.00
        price_id = STRIPE_6MONTH_PRICE_ID
        prepaid_months = 6
    else:  # 1month
        amount = 9950  # $99.50
        price_id = STRIPE_1MONTH_PRICE_ID
        prepaid_months = 1

    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=f"Stripe price ID not configured for {plan} plan"
        )

    # Generate activation code and order number
    activation_code = generate_activation_code()
    order_number = generate_order_number()

    # Ensure activation code is unique
    existing_order = db.query(HardwareOrder).filter(
        HardwareOrder.activation_code == activation_code
    ).first()
    while existing_order:
        activation_code = generate_activation_code()
        existing_order = db.query(HardwareOrder).filter(
            HardwareOrder.activation_code == activation_code
        ).first()

    try:
        # Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{os.getenv('APP_BASE_URL', 'https://app.visant.ai')}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('APP_BASE_URL', 'https://app.visant.ai')}/checkout/canceled",
            billing_address_collection="required",
            shipping_address_collection={
                "allowed_countries": ["US", "CA"],  # Expand as needed
            },
            customer_creation="always",  # Create Stripe customer for future billing
            payment_intent_data={
                "setup_future_usage": "off_session",  # Save payment method for later
            },
            metadata={
                "order_number": order_number,
                "activation_code": activation_code,
                "plan_type": plan,
                "prepaid_months": str(prepaid_months),
            }
        )

        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id
        )

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.post("/api/stripe-webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events.

    Events processed:
    - checkout.session.completed: Create hardware order, send activation code
    - invoice.payment_succeeded: Confirm recurring payment
    - invoice.payment_failed: Mark subscription as past_due
    - customer.subscription.deleted: Mark subscription as canceled
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_completed(session, db)

    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        await handle_payment_succeeded(invoice, db)

    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        await handle_payment_failed(invoice, db)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await handle_subscription_deleted(subscription, db)

    return {"status": "success"}


async def handle_checkout_completed(session: dict, db: Session):
    """Process completed checkout - create hardware order and send activation code."""
    # Extract metadata
    order_number = session["metadata"]["order_number"]
    activation_code = session["metadata"]["activation_code"]
    plan_type = session["metadata"]["plan_type"]
    prepaid_months = int(session["metadata"]["prepaid_months"])

    # Extract customer info
    customer_email = session["customer_details"]["email"]
    shipping = session["shipping_details"]
    shipping_address = {
        "name": shipping["name"],
        "line1": shipping["address"]["line1"],
        "line2": shipping["address"].get("line2"),
        "city": shipping["address"]["city"],
        "state": shipping["address"]["state"],
        "postal_code": shipping["address"]["postal_code"],
        "country": shipping["address"]["country"],
    }

    # Get amount paid
    amount_total = session["amount_total"] / 100  # Convert cents to dollars

    # Create hardware order
    order = HardwareOrder(
        order_number=order_number,
        plan_type=plan_type,
        total_paid=amount_total,
        prepaid_months=prepaid_months,
        customer_email=customer_email,
        shipping_address=shipping_address,
        stripe_payment_intent_id=session.get("payment_intent"),
        stripe_customer_id=session["customer"],
        stripe_checkout_session_id=session["id"],
        activation_code=activation_code,
        shipping_status="pending",
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    # TODO: Send confirmation email with activation code
    print(f"Order created: {order_number}, Activation code: {activation_code}, Email: {customer_email}")

    return order


async def handle_payment_succeeded(invoice: dict, db: Session):
    """Handle successful recurring payment."""
    customer_id = invoice["customer"]
    subscription_id = invoice["subscription"]

    # Find organization by Stripe customer ID
    org = db.query(Organization).filter(
        Organization.stripe_customer_id == customer_id
    ).first()

    if org:
        # Ensure subscription is active
        org.subscription_status = "active"
        if not org.stripe_subscription_id:
            org.stripe_subscription_id = subscription_id
        db.commit()

        print(f"Payment succeeded for org {org.id}, subscription {subscription_id}")


async def handle_payment_failed(invoice: dict, db: Session):
    """Handle failed recurring payment."""
    customer_id = invoice["customer"]

    # Find organization by Stripe customer ID
    org = db.query(Organization).filter(
        Organization.stripe_customer_id == customer_id
    ).first()

    if org:
        org.subscription_status = "past_due"
        db.commit()

        # TODO: Send email notification
        print(f"Payment failed for org {org.id}, status set to past_due")


async def handle_subscription_deleted(subscription: dict, db: Session):
    """Handle subscription cancellation."""
    customer_id = subscription["customer"]

    # Find organization by Stripe customer ID
    org = db.query(Organization).filter(
        Organization.stripe_customer_id == customer_id
    ).first()

    if org:
        org.subscription_status = "canceled"
        org.stripe_subscription_id = None
        db.commit()

        print(f"Subscription canceled for org {org.id}")


@router.post("/api/create-portal-session")
async def create_portal_session(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Create Stripe Customer Portal session for managing subscription.
    Requires authentication.
    """
    if not org.stripe_customer_id:
        raise HTTPException(
            status_code=404,
            detail="No Stripe customer found for this organization"
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=org.stripe_customer_id,
            return_url=f"{os.getenv('APP_BASE_URL', 'https://app.visant.ai')}/ui/billing",
        )

        return PortalSessionResponse(portal_url=session.url)

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.post("/api/activate-code")
async def activate_code(
    request: ActivationRequest,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Activate a hardware purchase code.

    This endpoint:
    1. Validates the activation code
    2. Links the code to the user's organization
    3. Sets subscription status to active
    4. Creates a Stripe subscription for future billing (after prepaid period)

    Requires authentication.
    """
    # Find the hardware order by activation code
    order = db.query(HardwareOrder).filter(
        HardwareOrder.activation_code == request.activation_code.strip().upper()
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Invalid activation code. Please check and try again."
        )

    # Check if code is already activated
    if order.code_activated_at is not None:
        raise HTTPException(
            status_code=400,
            detail=f"This activation code has already been used on {order.code_activated_at.strftime('%Y-%m-%d')}."
        )

    # Activate the code NOW
    activation_date = datetime.utcnow()
    order.code_activated_at = activation_date
    order.activated_by_user_id = user.id
    order.org_id = org.id
    order.subscription_starts_at = activation_date

    # Calculate when prepaid period ends
    if order.plan_type == "6month":
        order.subscription_ends_at = activation_date + timedelta(days=180)
        order.auto_renewal_starts_at = activation_date + timedelta(days=180)
    else:  # 1month
        order.subscription_ends_at = activation_date + timedelta(days=30)
        order.auto_renewal_starts_at = activation_date + timedelta(days=30)

    # Update organization subscription status
    org.subscription_status = "active"
    org.subscription_plan_id = order.plan_type
    org.allowed_devices += 1  # Grant one device slot

    # Link Stripe customer to organization if not already linked
    if not org.stripe_customer_id and order.stripe_customer_id:
        org.stripe_customer_id = order.stripe_customer_id

    # Create Stripe subscription that will start billing AFTER prepaid period
    try:
        if org.stripe_customer_id and STRIPE_MONTHLY_RECURRING_PRICE_ID:
            # Create subscription with trial period equal to prepaid months
            # The subscription will start charging after the trial ends
            subscription = stripe.Subscription.create(
                customer=org.stripe_customer_id,
                items=[{"price": STRIPE_MONTHLY_RECURRING_PRICE_ID}],  # $49.50/month
                trial_end=int(order.auto_renewal_starts_at.timestamp()),  # Start billing after prepaid period
                metadata={
                    "org_id": str(org.id),
                    "order_number": order.order_number,
                    "activation_date": activation_date.isoformat(),
                }
            )

            order.stripe_subscription_id = subscription.id
            org.stripe_subscription_id = subscription.id

            print(f"Created Stripe subscription {subscription.id} for org {org.id}, billing starts {order.auto_renewal_starts_at}")
        else:
            print(f"Warning: Could not create Stripe subscription - missing customer_id or price_id")
    except stripe.error.StripeError as e:
        # Log error but don't fail activation
        print(f"Error creating Stripe subscription: {e}")
        # Activation still succeeds, but auto-renewal won't work

    db.commit()
    db.refresh(order)
    db.refresh(org)

    return ActivationResponse(
        success=True,
        message=f"Activation successful! Your {order.plan_type} subscription is now active.",
        subscription_ends_at=order.subscription_ends_at.isoformat(),
        plan_type=order.plan_type
    )
