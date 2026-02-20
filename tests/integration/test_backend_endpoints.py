"""
Integration tests for Backend Service endpoints

Tests ALL valid backend endpoints against test_config.yaml configuration.

Requirements:
- Backend service running on port 8000
- Aliyun RDS databases accessible
- Test config: backend/configs/test_config.yaml

Frontend Usage: YES
- beta_frontend H5 web interface uses these endpoints
- JS modules: auth.js, main.js
- API calls match backend routes

Test Coverage:
- TestHealthEndpoints: Root, health check, research domains
- TestAuthEndpoints: Registration, login (success/failure), duplicate detection, user cleanup

Usage:
    pytest tests/integration/test_backend_endpoints.py -v

Run specific test classes:
    pytest tests/integration/test_backend_endpoints.py::TestHealthEndpoints -v
    pytest tests/integration/test_backend_endpoints.py::TestAuthEndpoints -v
"""

import pytest
import requests
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.shared.config_utils import load_config


# Load test configuration
config = load_config("backend/configs/test_config.yaml", service="backend")
base_url = config["APP_SERVICE"]["host"]
# Note: using http:// directly (http://localhost:8080)


class TestHealthEndpoints:
    """Test health and status endpoints - Used by frontend for connectivity checks"""

    def test_root_endpoint(self):
        """Test GET / - Frontend uses this for basic connectivity"""
        response = requests.get(f"{base_url}/", timeout=10)
        assert response.status_code == 200
        # Frontend expects HTML or JSON response

    def test_health_check(self):
        """Test GET /api/health - Frontend uses for service health monitoring"""
        response = requests.get(f"{base_url}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "message" in data

    def test_research_domains(self):
        """Test GET /api/domains - Frontend uses for research domain dropdown"""
        response = requests.get(f"{base_url}/api/domains", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Frontend expects domain structure with name, code, description


class TestAuthEndpoints:
    """Test authentication endpoints - beta_frontend/js/auth.js uses these"""

    @classmethod
    def setup_class(cls):
        """Setup test configuration"""
        cls.test_email = "test@example.com"
        cls.test_username = "testuser"
        cls.test_password = "testpass123"

    def cleanup_test_user(self):
        """Clean up test user before/after tests"""
        try:
            response = requests.delete(
                f"{base_url}/api/auth/users/{self.test_email}",
                headers={"X-Test-Mode": "true"},
                timeout=10
            )
            # Ignore 404 (user doesn't exist) - that's fine
            if response.status_code not in [200, 404]:
                print(f"Warning: Cleanup failed with status {response.status_code}")
        except Exception as e:
            print(f"Warning: Cleanup failed with error: {e}")

    def test_email_register(self):
        """Test POST /api/auth/register-email - Frontend registration flow"""
        # Clean up first to ensure we can test fresh registration
        self.cleanup_test_user()

        response = requests.post(
            f"{base_url}/api/auth/register-email",
            json={
                "email": self.test_email,
                "username": self.test_username,
                "password": self.test_password
            },
            timeout=10
        )
        # Endpoint returns 200 for new user with token, 400 if email exists
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        # Frontend auth.js expects access_token in response
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user_info" in data
        assert data["user_info"]["email"] == self.test_email

    def test_email_login_success(self):
        """Test POST /api/auth/login-email - Valid credentials (auth.js)"""
        # Ensure test user exists
        self.cleanup_test_user()
        requests.post(
            f"{base_url}/api/auth/register-email",
            json={
                "email": self.test_email,
                "username": self.test_username,
                "password": self.test_password
            },
            timeout=10
        )

        # Test successful login
        response = requests.post(
            f"{base_url}/api/auth/login-email",
            json={
                "email": self.test_email,
                "password": self.test_password
            },
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        # Frontend auth.js expects these fields:
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user_info" in data
        assert data["user_info"]["email"] == self.test_email

    def test_email_login_wrong_password(self):
        """Test POST /api/auth/login-email - Invalid password"""
        # Ensure test user exists
        self.cleanup_test_user()
        requests.post(
            f"{base_url}/api/auth/register-email",
            json={
                "email": self.test_email,
                "username": self.test_username,
                "password": self.test_password
            },
            timeout=10
        )

        # Test login with wrong password
        response = requests.post(
            f"{base_url}/api/auth/login-email",
            json={
                "email": self.test_email,
                "password": "wrongpassword"
            },
            timeout=10
        )
        # Frontend handles 401 (invalid credentials)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

    def test_email_register_duplicate(self):
        """Test POST /api/auth/register-email - Duplicate email (should fail)"""
        # Ensure test user exists
        self.cleanup_test_user()
        requests.post(
            f"{base_url}/api/auth/register-email",
            json={
                "email": self.test_email,
                "username": self.test_username,
                "password": self.test_password
            },
            timeout=10
        )

        # Try to register same email again
        response = requests.post(
            f"{base_url}/api/auth/register-email",
            json={
                "email": self.test_email,
                "username": "different_user",
                "password": "different_pass"
            },
            timeout=10
        )
        # Should return 400 (email already exists)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"

    def test_delete_user_cleanup(self):
        """Test DELETE /api/auth/users/{email} - Cleanup test user"""
        # Create a test user
        self.cleanup_test_user()
        requests.post(
            f"{base_url}/api/auth/register-email",
            json={
                "email": self.test_email,
                "username": self.test_username,
                "password": self.test_password
            },
            timeout=10
        )

        # Delete the user
        response = requests.delete(
            f"{base_url}/api/auth/users/{self.test_email}",
            headers={"X-Test-Mode": "true"},
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "message" in data
        assert data["email"] == self.test_email

        # Verify user is deleted (login should fail)
        login_response = requests.post(
            f"{base_url}/api/auth/login-email",
            json={
                "email": self.test_email,
                "password": self.test_password
            },
            timeout=10
        )
        # Should return 401 (user not found)
        assert login_response.status_code == 401

    @classmethod
    def teardown_class(cls):
        """Final cleanup after all tests"""
        try:
            response = requests.delete(
                f"{base_url}/api/auth/users/{cls.test_email}",
                headers={"X-Test-Mode": "true"},
                timeout=10
            )
        except:
            pass


if __name__ == "__main__":
    # Run all tests in this file
    pytest.main([__file__, "-v"])
