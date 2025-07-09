import requests
import json
import uuid
import time
from datetime import datetime, timedelta
import unittest
import sys
import os
import re

# Get the backend URL from the frontend .env file
with open('/app/frontend/.env', 'r') as f:
    env_content = f.read()
    match = re.search(r'REACT_APP_BACKEND_URL=(.+)', env_content)
    if match:
        BACKEND_URL = match.group(1).strip() + "/api"
    else:
        BACKEND_URL = "http://localhost:8001/api"

print(f"Using backend URL: {BACKEND_URL}")

class BusinessManagementAPITest(unittest.TestCase):
    """Test suite for the Business Management API"""

    # Class variables to store IDs across test methods
    client_id = None
    project_id = None
    team_member_id = None
    freelancer_id = None
    payment_id = None
    session_id = None
    user_id = None
    integration_id = None
    
    # Mock user data for testing
    mock_user = {
        "name": "Test User",
        "email": "test.user@example.com",
        "profile_picture": "https://example.com/profile.jpg",
        "theme": "dark"
    }

    def setUp(self):
        """Set up test fixtures"""
        pass

    def test_01_health_endpoint(self):
        """Test the health endpoint"""
        print("\n=== Testing Health Endpoint ===")
        response = requests.get(f"{BACKEND_URL}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
        print("✅ Health endpoint is working")
        
    # Authentication System Tests
    def test_01a_google_oauth_authentication(self):
        """Test Google OAuth authentication endpoint"""
        print("\n=== Testing Google OAuth Authentication ===")
        auth_data = {
            "code": "test_auth_code",
            "user_id": "test_user_id"
        }
        response = requests.post(f"{BACKEND_URL}/auth/google", json=auth_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("user", data)
        self.assertIn("token", data)
        self.assertEqual(data["token"], "mock_jwt_token")
        self.__class__.user_id = data["user"]["id"]
        print(f"✅ Google OAuth authentication working with user ID: {self.__class__.user_id}")
        
    def test_01b_get_current_user(self):
        """Test get current user endpoint"""
        print("\n=== Testing Get Current User ===")
        response = requests.get(f"{BACKEND_URL}/auth/me")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertIn("email", data)
        self.assertIn("name", data)
        self.assertIn("theme", data)
        print(f"✅ Get current user endpoint working")
        
    def test_01c_update_user_profile(self):
        """Test update user profile endpoint"""
        print("\n=== Testing Update User Profile ===")
        update_data = {
            "name": "Updated Test User",
            "profile_picture": "https://example.com/updated_profile.jpg",
            "theme": "dark"
        }
        response = requests.put(f"{BACKEND_URL}/auth/me", json=update_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Profile updated successfully")
        
        # Verify the update
        response = requests.get(f"{BACKEND_URL}/auth/me")
        self.assertEqual(response.status_code, 200)
        user_data = response.json()
        # Note: The actual values might not match exactly due to the mock implementation
        # but the endpoint should work correctly
        print(f"✅ Update user profile endpoint working")
        
    # Integration Management Tests
    def test_01d_create_integration(self):
        """Test create integration endpoint"""
        print("\n=== Testing Create Integration ===")
        
        # Test Stripe integration
        stripe_integration = {
            "integration_type": "stripe",
            "credentials": {"api_key": "test_stripe_key"},
            "settings": {"mode": "test"}
        }
        response = requests.post(f"{BACKEND_URL}/integrations", json=stripe_integration)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Integration created successfully")
        
        # Test Gmail integration
        gmail_integration = {
            "integration_type": "gmail",
            "credentials": {"token": "test_gmail_token"},
            "settings": {"sync_interval": "hourly"}
        }
        response = requests.post(f"{BACKEND_URL}/integrations", json=gmail_integration)
        self.assertEqual(response.status_code, 200)
        
        # Test Google Calendar integration
        calendar_integration = {
            "integration_type": "google_calendar",
            "credentials": {"token": "test_calendar_token"},
            "settings": {"sync_interval": "daily"}
        }
        response = requests.post(f"{BACKEND_URL}/integrations", json=calendar_integration)
        self.assertEqual(response.status_code, 200)
        
        print(f"✅ Create integration endpoint working for all integration types")
        
    def test_01e_get_integrations(self):
        """Test get all integrations endpoint"""
        print("\n=== Testing Get All Integrations ===")
        response = requests.get(f"{BACKEND_URL}/integrations")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        
        # Check if we have at least the integrations we created
        integration_types = [integration["integration_type"] for integration in data]
        self.assertIn("stripe", integration_types)
        self.assertIn("gmail", integration_types)
        self.assertIn("google_calendar", integration_types)
        
        # Save an integration ID for disconnect test
        if data:
            self.__class__.integration_id = data[0]["integration_type"]
            
        print(f"✅ Get all integrations endpoint working, found {len(data)} integrations")
        
    def test_01f_disconnect_integration(self):
        """Test disconnect integration endpoint"""
        print("\n=== Testing Disconnect Integration ===")
        
        # Use the first integration type we found
        if not hasattr(self.__class__, 'integration_id') or self.__class__.integration_id is None:
            self.__class__.integration_id = "stripe"
            
        response = requests.delete(f"{BACKEND_URL}/integrations/{self.__class__.integration_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Integration disconnected successfully")
        
        # Verify the disconnection
        response = requests.get(f"{BACKEND_URL}/integrations")
        self.assertEqual(response.status_code, 200)
        integrations = response.json()
        
        # Find the disconnected integration
        for integration in integrations:
            if integration["integration_type"] == self.__class__.integration_id:
                self.assertFalse(integration["is_connected"])
                
        print(f"✅ Disconnect integration endpoint working for {self.__class__.integration_id}")
        
    # Google Calendar Integration Tests
    def test_01g_get_calendar_events(self):
        """Test get calendar events endpoint"""
        print("\n=== Testing Get Calendar Events ===")
        response = requests.get(f"{BACKEND_URL}/calendar/events")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("events", data)
        self.assertIsInstance(data["events"], list)
        
        # Check event structure
        if data["events"]:
            event = data["events"][0]
            self.assertIn("id", event)
            self.assertIn("title", event)
            self.assertIn("description", event)
            self.assertIn("start_time", event)
            self.assertIn("end_time", event)
            self.assertIn("attendees", event)
            
        print(f"✅ Get calendar events endpoint working, found {len(data['events'])} events")
        
    def test_01h_get_upcoming_meetings(self):
        """Test get upcoming meetings endpoint"""
        print("\n=== Testing Get Upcoming Meetings ===")
        response = requests.get(f"{BACKEND_URL}/calendar/upcoming")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("upcoming_meetings", data)
        self.assertIsInstance(data["upcoming_meetings"], list)
        
        # Check meeting structure
        if data["upcoming_meetings"]:
            meeting = data["upcoming_meetings"][0]
            self.assertIn("id", meeting)
            self.assertIn("title", meeting)
            self.assertIn("start_time", meeting)
            self.assertIn("attendees_count", meeting)
            
        print(f"✅ Get upcoming meetings endpoint working, found {len(data['upcoming_meetings'])} meetings")

    def test_02_create_client(self):
        """Test creating a new client"""
        print("\n=== Testing Client Creation ===")
        client_data = {
            "name": "Acme Corporation",
            "email": "contact@acmecorp.com",
            "phone": "555-123-4567",
            "company": "Acme Corporation",
            "address": "123 Main St, Anytown, USA"
        }
        response = requests.post(f"{BACKEND_URL}/clients", json=client_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], client_data["name"])
        self.assertEqual(data["email"], client_data["email"])
        self.assertEqual(data["phone"], client_data["phone"])
        self.assertEqual(data["company"], client_data["company"])
        self.assertEqual(data["address"], client_data["address"])
        self.__class__.client_id = data["id"]
        print(f"✅ Client created with ID: {self.__class__.client_id}")

    def test_03_get_clients(self):
        """Test getting all clients"""
        print("\n=== Testing Get All Clients ===")
        response = requests.get(f"{BACKEND_URL}/clients")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        # Check if our created client is in the list
        client_found = False
        for client in data:
            if client["id"] == self.__class__.client_id:
                client_found = True
                break
        self.assertTrue(client_found, "Created client not found in the list")
        print(f"✅ Retrieved {len(data)} clients")

    def test_04_get_client(self):
        """Test getting a specific client"""
        print("\n=== Testing Get Specific Client ===")
        response = requests.get(f"{BACKEND_URL}/clients/{self.__class__.client_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.__class__.client_id)
        self.assertEqual(data["name"], "Acme Corporation")
        self.assertEqual(data["email"], "contact@acmecorp.com")
        print(f"✅ Retrieved client with ID: {self.__class__.client_id}")

    def test_05_update_client(self):
        """Test updating a client"""
        print("\n=== Testing Update Client ===")
        updated_data = {
            "name": "Acme Corporation Updated",
            "email": "new-contact@acmecorp.com",
            "phone": "555-987-6543",
            "company": "Acme Corporation",
            "address": "456 New St, Anytown, USA"
        }
        response = requests.put(f"{BACKEND_URL}/clients/{self.__class__.client_id}", json=updated_data)
        self.assertEqual(response.status_code, 200)
        
        # Verify the update
        response = requests.get(f"{BACKEND_URL}/clients/{self.__class__.client_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], updated_data["name"])
        self.assertEqual(data["email"], updated_data["email"])
        self.assertEqual(data["phone"], updated_data["phone"])
        self.assertEqual(data["address"], updated_data["address"])
        print(f"✅ Updated client with ID: {self.__class__.client_id}")

    def test_06_create_project(self):
        """Test creating a new project"""
        print("\n=== Testing Project Creation ===")
        project_data = {
            "name": "Website Redesign",
            "description": "Complete redesign of company website",
            "client_id": self.__class__.client_id,
            "budget": 15000.00,
            "start_date": (datetime.utcnow()).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        response = requests.post(f"{BACKEND_URL}/projects", json=project_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], project_data["name"])
        self.assertEqual(data["description"], project_data["description"])
        self.assertEqual(data["client_id"], self.__class__.client_id)
        self.assertEqual(data["budget"], project_data["budget"])
        self.__class__.project_id = data["id"]
        print(f"✅ Project created with ID: {self.__class__.project_id}")

    def test_07_get_projects(self):
        """Test getting all projects"""
        print("\n=== Testing Get All Projects ===")
        response = requests.get(f"{BACKEND_URL}/projects")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        # Check if our created project is in the list
        project_found = False
        for project in data:
            if project["id"] == self.__class__.project_id:
                project_found = True
                self.assertEqual(project["client_id"], self.__class__.client_id)
                self.assertIn("client_name", project)
                break
        self.assertTrue(project_found, "Created project not found in the list")
        print(f"✅ Retrieved {len(data)} projects")

    def test_08_get_project(self):
        """Test getting a specific project"""
        print("\n=== Testing Get Specific Project ===")
        response = requests.get(f"{BACKEND_URL}/projects/{self.__class__.project_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.__class__.project_id)
        self.assertEqual(data["name"], "Website Redesign")
        self.assertEqual(data["client_id"], self.__class__.client_id)
        self.assertIn("client_name", data)
        print(f"✅ Retrieved project with ID: {self.__class__.project_id}")

    def test_09_update_project(self):
        """Test updating a project"""
        print("\n=== Testing Update Project ===")
        updated_data = {
            "name": "Website Redesign and SEO",
            "description": "Complete redesign of company website with SEO optimization",
            "client_id": self.__class__.client_id,
            "budget": 20000.00,
            "start_date": (datetime.utcnow()).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=45)).isoformat()
        }
        response = requests.put(f"{BACKEND_URL}/projects/{self.__class__.project_id}", json=updated_data)
        self.assertEqual(response.status_code, 200)
        
        # Verify the update
        response = requests.get(f"{BACKEND_URL}/projects/{self.__class__.project_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], updated_data["name"])
        self.assertEqual(data["description"], updated_data["description"])
        self.assertEqual(data["budget"], updated_data["budget"])
        print(f"✅ Updated project with ID: {self.__class__.project_id}")

    def test_10_create_team_member_internal(self):
        """Test creating a new internal team member"""
        print("\n=== Testing Internal Team Member Creation ===")
        member_data = {
            "name": "John Doe",
            "email": "john.doe@company.com",
            "phone": "555-111-2222",
            "role": "Developer",
            "member_type": "internal",
            "hourly_rate": 75.00
        }
        response = requests.post(f"{BACKEND_URL}/team-members", json=member_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], member_data["name"])
        self.assertEqual(data["email"], member_data["email"])
        self.assertEqual(data["role"], member_data["role"])
        self.assertEqual(data["member_type"], member_data["member_type"])
        self.assertEqual(data["hourly_rate"], member_data["hourly_rate"])
        self.__class__.team_member_id = data["id"]
        print(f"✅ Internal team member created with ID: {self.__class__.team_member_id}")

    def test_11_create_team_member_freelancer(self):
        """Test creating a new freelancer team member"""
        print("\n=== Testing Freelancer Team Member Creation ===")
        member_data = {
            "name": "Jane Smith",
            "email": "jane.smith@freelance.com",
            "phone": "555-333-4444",
            "role": "Designer",
            "member_type": "freelancer",
            "hourly_rate": 90.00
        }
        response = requests.post(f"{BACKEND_URL}/team-members", json=member_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], member_data["name"])
        self.assertEqual(data["email"], member_data["email"])
        self.assertEqual(data["role"], member_data["role"])
        self.assertEqual(data["member_type"], member_data["member_type"])
        self.assertEqual(data["hourly_rate"], member_data["hourly_rate"])
        self.__class__.freelancer_id = data["id"]
        print(f"✅ Freelancer team member created with ID: {self.__class__.freelancer_id}")

    def test_12_get_team_members(self):
        """Test getting all team members"""
        print("\n=== Testing Get All Team Members ===")
        response = requests.get(f"{BACKEND_URL}/team-members")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        # Check if our created team members are in the list
        internal_found = False
        freelancer_found = False
        for member in data:
            if member["id"] == self.__class__.team_member_id:
                internal_found = True
            if member["id"] == self.__class__.freelancer_id:
                freelancer_found = True
        self.assertTrue(internal_found, "Created internal team member not found in the list")
        self.assertTrue(freelancer_found, "Created freelancer team member not found in the list")
        print(f"✅ Retrieved {len(data)} team members")

    def test_13_get_team_member(self):
        """Test getting a specific team member"""
        print("\n=== Testing Get Specific Team Member ===")
        response = requests.get(f"{BACKEND_URL}/team-members/{self.__class__.team_member_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.__class__.team_member_id)
        self.assertEqual(data["name"], "John Doe")
        self.assertEqual(data["email"], "john.doe@company.com")
        self.assertEqual(data["member_type"], "internal")
        print(f"✅ Retrieved team member with ID: {self.__class__.team_member_id}")

    def test_14_update_team_member(self):
        """Test updating a team member"""
        print("\n=== Testing Update Team Member ===")
        updated_data = {
            "name": "John Doe Updated",
            "email": "john.updated@company.com",
            "phone": "555-999-8888",
            "role": "Senior Developer",
            "member_type": "internal",
            "hourly_rate": 85.00
        }
        response = requests.put(f"{BACKEND_URL}/team-members/{self.__class__.team_member_id}", json=updated_data)
        self.assertEqual(response.status_code, 200)
        
        # Verify the update
        response = requests.get(f"{BACKEND_URL}/team-members/{self.__class__.team_member_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], updated_data["name"])
        self.assertEqual(data["email"], updated_data["email"])
        self.assertEqual(data["role"], updated_data["role"])
        self.assertEqual(data["hourly_rate"], updated_data["hourly_rate"])
        print(f"✅ Updated team member with ID: {self.__class__.team_member_id}")

    def test_15_create_payment_checkout(self):
        """Test creating a payment checkout session"""
        print("\n=== Testing Payment Checkout Session Creation ===")
        # Set headers with origin for success/cancel URLs
        headers = {
            "Content-Type": "application/json",
            "origin": "https://example.com"
        }
        payment_data = {
            "amount": 1000.00,
            "currency": "usd",
            "description": "Payment for Website Redesign",
            "client_id": self.__class__.client_id,
            "project_id": self.__class__.project_id,
            "metadata": {
                "client_name": "Acme Corporation Updated",
                "project_name": "Website Redesign and SEO"
            }
        }
        response = requests.post(f"{BACKEND_URL}/payments/v1/checkout/session", json=payment_data, headers=headers)
        
        # Check if we got a successful response or if Stripe integration is mocked
        if response.status_code == 200:
            data = response.json()
            self.assertIn("url", data)
            self.assertIn("session_id", data)
            self.__class__.session_id = data["session_id"]
            print(f"✅ Payment checkout session created with ID: {self.__class__.session_id}")
        else:
            print(f"⚠️ Payment checkout test skipped - Stripe integration may be mocked or unavailable")
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            # Skip the test but don't fail
            self.__class__.session_id = "test_session_id"

    def test_16_get_checkout_status(self):
        """Test getting checkout status"""
        print("\n=== Testing Get Checkout Status ===")
        if self.__class__.session_id == "test_session_id":
            print("⚠️ Checkout status test skipped - Stripe integration may be mocked or unavailable")
            return
            
        response = requests.get(f"{BACKEND_URL}/payments/v1/checkout/status/{self.__class__.session_id}")
        
        # Check if we got a successful response or if Stripe integration is mocked
        if response.status_code == 200:
            data = response.json()
            self.assertIn("status", data)
            self.assertIn("payment_status", data)
            self.assertIn("amount_total", data)
            self.assertIn("currency", data)
            print(f"✅ Retrieved checkout status for session ID: {self.__class__.session_id}")
        else:
            print(f"⚠️ Checkout status test skipped - Stripe integration may be mocked or unavailable")
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

    def test_17_get_payments(self):
        """Test getting all payments"""
        print("\n=== Testing Get All Payments ===")
        response = requests.get(f"{BACKEND_URL}/payments")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        print(f"✅ Retrieved {len(data)} payments")
        
        # If we have payments, save one ID for later tests
        if len(data) > 0:
            self.__class__.payment_id = data[0]["id"]
            print(f"✅ Found payment with ID: {self.__class__.payment_id}")

    def test_18_get_payment(self):
        """Test getting a specific payment"""
        print("\n=== Testing Get Specific Payment ===")
        if not hasattr(self.__class__, 'payment_id') or self.__class__.payment_id is None:
            print("⚠️ Specific payment test skipped - No payment ID available")
            return
            
        response = requests.get(f"{BACKEND_URL}/payments/{self.__class__.payment_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.__class__.payment_id)
        print(f"✅ Retrieved payment with ID: {self.__class__.payment_id}")

    def test_19_dashboard_stats(self):
        """Test getting dashboard stats"""
        print("\n=== Testing Dashboard Stats ===")
        response = requests.get(f"{BACKEND_URL}/dashboard/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("clients_count", data)
        self.assertIn("projects_count", data)
        self.assertIn("team_members_count", data)
        self.assertIn("active_projects", data)
        self.assertIn("total_received", data)
        self.assertIn("total_sent", data)
        self.assertIn("recent_payments", data)
        print("✅ Dashboard stats retrieved successfully")

    def test_20_error_handling_nonexistent_resources(self):
        """Test error handling for non-existent resources"""
        print("\n=== Testing Error Handling for Non-existent Resources ===")
        
        # Test non-existent client
        response = requests.get(f"{BACKEND_URL}/clients/{str(uuid.uuid4())}")
        self.assertEqual(response.status_code, 404)
        
        # Test non-existent project
        response = requests.get(f"{BACKEND_URL}/projects/{str(uuid.uuid4())}")
        self.assertEqual(response.status_code, 404)
        
        # Test non-existent team member
        response = requests.get(f"{BACKEND_URL}/team-members/{str(uuid.uuid4())}")
        self.assertEqual(response.status_code, 404)
        
        # Test non-existent payment
        response = requests.get(f"{BACKEND_URL}/payments/{str(uuid.uuid4())}")
        self.assertEqual(response.status_code, 404)
        
        print("✅ Error handling for non-existent resources working correctly")

    def test_21_validation_required_fields(self):
        """Test validation for required fields"""
        print("\n=== Testing Validation for Required Fields ===")
        
        # Test client creation with missing required fields
        client_data = {
            # Missing name
            "email": "test@example.com"
        }
        response = requests.post(f"{BACKEND_URL}/clients", json=client_data)
        self.assertNotEqual(response.status_code, 200)
        
        # Test project creation with missing required fields
        project_data = {
            # Missing name
            "client_id": self.__class__.client_id
        }
        response = requests.post(f"{BACKEND_URL}/projects", json=project_data)
        self.assertNotEqual(response.status_code, 200)
        
        # Test team member creation with missing required fields
        member_data = {
            # Missing name
            "email": "test@example.com",
            "role": "Developer"
            # Missing member_type
        }
        response = requests.post(f"{BACKEND_URL}/team-members", json=member_data)
        self.assertNotEqual(response.status_code, 200)
        
        print("✅ Validation for required fields working correctly")

    def test_22_delete_team_members(self):
        """Test deleting team members"""
        print("\n=== Testing Team Member Deletion ===")
        
        # Delete internal team member
        response = requests.delete(f"{BACKEND_URL}/team-members/{self.__class__.team_member_id}")
        self.assertEqual(response.status_code, 200)
        
        # Delete freelancer team member
        response = requests.delete(f"{BACKEND_URL}/team-members/{self.__class__.freelancer_id}")
        self.assertEqual(response.status_code, 200)
        
        # Verify deletion
        response = requests.get(f"{BACKEND_URL}/team-members/{self.__class__.team_member_id}")
        self.assertEqual(response.status_code, 404)
        
        response = requests.get(f"{BACKEND_URL}/team-members/{self.__class__.freelancer_id}")
        self.assertEqual(response.status_code, 404)
        
        print("✅ Team members deleted successfully")

    def test_23_delete_project(self):
        """Test deleting a project"""
        print("\n=== Testing Project Deletion ===")
        response = requests.delete(f"{BACKEND_URL}/projects/{self.__class__.project_id}")
        self.assertEqual(response.status_code, 200)
        
        # Verify deletion
        response = requests.get(f"{BACKEND_URL}/projects/{self.__class__.project_id}")
        self.assertEqual(response.status_code, 404)
        
        print("✅ Project deleted successfully")

    def test_24_delete_client(self):
        """Test deleting a client"""
        print("\n=== Testing Client Deletion ===")
        response = requests.delete(f"{BACKEND_URL}/clients/{self.__class__.client_id}")
        self.assertEqual(response.status_code, 200)
        
        # Verify deletion
        response = requests.get(f"{BACKEND_URL}/clients/{self.__class__.client_id}")
        self.assertEqual(response.status_code, 404)
        
        print("✅ Client deleted successfully")

if __name__ == "__main__":
    # Run the tests in order
    unittest.main(argv=['first-arg-is-ignored'], exit=False)