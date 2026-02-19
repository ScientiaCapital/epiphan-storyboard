"""Example demonstrating OAuth2 flow for enterprise connectors.

This example shows how to use the OAuth providers to implement a complete
authorization flow for connecting to enterprise data sources.

Usage:
    # Set environment variables first:
    export GONG_CLIENT_ID=your_client_id
    export GONG_CLIENT_SECRET=your_client_secret

    # Run the example:
    python examples/oauth_flow_example.py
"""

import asyncio
import os
from urllib.parse import parse_qs, urlparse

from src.connectors.oauth import (
    GongOAuthProvider,
    GoogleOAuthProvider,
    LinearOAuthProvider,
    NotionOAuthProvider,
)


async def demonstrate_oauth_flow():
    """Demonstrate complete OAuth2 flow for all providers."""

    # 1. Initialize provider
    print("=" * 60)
    print("OAuth2 Flow Demonstration")
    print("=" * 60)
    print()

    provider = GongOAuthProvider()

    # 2. Build authorization URL
    redirect_uri = "https://app.example.com/oauth/callback"
    state = "random_state_12345_secure"

    # In production, you would:
    # - Generate a cryptographically secure random state
    # - Store state in session/database
    # - Redirect user to this URL

    try:
        auth_url = provider.build_authorize_url(
            redirect_uri=redirect_uri,
            state=state,
        )

        print(f"Provider: {provider.provider_name.upper()}")
        print()
        print("Step 1: Authorization URL")
        print("-" * 60)
        print(f"Redirect user to:\n{auth_url}")
        print()

        # Parse URL to show components
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)
        print("URL Components:")
        for key, value in params.items():
            print(f"  {key}: {value[0]}")
        print()

    except ValueError as e:
        print(f"Error: {e}")
        print(
            f"Please set {provider.provider_name.upper()}_CLIENT_ID and "
            f"{provider.provider_name.upper()}_CLIENT_SECRET environment variables"
        )
        return

    # 3. Simulate receiving authorization code
    print("Step 2: User Authorizes")
    print("-" * 60)
    print("User is redirected to provider's login page")
    print("User grants permissions")
    print("Provider redirects back with authorization code:")
    print(f"  {redirect_uri}?code=AUTH_CODE_12345&state={state}")
    print()

    # 4. Exchange code for tokens (simulated)
    print("Step 3: Exchange Code for Tokens")
    print("-" * 60)
    print("In production, you would:")
    print(f"  result = await provider.exchange_code(")
    print(f'      code="AUTH_CODE_12345",')
    print(f'      redirect_uri="{redirect_uri}",')
    print(f"  )")
    print()
    print("This would return:")
    print("  OAuthTokenResponse(")
    print('    access_token="...",')
    print('    refresh_token="...",')
    print("    expires_in=3600,")
    print("    expires_at=datetime(...),")
    print("  )")
    print()

    # 5. Refresh tokens (simulated)
    print("Step 4: Refresh Tokens (when expired)")
    print("-" * 60)
    print("When access token expires, refresh it:")
    print(f"  result = await provider.refresh_tokens(")
    print(f'      refresh_token="REFRESH_TOKEN_12345",')
    print(f"  )")
    print()


async def show_all_providers():
    """Show configuration for all supported providers."""

    providers = [
        GongOAuthProvider(),
        LinearOAuthProvider(),
        NotionOAuthProvider(),
        GoogleOAuthProvider(),
    ]

    print()
    print("=" * 60)
    print("All Supported OAuth2 Providers")
    print("=" * 60)
    print()

    for provider in providers:
        print(f"{provider.provider_name.upper()} OAuth Provider")
        print("-" * 60)
        print(f"  Authorization URL: {provider.authorize_url}")
        print(f"  Token URL: {provider.token_url}")
        print(f"  Required Scopes: {', '.join(provider.scopes) if provider.scopes else 'None (implicit)'}")
        print(f"  Extra Params: {provider.get_extra_authorize_params()}")
        print()
        print(f"  Environment Variables Required:")
        print(f"    - {provider.provider_name.upper()}_CLIENT_ID")
        print(f"    - {provider.provider_name.upper()}_CLIENT_SECRET")
        print()


async def demonstrate_token_expiry():
    """Demonstrate token expiry checking."""
    from datetime import datetime, timedelta, timezone

    from src.connectors.oauth import OAuthTokenResponse

    print("=" * 60)
    print("Token Expiry Demonstration")
    print("=" * 60)
    print()

    # Token expiring in 2 hours
    future_expiry = datetime.now(timezone.utc) + timedelta(hours=2)
    token = OAuthTokenResponse(
        access_token="test_token",
        expires_at=future_expiry,
    )
    print(f"Token expiring at: {future_expiry}")
    print(f"Is expired? {token.is_expired()}")
    print()

    # Token expiring in 30 seconds (within 60 second buffer)
    soon_expiry = datetime.now(timezone.utc) + timedelta(seconds=30)
    token = OAuthTokenResponse(
        access_token="test_token",
        expires_at=soon_expiry,
    )
    print(f"Token expiring at: {soon_expiry} (in 30 seconds)")
    print(f"Is expired? {token.is_expired()} (True due to 60s buffer)")
    print()

    # Expired token
    past_expiry = datetime.now(timezone.utc) - timedelta(hours=1)
    token = OAuthTokenResponse(
        access_token="test_token",
        expires_at=past_expiry,
    )
    print(f"Token expired at: {past_expiry}")
    print(f"Is expired? {token.is_expired()}")
    print()


async def main():
    """Run all demonstrations."""
    await demonstrate_oauth_flow()
    await show_all_providers()
    await demonstrate_token_expiry()


if __name__ == "__main__":
    asyncio.run(main())
