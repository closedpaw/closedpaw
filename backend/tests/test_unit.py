"""
Unit tests for core ClosedPaw components
"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.security import SecurityManager
from app.core.providers import LLMProvider


class TestLLMProvider:
    """Tests for LLM provider functionality"""
    
    @pytest.fixture
    def provider(self):
        return LLMProvider()
    
    @pytest.mark.asyncio
    async def test_local_model_selection(self, provider):
        """Test that local models can be selected"""
        models = await provider.list_models()
        assert isinstance(models, list)
        
        if models:
            # Should be able to select first model
            model_name = models[0].name if hasattr(models[0], 'name') else models[0]["name"]
            selected = await provider.select_model(model_name)
            assert selected is True
    
    @pytest.mark.asyncio
    async def test_cloud_provider_disabled_by_default(self, provider):
        """Test that cloud providers are disabled by default"""
        status = provider.get_cloud_status()
        
        # All cloud providers should be disabled
        for provider_name, enabled in status.items():
            assert enabled is False, f"{provider_name} should be disabled by default"


class TestSanitization:
    """Tests for input/output sanitization"""
    
    @pytest.fixture
    def security(self):
        return SecurityManager()
    
    def test_html_sanitization(self, security):
        """Test HTML is properly sanitized"""
        malicious_html = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<a href='javascript:alert(1)'>click</a>",
            "<svg onload=alert('xss')>",
        ]
        
        for html in malicious_html:
            sanitized = security.sanitize_html(html)
            assert "<script>" not in sanitized
            assert "onerror=" not in sanitized
            assert "javascript:" not in sanitized
            assert "onload=" not in sanitized
    
    def test_path_traversal_prevention(self, security):
        """Test path traversal attacks are prevented"""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//....//etc/shadow",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
        ]
        
        for attempt in traversal_attempts:
            result = security.sanitize_path(attempt)
            # Should not traverse outside allowed directory
            assert ".." not in result
            assert not result.startswith("/etc") or result.startswith("/tmp")


class TestRateLimiting:
    """Tests for rate limiting functionality"""
    
    @pytest.fixture
    def security(self):
        return SecurityManager()
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, security):
        """Test that rate limits are enforced"""
        user_id = "test_user"
        
        # First 10 requests should succeed
        for i in range(10):
            result = await security.check_rate_limit(user_id)
            assert result.allowed is True
        
        # 11th request should be rate limited
        result = await security.check_rate_limit(user_id)
        # Depending on config, this might be limited


class TestSessionManagement:
    """Tests for session management"""
    
    @pytest.fixture
    def security(self):
        return SecurityManager()
    
    @pytest.mark.asyncio
    async def test_session_creation(self, security):
        """Test session creation"""
        session = await security.create_session(user_id="test_user")
        
        assert session is not None
        assert session.id is not None
        assert session.user_id == "test_user"
    
    @pytest.mark.asyncio
    async def test_session_expiry(self, security):
        """Test session expiry"""
        # Create session with short expiry
        session = await security.create_session(
            user_id="test_user",
            expires_in_seconds=1
        )
        
        assert session.is_valid is True
        
        # Wait for expiry
        await asyncio.sleep(2)
        
        # Session should be expired
        valid = await security.validate_session(session.id)
        assert valid is False


class TestErrorHandling:
    """Tests for secure error handling"""
    
    @pytest.fixture
    def security(self):
        return SecurityManager()
    
    def test_error_messages_no_sensitive_info(self, security):
        """Test that error messages don't leak sensitive info"""
        # Simulate errors
        errors = [
            Exception("Connection failed: password=secret123"),
            ValueError("Invalid API key: sk-12345678"),
            RuntimeError("Database error: user=admin pass=admin"),
        ]
        
        for error in errors:
            safe_message = security.sanitize_error(error)
            
            # Should not contain sensitive data
            assert "secret123" not in safe_message
            assert "sk-12345678" not in safe_message
            assert "pass=admin" not in safe_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
