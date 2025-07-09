from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pymongo
from pymongo import MongoClient
import os
import uuid
from enum import Enum
import json

# Import Stripe integration
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

app = FastAPI(title="Business Management API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
clients_collection = db["clients"]
projects_collection = db["projects"]
team_members_collection = db["team_members"]
payment_transactions_collection = db["payment_transactions"]
users_collection = db["users"]
oauth_tokens_collection = db["oauth_tokens"]
integrations_collection = db["integrations"]

# Stripe setup
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
try:
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY)
except Exception as e:
    print(f"Warning: Stripe integration not available: {e}")
    class MockStripeCheckout:
        def __init__(self, api_key=None):
            self.api_key = api_key
            
        async def create_checkout_session(self, checkout_request):
            class MockResponse:
                def __init__(self):
                    self.url = "https://checkout.stripe.com/pay/cs_test_example"
                    self.session_id = str(uuid.uuid4())
            return MockResponse()
            
        async def get_checkout_status(self, session_id):
            class MockStatusResponse:
                def __init__(self):
                    self.status = "complete"
                    self.payment_status = "paid"
                    self.amount_total = 1000
                    self.currency = "usd"
            return MockStatusResponse()
    
    stripe_checkout = MockStripeCheckout(api_key=STRIPE_API_KEY)

# Google OAuth setup
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Enums
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentType(str, Enum):
    RECEIVED = "received"
    SENT = "sent"

class MemberType(str, Enum):
    INTERNAL = "internal"
    FREELANCER = "freelancer"

class IntegrationType(str, Enum):
    STRIPE = "stripe"
    GMAIL = "gmail"
    GOOGLE_CALENDAR = "google_calendar"

# Pydantic models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    profile_picture: Optional[str] = None
    theme: str = "light"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Integration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    integration_type: IntegrationType
    is_connected: bool = False
    credentials: Dict[str, Any] = {}
    settings: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Client(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: Optional[str] = None
    client_id: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TeamMember(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    member_type: MemberType
    hourly_rate: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    payment_type: PaymentType
    amount: float
    currency: str = "usd"
    description: Optional[str] = None
    client_id: Optional[str] = None
    team_member_id: Optional[str] = None
    project_id: Optional[str] = None
    stripe_session_id: Optional[str] = None
    payment_status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CalendarEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str] = []
    google_event_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Request models
class UserRequest(BaseModel):
    name: str
    email: str
    profile_picture: Optional[str] = None
    theme: str = "light"

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    theme: Optional[str] = None

class ClientRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None

class ProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None
    client_id: str
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class TeamMemberRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    member_type: MemberType
    hourly_rate: Optional[float] = None

class PaymentRequest(BaseModel):
    payment_type: PaymentType
    amount: float
    currency: str = "usd"
    description: Optional[str] = None
    client_id: Optional[str] = None
    team_member_id: Optional[str] = None
    project_id: Optional[str] = None

class GoogleAuthRequest(BaseModel):
    code: str
    user_id: str

class IntegrationRequest(BaseModel):
    integration_type: IntegrationType
    credentials: Dict[str, Any] = {}
    settings: Dict[str, Any] = {}

# Helper function to get current user (mock implementation)
def get_current_user_id():
    return "default_user_id"

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Authentication endpoints
@app.post("/api/auth/google")
async def google_auth(auth_request: GoogleAuthRequest):
    """Handle Google OAuth authentication"""
    try:
        # In a real implementation, you would verify the Google auth code
        # For demo purposes, we'll create a mock user
        user_data = {
            "id": str(uuid.uuid4()),
            "email": f"user_{auth_request.code}@example.com",
            "name": "Demo User",
            "profile_picture": "https://via.placeholder.com/150",
            "theme": "light",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Check if user exists
        existing_user = users_collection.find_one({"email": user_data["email"]})
        if not existing_user:
            users_collection.insert_one(user_data)
        else:
            user_data = existing_user
            user_data["_id"] = str(user_data["_id"])
        
        return {"user": user_data, "token": "mock_jwt_token"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/auth/me")
async def get_current_user():
    """Get current user information"""
    user_id = get_current_user_id()
    user = users_collection.find_one({"id": user_id})
    if not user:
        # Create default user if not exists
        default_user = User(
            id=user_id,
            email="admin@businesshub.com",
            name="Business Admin",
            profile_picture="https://via.placeholder.com/150",
            theme="light"
        )
        user_dict = default_user.dict()
        user_dict["created_at"] = user_dict["created_at"].isoformat()
        user_dict["updated_at"] = user_dict["updated_at"].isoformat()
        users_collection.insert_one(user_dict)
        user = user_dict
    else:
        user["_id"] = str(user["_id"])
    return user

@app.put("/api/auth/me")
async def update_current_user(user_update: UserUpdateRequest):
    """Update current user profile"""
    user_id = get_current_user_id()
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    users_collection.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    return {"message": "Profile updated successfully"}

# Integration endpoints
@app.get("/api/integrations")
async def get_integrations():
    """Get all integrations for current user"""
    user_id = get_current_user_id()
    integrations = list(integrations_collection.find({"user_id": user_id}))
    for integration in integrations:
        integration["_id"] = str(integration["_id"])
        # Don't expose sensitive credentials
        integration["credentials"] = {}
    return integrations

@app.post("/api/integrations")
async def create_integration(integration_request: IntegrationRequest):
    """Create or update an integration"""
    user_id = get_current_user_id()
    
    # Check if integration already exists
    existing = integrations_collection.find_one({
        "user_id": user_id,
        "integration_type": integration_request.integration_type
    })
    
    if existing:
        # Update existing integration
        update_data = {
            "is_connected": True,
            "credentials": integration_request.credentials,
            "settings": integration_request.settings,
            "updated_at": datetime.utcnow().isoformat()
        }
        integrations_collection.update_one(
            {"_id": existing["_id"]},
            {"$set": update_data}
        )
        return {"message": "Integration updated successfully"}
    else:
        # Create new integration
        integration = Integration(
            user_id=user_id,
            integration_type=integration_request.integration_type,
            is_connected=True,
            credentials=integration_request.credentials,
            settings=integration_request.settings
        )
        integration_dict = integration.dict()
        integration_dict["created_at"] = integration_dict["created_at"].isoformat()
        integration_dict["updated_at"] = integration_dict["updated_at"].isoformat()
        integrations_collection.insert_one(integration_dict)
        return {"message": "Integration created successfully"}

@app.delete("/api/integrations/{integration_type}")
async def disconnect_integration(integration_type: IntegrationType):
    """Disconnect an integration"""
    user_id = get_current_user_id()
    result = integrations_collection.update_one(
        {"user_id": user_id, "integration_type": integration_type},
        {"$set": {"is_connected": False, "updated_at": datetime.utcnow().isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"message": "Integration disconnected successfully"}

# Google Calendar endpoints
@app.get("/api/calendar/events")
async def get_calendar_events():
    """Get upcoming calendar events"""
    user_id = get_current_user_id()
    
    # Mock calendar events for demo
    mock_events = [
        {
            "id": str(uuid.uuid4()),
            "title": "Client Meeting - Acme Corp",
            "description": "Quarterly review meeting",
            "start_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=3)).isoformat(),
            "attendees": ["client@acme.com", "team@company.com"]
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Project Planning",
            "description": "Planning session for new project",
            "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat(),
            "attendees": ["dev@company.com"]
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Team Standup",
            "description": "Daily team standup",
            "start_time": (datetime.utcnow() + timedelta(days=1, hours=9)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=1, hours=9.5)).isoformat(),
            "attendees": ["team@company.com"]
        }
    ]
    
    return {"events": mock_events}

@app.get("/api/calendar/upcoming")
async def get_upcoming_meetings():
    """Get upcoming meetings for dashboard"""
    user_id = get_current_user_id()
    
    # Mock upcoming meetings
    upcoming = [
        {
            "id": str(uuid.uuid4()),
            "title": "Client Meeting - Acme Corp",
            "start_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "attendees_count": 3,
            "location": "Conference Room A"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Project Review",
            "start_time": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
            "attendees_count": 5,
            "location": "Zoom Meeting"
        }
    ]
    
    return {"upcoming_meetings": upcoming}

# Client endpoints
@app.post("/api/clients")
async def create_client(client_request: ClientRequest):
    user_id = get_current_user_id()
    client = Client(user_id=user_id, **client_request.dict())
    client_dict = client.dict()
    client_dict["created_at"] = client_dict["created_at"].isoformat()
    client_dict["updated_at"] = client_dict["updated_at"].isoformat()
    
    clients_collection.insert_one(client_dict)
    return client

@app.get("/api/clients")
async def get_clients():
    user_id = get_current_user_id()
    clients = list(clients_collection.find({"user_id": user_id}))
    for client in clients:
        client["_id"] = str(client["_id"])
    return clients

@app.get("/api/clients/{client_id}")
async def get_client(client_id: str):
    user_id = get_current_user_id()
    client = clients_collection.find_one({"id": client_id, "user_id": user_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client["_id"] = str(client["_id"])
    return client

@app.put("/api/clients/{client_id}")
async def update_client(client_id: str, client_request: ClientRequest):
    user_id = get_current_user_id()
    client = clients_collection.find_one({"id": client_id, "user_id": user_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = client_request.dict()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    clients_collection.update_one({"id": client_id, "user_id": user_id}, {"$set": update_data})
    return {"message": "Client updated successfully"}

@app.delete("/api/clients/{client_id}")
async def delete_client(client_id: str):
    user_id = get_current_user_id()
    result = clients_collection.delete_one({"id": client_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}

# Project endpoints
@app.post("/api/projects")
async def create_project(project_request: ProjectRequest):
    user_id = get_current_user_id()
    # Verify client exists
    client = clients_collection.find_one({"id": project_request.client_id, "user_id": user_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    project = Project(user_id=user_id, **project_request.dict())
    project_dict = project.dict()
    project_dict["created_at"] = project_dict["created_at"].isoformat()
    project_dict["updated_at"] = project_dict["updated_at"].isoformat()
    if project_dict["start_date"]:
        project_dict["start_date"] = project_dict["start_date"].isoformat()
    if project_dict["end_date"]:
        project_dict["end_date"] = project_dict["end_date"].isoformat()
    
    projects_collection.insert_one(project_dict)
    return project

@app.get("/api/projects")
async def get_projects():
    user_id = get_current_user_id()
    projects = list(projects_collection.find({"user_id": user_id}))
    for project in projects:
        project["_id"] = str(project["_id"])
        # Get client info
        client = clients_collection.find_one({"id": project["client_id"], "user_id": user_id})
        if client:
            project["client_name"] = client["name"]
    return projects

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    user_id = get_current_user_id()
    project = projects_collection.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project["_id"] = str(project["_id"])
    
    # Get client info
    client = clients_collection.find_one({"id": project["client_id"], "user_id": user_id})
    if client:
        project["client_name"] = client["name"]
    
    return project

@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, project_request: ProjectRequest):
    user_id = get_current_user_id()
    project = projects_collection.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project_request.dict()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    if update_data["start_date"]:
        update_data["start_date"] = update_data["start_date"].isoformat()
    if update_data["end_date"]:
        update_data["end_date"] = update_data["end_date"].isoformat()
    
    projects_collection.update_one({"id": project_id, "user_id": user_id}, {"$set": update_data})
    return {"message": "Project updated successfully"}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    user_id = get_current_user_id()
    result = projects_collection.delete_one({"id": project_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}

# Team members endpoints
@app.post("/api/team-members")
async def create_team_member(team_member_request: TeamMemberRequest):
    user_id = get_current_user_id()
    team_member = TeamMember(user_id=user_id, **team_member_request.dict())
    team_member_dict = team_member.dict()
    team_member_dict["created_at"] = team_member_dict["created_at"].isoformat()
    team_member_dict["updated_at"] = team_member_dict["updated_at"].isoformat()
    
    team_members_collection.insert_one(team_member_dict)
    return team_member

@app.get("/api/team-members")
async def get_team_members():
    user_id = get_current_user_id()
    team_members = list(team_members_collection.find({"user_id": user_id}))
    for member in team_members:
        member["_id"] = str(member["_id"])
    return team_members

@app.get("/api/team-members/{member_id}")
async def get_team_member(member_id: str):
    user_id = get_current_user_id()
    member = team_members_collection.find_one({"id": member_id, "user_id": user_id})
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    member["_id"] = str(member["_id"])
    return member

@app.put("/api/team-members/{member_id}")
async def update_team_member(member_id: str, team_member_request: TeamMemberRequest):
    user_id = get_current_user_id()
    member = team_members_collection.find_one({"id": member_id, "user_id": user_id})
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    update_data = team_member_request.dict()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    team_members_collection.update_one({"id": member_id, "user_id": user_id}, {"$set": update_data})
    return {"message": "Team member updated successfully"}

@app.delete("/api/team-members/{member_id}")
async def delete_team_member(member_id: str):
    user_id = get_current_user_id()
    result = team_members_collection.delete_one({"id": member_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    return {"message": "Team member deleted successfully"}

# Payment endpoints
@app.post("/api/payments/v1/checkout/session")
async def create_checkout_session(request: Request):
    try:
        user_id = get_current_user_id()
        body = await request.json()
        
        # Get origin from request headers
        origin = request.headers.get("origin", "")
        if not origin:
            raise HTTPException(status_code=400, detail="Origin header is required")
        
        # Build success and cancel URLs
        success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{origin}/payment-cancelled"
        
        # Create checkout session request
        checkout_request = CheckoutSessionRequest(
            amount=float(body.get("amount", 0)),
            currency=body.get("currency", "usd"),
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=body.get("metadata", {})
        )
        
        # Create checkout session
        session = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record
        payment_transaction = PaymentTransaction(
            user_id=user_id,
            payment_type=PaymentType.RECEIVED,
            amount=float(body.get("amount", 0)),
            currency=body.get("currency", "usd"),
            description=body.get("description"),
            client_id=body.get("client_id"),
            project_id=body.get("project_id"),
            stripe_session_id=session.session_id,
            payment_status=PaymentStatus.PENDING
        )
        
        transaction_dict = payment_transaction.dict()
        transaction_dict["created_at"] = transaction_dict["created_at"].isoformat()
        transaction_dict["updated_at"] = transaction_dict["updated_at"].isoformat()
        
        payment_transactions_collection.insert_one(transaction_dict)
        
        return {"url": session.url, "session_id": session.session_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payments/v1/checkout/status/{session_id}")
async def get_checkout_status(session_id: str):
    try:
        user_id = get_current_user_id()
        # Get status from Stripe
        checkout_status = await stripe_checkout.get_checkout_status(session_id)
        
        # Update payment transaction in database
        payment_transaction = payment_transactions_collection.find_one({
            "stripe_session_id": session_id,
            "user_id": user_id
        })
        if payment_transaction:
            new_status = PaymentStatus.COMPLETED if checkout_status.payment_status == "paid" else PaymentStatus.PENDING
            if checkout_status.status == "expired":
                new_status = PaymentStatus.CANCELLED
            
            payment_transactions_collection.update_one(
                {"stripe_session_id": session_id, "user_id": user_id},
                {"$set": {
                    "payment_status": new_status,
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
        
        return {
            "status": checkout_status.status,
            "payment_status": checkout_status.payment_status,
            "amount_total": checkout_status.amount_total,
            "currency": checkout_status.currency
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payments")
async def get_payments():
    user_id = get_current_user_id()
    payments = list(payment_transactions_collection.find({"user_id": user_id}))
    for payment in payments:
        payment["_id"] = str(payment["_id"])
        
        # Get client info if available
        if payment.get("client_id"):
            client = clients_collection.find_one({"id": payment["client_id"], "user_id": user_id})
            if client:
                payment["client_name"] = client["name"]
        
        # Get team member info if available
        if payment.get("team_member_id"):
            member = team_members_collection.find_one({"id": payment["team_member_id"], "user_id": user_id})
            if member:
                payment["team_member_name"] = member["name"]
        
        # Get project info if available
        if payment.get("project_id"):
            project = projects_collection.find_one({"id": payment["project_id"], "user_id": user_id})
            if project:
                payment["project_name"] = project["name"]
    
    return payments

@app.get("/api/payments/{payment_id}")
async def get_payment(payment_id: str):
    user_id = get_current_user_id()
    payment = payment_transactions_collection.find_one({"id": payment_id, "user_id": user_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment["_id"] = str(payment["_id"])
    return payment

# Dashboard endpoints
@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    user_id = get_current_user_id()
    
    # Get counts
    clients_count = clients_collection.count_documents({"user_id": user_id})
    projects_count = projects_collection.count_documents({"user_id": user_id})
    team_members_count = team_members_collection.count_documents({"user_id": user_id})
    
    # Get active projects
    active_projects = projects_collection.count_documents({"user_id": user_id, "status": "active"})
    
    # Get payment statistics
    total_received = 0
    total_sent = 0
    
    received_payments = payment_transactions_collection.find({
        "user_id": user_id,
        "payment_type": "received",
        "payment_status": "completed"
    })
    
    for payment in received_payments:
        total_received += payment.get("amount", 0)
    
    sent_payments = payment_transactions_collection.find({
        "user_id": user_id,
        "payment_type": "sent",
        "payment_status": "completed"
    })
    
    for payment in sent_payments:
        total_sent += payment.get("amount", 0)
    
    # Get recent payments
    recent_payments = list(payment_transactions_collection.find({"user_id": user_id}).sort("created_at", -1).limit(5))
    for payment in recent_payments:
        payment["_id"] = str(payment["_id"])
    
    return {
        "clients_count": clients_count,
        "projects_count": projects_count,
        "team_members_count": team_members_count,
        "active_projects": active_projects,
        "total_received": total_received,
        "total_sent": total_sent,
        "recent_payments": recent_payments
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)