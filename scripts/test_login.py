#!/usr/bin/env python3
"""
Test login endpoint directly

Usage:
    python scripts/test_login.py <email> <password>
"""

import requests
import json

def test_login(email, password):
    """Test login endpoint"""
    base_url = "http://localhost:8000"
    endpoint = "/api/auth/login-email"

    print(f"🔐 Testing login for: {email}")
    print(f"🌐 Endpoint: {base_url}{endpoint}")
    print()

    try:
        response = requests.post(
            f"{base_url}{endpoint}",
            json={
                "email": "qi.zhu.ckc@gmail.com",
                "password": "123zhuqi"
            },
            timeout=10
        )

        print(f"📡 Status Code: {response.status_code}")
        print(f"📄 Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print()

        print(f"📦 Response Body:")
        try:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(response.text)

        print()

        if response.status_code == 200:
            print("✅ Login SUCCESSFUL!")
            if 'access_token' in data:
                print(f"🔑 Token: {data['access_token'][:50]}...")
            if 'user_info' in data:
                print(f"👤 User: {data['user_info']}")
        elif response.status_code == 401:
            print("❌ Login FAILED: Invalid credentials")
        else:
            print(f"⚠️  Unexpected response code: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend service!")
        print("💡 Make sure backend is running on http://localhost:8000")
        print()
        print("Start backend with:")
        print("  cd backend")
        print("  uvicorn app.main:app --reload --port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python scripts/test_login.py <email> <password>")
        print("Example: python scripts/test_login.py qi.zhu.ckc@gmail.com newpass123")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    test_login(email, password)
