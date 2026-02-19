# OAuth2 Authentication Framework

Enterprise-grade OAuth2 providers for data connector authentication.

## Overview

This module provides a unified OAuth2 framework for authenticating with enterprise data sources. It handles the complete OAuth2 authorization code flow, token management, and refresh logic.

## Supported Providers

| Provider | Use Case | Special Features |
|----------|----------|------------------|
| **Gong** | Sales call transcripts & insights | 3 scopes (calls, users) |
| **Linear** | Issue tracking & product management | Simple read scope |
| **Notion** | Knowledge base & documentation | Basic auth, implicit scope |
| **Google** | Google Docs & Drive access | Offline access, forced consent |

## Quick Start

### 1. Set Environment Variables

```bash
# For Gong
export GONG_CLIENT_ID=your_client_id
export GONG_CLIENT_SECRET=your_client_secret

# For Linear
export LINEAR_CLIENT_ID=your_client_id
export LINEAR_CLIENT_SECRET=your_client_secret

# For Notion
export NOTION_CLIENT_ID=your_client_id
export NOTION_CLIENT_SECRET=your_client_secret

# For Google
export GOOGLE_CLIENT_ID=your_client_id
export GOOGLE_CLIENT_SECRET=your_client_secret
```

### 2. Basic Usage

```python
from src.connectors.oauth import GongOAuthProvider

# Initialize provider
provider = GongOAuthProvider()

# Step 1: Build authorization URL
auth_url = provider.build_authorize_url(
    redirect_uri="https://app.example.com/oauth/callback",
    state="random_secure_state_12345",
)

# Redirect user to auth_url
# User authorizes and is redirected back with code

# Step 2: Exchange authorization code for tokens
result = await provider.exchange_code(
    code="authorization_code_from_callback",
    redirect_uri="https://app.example.com/oauth/callback",
)

# Access tokens
access_token = result.access_token
refresh_token = result.refresh_token
expires_at = result.expires_at

# Step 3: Refresh tokens when expired
if result.is_expired():
    result = await provider.refresh_tokens(
        refresh_token=refresh_token,
    )
```

## Architecture

### Base Classes

**OAuthProvider** - Abstract base class for all providers
- `authorize_url` - Authorization endpoint
- `token_url` - Token endpoint
- `scopes` - Required OAuth scopes
- `build_authorize_url()` - Generate auth URL with params
- `exchange_code()` - Exchange code for tokens
- `refresh_tokens()` - Refresh access token

**OAuthTokenResponse** - Token response data
- `access_token` - Access token string
- `refresh_token` - Refresh token (optional)
- `expires_in` - Seconds until expiry
- `expires_at` - Absolute expiry datetime
- `is_expired()` - Check if token needs refresh (60s buffer)

### Provider Details

#### Gong OAuth Provider
```python
from src.connectors.oauth import GongOAuthProvider

provider = GongOAuthProvider()
# Authorize URL: https://app.gong.io/oauth2/authorize
# Token URL: https://app.gong.io/oauth2/generate-customer-token
# Scopes:
#   - api:calls:read:transcript
#   - api:calls:read:extensive
#   - api:users:read
```

#### Linear OAuth Provider
```python
from src.connectors.oauth import LinearOAuthProvider

provider = LinearOAuthProvider()
# Authorize URL: https://linear.app/oauth/authorize
# Token URL: https://api.linear.app/oauth/token
# Scopes: read
```

#### Notion OAuth Provider
```python
from src.connectors.oauth import NotionOAuthProvider

provider = NotionOAuthProvider()
# Authorize URL: https://api.notion.com/v1/oauth/authorize
# Token URL: https://api.notion.com/v1/oauth/token
# Scopes: [] (implicit)
# Extra params: owner=user
# Auth: Basic auth (base64 client_id:client_secret)
```

#### Google OAuth Provider
```python
from src.connectors.oauth import GoogleOAuthProvider

provider = GoogleOAuthProvider()
# Authorize URL: https://accounts.google.com/o/oauth2/v2/auth
# Token URL: https://oauth2.googleapis.com/token
# Scopes:
#   - https://www.googleapis.com/auth/documents.readonly
#   - https://www.googleapis.com/auth/drive.readonly
# Extra params:
#   - access_type=offline (request refresh token)
#   - prompt=consent (force consent screen)
```

## Token Management

### Expiry Checking

Tokens are checked with a 60-second buffer to prevent race conditions:

```python
from datetime import datetime, timedelta, timezone
from src.connectors.oauth import OAuthTokenResponse

# Token expiring in 2 hours
expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
token = OAuthTokenResponse(access_token="...", expires_at=expires_at)
token.is_expired()  # False

# Token expiring in 30 seconds
expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
token = OAuthTokenResponse(access_token="...", expires_at=expires_at)
token.is_expired()  # True (60s buffer)
```

### Automatic Refresh

```python
async def get_valid_token(provider, current_token, refresh_token):
    """Get a valid access token, refreshing if needed."""
    if current_token.is_expired():
        current_token = await provider.refresh_tokens(refresh_token)
    return current_token.access_token
```

## Security Features

### Request Timeouts

All HTTP requests have a 30-second timeout to prevent hanging:

```python
# Automatic in exchange_code() and refresh_tokens()
response = await client.post(
    self.token_url,
    data=data,
    headers=headers,
    timeout=30.0,  # 30 second timeout
)
```

### State Parameter Validation

Always validate the state parameter to prevent CSRF attacks:

```python
import secrets

# Generate secure state
state = secrets.token_urlsafe(32)

# Store in session/database
session['oauth_state'] = state

# Build auth URL
auth_url = provider.build_authorize_url(
    redirect_uri=redirect_uri,
    state=state,
)

# On callback, validate state
if request.args.get('state') != session.get('oauth_state'):
    raise ValueError("Invalid state parameter")
```

### Environment Variable Isolation

Client credentials are never hardcoded:

```python
# Automatic environment variable lookup
provider.get_client_id()      # Reads GONG_CLIENT_ID
provider.get_client_secret()  # Reads GONG_CLIENT_SECRET

# Raises ValueError if missing
```

## Error Handling

```python
import httpx

try:
    result = await provider.exchange_code(
        code=authorization_code,
        redirect_uri=redirect_uri,
    )
except ValueError as e:
    # Missing environment variables
    print(f"Configuration error: {e}")
except httpx.HTTPStatusError as e:
    # OAuth error (invalid code, expired code, etc.)
    print(f"OAuth error: {e.response.status_code}")
    print(f"Details: {e.response.json()}")
except httpx.TimeoutException:
    # Request timeout
    print("Request timed out")
```

## Testing

### Test Coverage

- 40 comprehensive tests covering all providers
- 100% code coverage on OAuth module
- Tests use `respx` for HTTP mocking
- All edge cases covered

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run OAuth tests only
python3 -m pytest tests/connectors/test_oauth.py -v

# Run with coverage
python3 -m pytest tests/connectors/test_oauth.py --cov=src/connectors/oauth
```

### Example Test

```python
import pytest
import respx
import httpx
from src.connectors.oauth import GongOAuthProvider

@pytest.mark.asyncio
@respx.mock
async def test_exchange_code(monkeypatch):
    # Setup
    monkeypatch.setenv("GONG_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GONG_CLIENT_SECRET", "test_client_secret")

    provider = GongOAuthProvider()

    # Mock token endpoint
    mock_response = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
    }
    respx.post(provider.token_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Test
    result = await provider.exchange_code(
        code="test_code",
        redirect_uri="https://app.example.com/callback",
    )

    # Verify
    assert result.access_token == "test_access_token"
    assert result.refresh_token == "test_refresh_token"
```

## Code Statistics

- Base framework: 172 lines
- 4 provider implementations: 138 lines total
- Tests: 483 lines (40 tests)
- Example: 193 lines
- Total: ~986 lines

## Provider-Specific Notes

### Notion OAuth

Notion requires Basic authentication for token exchange:

```python
# Automatic in NotionOAuthProvider
def _get_token_request_headers(self) -> dict:
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded}",
    }
```

### Google OAuth

Google requires specific parameters for offline access:

```python
# Automatic in GoogleOAuthProvider
def get_extra_authorize_params(self) -> dict:
    return {
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",       # Force consent screen
    }
```

## Example Application

See `examples/oauth_flow_example.py` for a complete demonstration:

```bash
# Set environment variables
export GONG_CLIENT_ID=your_client_id
export GONG_CLIENT_SECRET=your_client_secret

# Run example
PYTHONPATH=. python3 examples/oauth_flow_example.py
```

## Next Steps

1. **Token Storage** - Implement secure token storage in Supabase
2. **FastAPI Integration** - Add OAuth callback endpoints
3. **Token Refresh Worker** - Background task to refresh expiring tokens
4. **Multi-tenant Support** - Per-organization OAuth credentials
5. **Webhook Support** - Real-time data sync via webhooks

## References

- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [Gong API Documentation](https://help.gong.io/docs/api-overview)
- [Linear API Documentation](https://developers.linear.app/docs/graphql/working-with-the-graphql-api)
- [Notion API Documentation](https://developers.notion.com/docs/authorization)
- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
