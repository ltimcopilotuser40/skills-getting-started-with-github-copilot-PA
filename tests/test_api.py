"""
Test suite for the High School Management System API

Tests cover:
- GET /activities endpoint
- POST /activities/{activity_name}/signup endpoint
- DELETE /activities/{activity_name}/unregister endpoint
- Error handling and edge cases
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_participants = {
        name: activity["participants"].copy()
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, activity in activities.items():
        activity["participants"] = original_participants[name]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test successful retrieval of all activities"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Soccer Team" in data
        assert "Swimming Club" in data
        assert "Programming Class" in data
    
    def test_activities_structure(self, client):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer Team/signup?email=test@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_participant(self, client):
        """Test that duplicate signup is prevented"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/Soccer Team/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/Soccer Team/signup?email={email}"
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity names"""
        # Using Chess Club which exists
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "unregister@mergington.edu"
        
        # First, sign up
        client.post(f"/activities/Soccer Team/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/Soccer Team/unregister?email={email}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Soccer Team"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_unregister_not_signed_up(self, client):
        """Test unregister when not signed up returns 400"""
        response = client.delete(
            "/activities/Soccer Team/unregister?email=notregistered@mergington.edu"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # Soccer Team has james@mergington.edu as existing participant
        response = client.delete(
            "/activities/Soccer Team/unregister?email=james@mergington.edu"
        )
        
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "james@mergington.edu" not in activities_data["Soccer Team"]["participants"]


class TestRootRedirect:
    """Tests for root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root path redirects to static HTML"""
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code in [307, 308]  # Temporary or permanent redirect
        assert "/static/index.html" in response.headers["location"]


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signup and unregister"""
        email = "workflow@mergington.edu"
        activity = "Drama Club"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify count increased
        after_signup = client.get("/activities")
        after_signup_count = len(after_signup.json()[activity]["participants"])
        assert after_signup_count == initial_count + 1
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify count returned to original
        final_response = client.get("/activities")
        final_count = len(final_response.json()[activity]["participants"])
        assert final_count == initial_count
    
    def test_multiple_activities_signup(self, client):
        """Test signing up for multiple activities"""
        email = "multi@mergington.edu"
        activities_to_join = ["Soccer Team", "Chess Club", "Programming Class"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for activity in activities_to_join:
            assert email in activities_data[activity]["participants"]
