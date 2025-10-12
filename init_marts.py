#!/usr/bin/env python3
import os
import requests
import time
from dotenv import load_dotenv

# Check if PyJWT is installed
try:
    import jwt
except ImportError:
    print("❌ Error: PyJWT library is not installed")
    print("Please install it using one of the following methods:")
    print("  pip install PyJWT")
    print("  pip3 install PyJWT")
    print("  conda install -c conda-forge pyjwt")
    print("  # Or add 'PyJWT' to your requirements.txt file")
    exit(1)

# Load environment variables from .env file
load_dotenv()

# Configuration
KERNEL_URL = "http://localhost:8001"  # Using the first kernel's mapped port (8001 is mapped to 8000 in the container)
JWT_TOKEN = os.getenv("KERNEL1_TOKEN")  # Token with kernel role

if not JWT_TOKEN:
    print("❌ Error: KERNEL1_TOKEN environment variable is not set")
    print("Please set the KERNEL1_TOKEN in your .env file or export it")
    exit(1)

# Mart definitions
MARTS = [
    {
        "mart_id": "photos",
        "parent": "photos-parent",
        "children": ["photos-child-a", "photos-child-b"]
    },
    {
        "mart_id": "research",
        "parent": "research-parent",
        "children": ["research-child-a", "research-child-b"]
    },
    {
        "mart_id": "clients",
        "parent": "clients-parent",
        "children": ["clients-child-a", "clients-child-b"]
    }
]

def wait_for_service(url, timeout=60):
    """Wait for a service to become available with detailed feedback."""
    start_time = time.time()
    last_status = None
    
    print(f"⏳ Waiting for service at {url}...")
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Service at {url} is ready!")
                return True
            else:
                status = f"HTTP {response.status_code}"
                if status != last_status:
                    print(f"   Service returned {status}, waiting...")
                    last_status = status
        except requests.exceptions.ConnectionError as e:
            if "Connection refused" in str(e) and last_status != "connection_refused":
                print("   Service not accepting connections yet...")
                last_status = "connection_refused"
        except requests.exceptions.RequestException as e:
            if str(e) != last_status:
                print(f"   Error: {e}")
                last_status = str(e)
        
        # Show a progress indicator every 5 seconds
        elapsed = int(time.time() - start_time)
        if elapsed > 0 and elapsed % 5 == 0 and elapsed != int(time.time() - start_time - 1):
            print(f"   Waiting... ({elapsed}/{timeout} seconds elapsed)")
        
        time.sleep(1)
    
    print(f"❌ Timed out waiting for service at {url} after {timeout} seconds")
    return False

def declare_mart(mart):
    """Declare a mart with its parent and children."""
    # Print debug info about the token
    print(f"\n🔑 Using JWT token (first 20 chars): {JWT_TOKEN[:20]}...")
    
    # Verify the token format
    if not JWT_TOKEN or len(JWT_TOKEN) < 30:  # JWT tokens are typically longer than 30 chars
        print("❌ Invalid JWT token format (too short or empty)")
        return False
    
    # Decode the token to verify its contents
    try:
        import jwt
        decoded = jwt.decode(JWT_TOKEN, options={"verify_signature": False})
        print(f"🔍 Decoded token: {decoded}")
    except Exception as e:
        print(f"⚠ Could not decode JWT token: {e}")
        
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print(f"\n🔧 Declaring mart: {mart['mart_id']}")
    print(f"   Parent: {mart['parent']}")
    print(f"   Children: {', '.join(mart['children'])}")
    
    # Prepare the request data according to the MartDecl model
    data = {
        "mart_id": mart["mart_id"],
        "parent": mart["parent"],
        "children": mart["children"]
    }
    
    try:
        # Print the full request for debugging
        import json
        print(f"\n📤 Sending request to {KERNEL_URL}/declare_mart")
        print(f"   Headers: {json.dumps({k: '...' if k.lower() == 'authorization' else v for k, v in headers.items()}, indent=4)}")
        print(f"   Data: {json.dumps(data, indent=4)}")
        
        # First, try with the standard endpoint
        response = requests.post(
            f"{KERNEL_URL}/declare_mart",
            json=data,
            headers=headers,
            timeout=10
        )
        
        # Print response details
        print(f"\n📥 Response from server:")
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"   Content: {response.text}")
        
        response.raise_for_status()
        print(f"✅ Successfully declared mart: {mart['mart_id']}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to declare mart {mart['mart_id']}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.status_code} - {e.response.text}")
        return False

def main():
    print("🚀 Initializing Bloom Network Marts...")
    
    # Print environment info for debugging
    print("\n🔍 Environment Info:")
    print(f"   Python version: {os.sys.version}")
    print(f"   Working directory: {os.getcwd()}")
    print(f"   Kernel URL: {KERNEL_URL}")
    
    # Verify .env file exists and is readable
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    print(f"   .env file: {env_path}")
    if not os.path.exists(env_path):
        print(f"❌ Error: .env file not found at {env_path}")
        return
    
    # Read the .env file to verify the token is there
    with open(env_path, 'r') as f:
        env_content = f.read()
        print(f"   .env contains KERNEL1_TOKEN: {'KERNEL1_TOKEN=' in env_content}")
    
    # Print the JWT token for debugging (first 10 chars)
    print(f"🔑 Using JWT token from environment: {JWT_TOKEN[:10]}...")
    
    # Test the token by making a request to the health endpoint
    print("\n🔍 Testing JWT token with health endpoint...")
    try:
        test_headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
        response = requests.get(f"{KERNEL_URL}/health", headers=test_headers, timeout=5)
        print(f"   Health check status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Health check response: {response.text}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
    
    # Wait for kernel to be ready
    print("\n⏳ Waiting for kernel to be ready...")
    if not wait_for_service(f"{KERNEL_URL}/health"):
        print("❌ Kernel is not ready. Exiting.")
        return
    
    print("✅ Kernel is ready. Declaring marts...")
    
    # First, try to get the registry to see current state
    try:
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}",
            "Accept": "application/json"
        }
        response = requests.get(f"{KERNEL_URL}/registry", headers=headers, timeout=10)
        response.raise_for_status()
        registry = response.json()
        print(f"📊 Current registry status: {len(registry.get('marts', {}))} marts, {len(registry.get('nodes', {}))} nodes")
    except Exception as e:
        print(f"⚠ Could not fetch registry: {e}")
    
    # Declare each mart
    success_count = 0
    for mart in MARTS:
        if declare_mart(mart):
            success_count += 1
    
    # Print summary
    print(f"\n✨ Initialization complete!")
    print(f"   Successfully declared: {success_count}/{len(MARTS)} marts")
    
    if success_count < len(MARTS):
        print("\n⚠ Some marts could not be declared. Please check the logs above.")
    else:
        print("\n✅ All marts declared successfully!")

if __name__ == "__main__":
    main()
