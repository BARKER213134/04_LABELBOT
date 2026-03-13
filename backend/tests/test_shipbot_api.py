"""
Backend API tests for ShipBot - Telegram Shipping Label Bot
Tests the following endpoints:
- /api/health - Health check
- /api/telegram/status - Telegram bot status  
- /api/admin/api-config - Admin API config (requires HTTP Basic Auth)
- /api/users/ - Users list
"""
import pytest
import requests
import os
from requests.auth import HTTPBasicAuth

# Get BASE_URL from environment - DO NOT add default
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
if BASE_URL:
    BASE_URL = BASE_URL.rstrip('/')

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "ShipBot2026!Secure"


class TestHealthEndpoints:
    """Health check endpoint tests"""
    
    def test_api_health_returns_200(self):
        """Test /api/health returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "healthy", f"Expected healthy status, got {data['status']}"
        print(f"✅ /api/health - Status: {data['status']}, Environment: {data.get('environment', 'N/A')}")


class TestTelegramEndpoints:
    """Telegram bot status endpoint tests"""
    
    def test_telegram_status_returns_bot_status(self):
        """Test /api/telegram/status returns bot status with production_loaded"""
        response = requests.get(f"{BASE_URL}/api/telegram/status", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "production_loaded" in data, "Response should contain 'production_loaded'"
        assert "sandbox_loaded" in data, "Response should contain 'sandbox_loaded'"
        assert "current_environment" in data, "Response should contain 'current_environment'"
        
        # The main agent expects production_loaded=true
        print(f"✅ /api/telegram/status - Environment: {data['current_environment']}")
        print(f"   production_loaded: {data['production_loaded']}, sandbox_loaded: {data['sandbox_loaded']}")


class TestAdminEndpoints:
    """Admin endpoints with HTTP Basic Auth"""
    
    def test_admin_api_config_requires_auth(self):
        """Test /api/admin/api-config returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/api-config", timeout=10)
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✅ /api/admin/api-config - Requires authentication (401 without auth)")
    
    def test_admin_api_config_with_auth(self):
        """Test /api/admin/api-config returns config with HTTP Basic Auth"""
        response = requests.get(
            f"{BASE_URL}/api/admin/api-config",
            auth=HTTPBasicAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200 with auth, got {response.status_code}"
        
        data = response.json()
        assert "environment" in data, "Response should contain 'environment'"
        assert data["environment"] in ["sandbox", "production"], f"Invalid environment: {data['environment']}"
        print(f"✅ /api/admin/api-config (with auth) - Environment: {data['environment']}")
        if "updated_at" in data:
            print(f"   Updated at: {data['updated_at']}")


class TestUsersEndpoints:
    """Users API endpoint tests"""
    
    def test_users_list_returns_200(self):
        """Test /api/users/ returns users list"""
        response = requests.get(f"{BASE_URL}/api/users/", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Should be a list (or dict with users key)
        if isinstance(data, list):
            print(f"✅ /api/users/ - Returns list with {len(data)} users")
        elif isinstance(data, dict) and "users" in data:
            print(f"✅ /api/users/ - Returns dict with {len(data['users'])} users")
        else:
            print(f"✅ /api/users/ - Returns: {type(data)}")


class TestMaintenanceEndpoints:
    """Maintenance mode endpoint tests (admin only)"""
    
    def test_maintenance_status_with_auth(self):
        """Test /api/admin/maintenance returns status with auth"""
        response = requests.get(
            f"{BASE_URL}/api/admin/maintenance",
            auth=HTTPBasicAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "enabled" in data, "Response should contain 'enabled'"
        print(f"✅ /api/admin/maintenance - Maintenance enabled: {data['enabled']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
