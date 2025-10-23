#!/usr/bin/env python3
import requests
import json

def test_auth_system():
    """Test the authentication system with debug endpoints"""
    base_url = "http://localhost:8000"
    
    # Test 1: Health check
    print("=== Testing Health Check ===")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return
    
    # Test 1.5: Check auth routes availability
    print("\n=== Testing Auth Route Availability ===")
    try:
        # Test the test-signup endpoint (should work without auth)
        test_response = requests.post(f"{base_url}/auth/test-signup", 
                                    json={"username": "test", "email": "test@test.com", "password": "testpass"})
        print(f"Test signup endpoint: {test_response.status_code}")
        if test_response.status_code == 200:
            print("✅ Auth router is loaded correctly")
        else:
            print(f"Auth router issue: {test_response.json()}")
    except Exception as e:
        print(f"Auth router test error: {e}")
    
    # Test 2: Login
    print("\n=== Testing Login ===")
    login_data = {
        "email": "aashij971@gmail.com",  # Use existing account
        "password": "AashiJain123@"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data)
        print(f"Login: {response.status_code}")
        
        if response.status_code == 200:
            auth_data = response.json()
            access_token = auth_data["access_token"]
            print("✅ Login successful")
            print(f"Token: {access_token[:50]}...")
            
            # Test 3: Token verification using /auth/me
            print("\n=== Testing Token Verification ===")
            headers = {"Authorization": f"Bearer {access_token}"}
            
            try:
                verify_response = requests.get(f"{base_url}/auth/me", headers=headers)
                print(f"Token verification: {verify_response.status_code}")
                
                if verify_response.status_code == 200:
                    user_data = verify_response.json()
                    print("✅ Token verification successful")
                    print(f"User ID: {user_data['id']}")
                    print(f"Email: {user_data['email']}")
                    print(f"Username: {user_data['username']}")
                    print(f"Active: {user_data['is_active']}")
                    return access_token
                else:
                    print(f"❌ Token verification failed: {verify_response.json()}")
                    
            except Exception as e:
                print(f"Token verification error: {e}")
                # Still return token since login worked
                return access_token
                
        else:
            print(f"❌ Login failed: {response.json()}")
            
    except Exception as e:
        print(f"Login error: {e}")
    
    return None

def test_upload_endpoint(token):
    """Test upload endpoint with auth"""
    if not token:
        print("No token available for upload test")
        return
    
    print("\n=== Testing Upload Start Endpoint ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    upload_data = {
        "file_id": "test-debug-123",
        "filename": "test_file.txt",
        "total_chunks": 1,
        "file_size": 100,
        "file_hash": "dummy_hash"
    }
    
    try:
        response = requests.post("http://localhost:8000/upload/start", 
                               data=upload_data, headers=headers)
        print(f"Upload start: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Upload start successful")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Upload start failed: {response.json()}")
            
    except Exception as e:
        print(f"Upload test error: {e}")

if __name__ == "__main__":
    print("🚀 Testing Authentication System Fixes")
    print("=" * 50)
    
    token = test_auth_system()
    test_upload_endpoint(token)
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")