import httpx

def check_connection_health(api_url, timeout=30.0):
    try:
        print(f"🔍 Checking health at: {api_url}/health")
        # 禁用代理，直接连接
        response = httpx.get(f"{api_url}/health", timeout=timeout)
        print(f"📡 Response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Response data: {data}")
            if data.get("status") == "healthy" and data.get("indexer_ready"):
                print("✅ Connection health check passed")
                return True
            elif data.get("status") == "healthy" and not data.get("indexer_ready"):
                print("❌ API server is not ready: ", data)
                return "not_ready"
            else:
                print("❌ API server unhealthy: ", data)
        else:
            print(f"❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: API server not accessible at {api_url}")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
    return False

if __name__ == "__main__":
    api_url = "http://localhost:8003"
    check_connection_health(api_url)
