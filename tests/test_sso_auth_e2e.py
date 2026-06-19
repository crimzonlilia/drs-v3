import sys
import os
import json
import httpx

# Add workspace root to python path
sys.path.append(os.path.abspath("."))

def test_sso_flow():
    print("=== Starting E2E Google/Mock SSO Integration Test ===")
    
    # We will test against the local running Uvicorn server on port 8000
    base_url = "http://127.0.0.1:8000"
    
    # 1. Fetch the login URL
    print("\n1. Requesting Google login redirect URL...")
    r = httpx.get(f"{base_url}/api/auth/google/login")
    assert r.status_code == 200, f"Failed: {r.status_code}"
    data = r.json()
    assert "url" in data, "No redirect URL in response"
    login_url = data["url"]
    print(f"  OK - Login URL: {login_url}")
    
    # 2. If it is a Mock SSO URL, retrieve the HTML page to confirm it works
    if "/api/auth/mock-sso/google" in login_url:
        print("\n2. Fetching Mock SSO HTML Consent Page...")
        # Extract query parameters
        import urllib.parse
        parsed = urllib.parse.urlparse(login_url)
        params = urllib.parse.parse_qs(parsed.query)
        redirect_uri = params.get("redirect_uri", [""])[0]
        
        r = httpx.get(f"{base_url}/api/auth/mock-sso/google", params={"redirect_uri": redirect_uri})
        assert r.status_code == 200, f"Failed to retrieve HTML consent: {r.status_code}"
        assert "text/html" in r.headers.get("content-type", ""), "Response is not HTML"
        assert "Mock Google User" in r.text, "Consent page missing mock user info"
        print("  OK - Mock SSO HTML Consent Page is active and structured correctly.")
    else:
        print("\n2. Real Google Client ID configured; skipping consent page check.")
        
    # 3. Simulate callback exchange with mock code
    print("\n3. Exchanging mock auth code for JWT Access Token...")
    callback_payload = {"code": "mock_google_123"}
    r = httpx.post(f"{base_url}/api/auth/google/callback", json=callback_payload)
    assert r.status_code == 200, f"Failed code exchange: {r.text}"
    token_data = r.json()
    assert "access_token" in token_data, "No access token returned"
    assert token_data["token_type"] == "bearer", "Incorrect token type"
    token = token_data["access_token"]
    print("  OK - Successfully exchanged auth code for JWT token.")
    
    # 4. Fetch the authenticated user's details
    print("\n4. Verifying token on /me endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    r = httpx.get(f"{base_url}/api/auth/me", headers=headers)
    assert r.status_code == 200, f"Failed to retrieve user: {r.text}"
    user_data = r.json()
    assert user_data["username"] == "mock_google_user", f"Unexpected username: {user_data['username']}"
    assert user_data["email"] == "mock.google.user@gmail.com", f"Unexpected email: {user_data['email']}"
    print("  OK - Correctly registered and authenticated Mock Google user profile.")
    
    print("\n=== E2E Google/Mock SSO Integration Test PASSED successfully! ===")

if __name__ == "__main__":
    test_sso_flow()
