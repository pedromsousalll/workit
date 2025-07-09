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
freelancers_collection = db["freelancers"]

# Stripe setup
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")
stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY)

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
    RECEIVED = "received"  # Money received from clients
    SENT = "sent"  # Money sent to freelancers/team

class MemberType(str, Enum):
    INTERNAL = "internal"  # Internal team member
    FREELANCER = "freelancer"  # External freelancer

# Pydantic models
class Client(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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
    payment_type: PaymentType
    amount: float
    currency: str = "usd"
    description: Optional[str] = None
    client_id: Optional[str] = None  # For received payments
    team_member_id: Optional[str] = None  # For sent payments
    project_id: Optional[str] = None
    stripe_session_id: Optional[str] = None
    payment_status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Request models
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

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Client endpoints
@app.post("/api/clients")
async def create_client(client_request: ClientRequest):
    client = Client(**client_request.dict())
    client_dict = client.dict()
    client_dict["created_at"] = client_dict["created_at"].isoformat()
    client_dict["updated_at"] = client_dict["updated_at"].isoformat()
    
    clients_collection.insert_one(client_dict)
    return client

@app.get("/api/clients")
async def get_clients():
    clients = list(clients_collection.find({}))
    for client in clients:
        client["_id"] = str(client["_id"])
    return clients

@app.get("/api/clients/{client_id}")
async def get_client(client_id: str):
    client = clients_collection.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client["_id"] = str(client["_id"])
    return client

@app.put("/api/clients/{client_id}")
async def update_client(client_id: str, client_request: ClientRequest):
    client = clients_collection.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = client_request.dict()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    clients_collection.update_one({"id": client_id}, {"$set": update_data})
    return {"message": "Client updated successfully"}

@app.delete("/api/clients/{client_id}")
async def delete_client(client_id: str):
    result = clients_collection.delete_one({"id": client_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}

# Project endpoints
@app.post("/api/projects")
async def create_project(project_request: ProjectRequest):
    # Verify client exists
    client = clients_collection.find_one({"id": project_request.client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    project = Project(**project_request.dict())
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
    projects = list(projects_collection.find({}))
    for project in projects:
        project["_id"] = str(project["_id"])
        # Get client info
        client = clients_collection.find_one({"id": project["client_id"]})
        if client:
            project["client_name"] = client["name"]
    return projects

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    project = projects_collection.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project["_id"] = str(project["_id"])
    
    # Get client info
    client = clients_collection.find_one({"id": project["client_id"]})
    if client:
        project["client_name"] = client["name"]
    
    return project

@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, project_request: ProjectRequest):
    project = projects_collection.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project_request.dict()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    if update_data["start_date"]:
        update_data["start_date"] = update_data["start_date"].isoformat()
    if update_data["end_date"]:
        update_data["end_date"] = update_data["end_date"].isoformat()
    
    projects_collection.update_one({"id": project_id}, {"$set": update_data})
    return {"message": "Project updated successfully"}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    result = projects_collection.delete_one({"id": project_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}

# Team members endpoints
@app.post("/api/team-members")
async def create_team_member(team_member_request: TeamMemberRequest):
    team_member = TeamMember(**team_member_request.dict())
    team_member_dict = team_member.dict()
    team_member_dict["created_at"] = team_member_dict["created_at"].isoformat()
    team_member_dict["updated_at"] = team_member_dict["updated_at"].isoformat()
    
    team_members_collection.insert_one(team_member_dict)
    return team_member

@app.get("/api/team-members")
async def get_team_members():
    team_members = list(team_members_collection.find({}))
    for member in team_members:
        member["_id"] = str(member["_id"])
    return team_members

@app.get("/api/team-members/{member_id}")
async def get_team_member(member_id: str):
    member = team_members_collection.find_one({"id": member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    member["_id"] = str(member["_id"])
    return member

@app.put("/api/team-members/{member_id}")
async def update_team_member(member_id: str, team_member_request: TeamMemberRequest):
    member = team_members_collection.find_one({"id": member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    update_data = team_member_request.dict()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    team_members_collection.update_one({"id": member_id}, {"$set": update_data})
    return {"message": "Team member updated successfully"}

@app.delete("/api/team-members/{member_id}")
async def delete_team_member(member_id: str):
    result = team_members_collection.delete_one({"id": member_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    return {"message": "Team member deleted successfully"}

# Payment endpoints
@app.post("/api/payments/v1/checkout/session")
async def create_checkout_session(request: Request):
    try:
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
        # Get status from Stripe
        checkout_status = await stripe_checkout.get_checkout_status(session_id)
        
        # Update payment transaction in database
        payment_transaction = payment_transactions_collection.find_one({"stripe_session_id": session_id})
        if payment_transaction:
            new_status = PaymentStatus.COMPLETED if checkout_status.payment_status == "paid" else PaymentStatus.PENDING
            if checkout_status.status == "expired":
                new_status = PaymentStatus.CANCELLED
            
            payment_transactions_collection.update_one(
                {"stripe_session_id": session_id},
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
    payments = list(payment_transactions_collection.find({}))
    for payment in payments:
        payment["_id"] = str(payment["_id"])
        
        # Get client info if available
        if payment.get("client_id"):
            client = clients_collection.find_one({"id": payment["client_id"]})
            if client:
                payment["client_name"] = client["name"]
        
        # Get team member info if available
        if payment.get("team_member_id"):
            member = team_members_collection.find_one({"id": payment["team_member_id"]})
            if member:
                payment["team_member_name"] = member["name"]
        
        # Get project info if available
        if payment.get("project_id"):
            project = projects_collection.find_one({"id": payment["project_id"]})
            if project:
                payment["project_name"] = project["name"]
    
    return payments

@app.get("/api/payments/{payment_id}")
async def get_payment(payment_id: str):
    payment = payment_transactions_collection.find_one({"id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment["_id"] = str(payment["_id"])
    return payment

# Dashboard endpoints
@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    # Get counts
    clients_count = clients_collection.count_documents({})
    projects_count = projects_collection.count_documents({})
    team_members_count = team_members_collection.count_documents({})
    
    # Get active projects
    active_projects = projects_collection.count_documents({"status": "active"})
    
    # Get payment statistics
    total_received = 0
    total_sent = 0
    
    received_payments = payment_transactions_collection.find({
        "payment_type": "received",
        "payment_status": "completed"
    })
    
    for payment in received_payments:
        total_received += payment.get("amount", 0)
    
    sent_payments = payment_transactions_collection.find({
        "payment_type": "sent",
        "payment_status": "completed"
    })
    
    for payment in sent_payments:
        total_sent += payment.get("amount", 0)
    
    # Get recent payments
    recent_payments = list(payment_transactions_collection.find({}).sort("created_at", -1).limit(5))
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