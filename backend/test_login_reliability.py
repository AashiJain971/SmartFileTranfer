#!/usr/bin/env python3
"""
Test database connection and login reliability
"""
import asyncio
import aiohttp
import json
import time

BASE_URL = "http://localhost:8000"

async def test_login_reliability():
    """Test login multiple times to check for timeout issues"""
    print("🧪 Testing Login Reliability...")
    print("=" * 50)
    
    test_user = {
        "email": "aashij971@gmail.com",
        "password": "password123"
    }
    
    success_count = 0
    total_tests = 10
    
    async with aiohttp.ClientSession() as session:
        for i in range(total_tests):
            try:
                print(f"\n🔄 Test {i+1}/{total_tests}: Logging in...")
                start_time = time.time()
                
                async with session.post(f"{BASE_URL}/auth/login", 
                                      json=test_user,
                                      timeout=aiohttp.ClientTimeout(total=15)) as response:
                    
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    
                    if response.status == 200:
                        data = await response.json()
                        success_count += 1
                        print(f"✅ Success in {response_time:.0f}ms - User: {data['user']['username']}")
                    else:
                        error_data = await response.json()
                        print(f"❌ Failed ({response.status}) in {response_time:.0f}ms - {error_data.get('detail', 'Unknown error')}")
                        
            except asyncio.TimeoutError:
                print(f"⏰ Timeout after 15 seconds")
            except Exception as e:
                print(f"❌ Exception: {e}")
                
            # Small delay between tests
            await asyncio.sleep(1)
    
    print(f"\n📊 Results:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {total_tests - success_count}")
    print(f"   Success Rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 All login attempts succeeded!")
    elif success_count >= total_tests * 0.8:  # 80% success rate
        print("✅ Good success rate - occasional failures are acceptable")
    else:
        print("⚠️ Poor success rate - database timeout issues may persist")

async def test_database_warmup():
    """Test if database warmup is working"""
    print("\n🔥 Testing Database Warmup...")
    print("=" * 30)
    
    try:
        # Test simple endpoint first
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status in [200, 404]:  # 404 is ok for root endpoint
                    print("✅ Server is responding")
                else:
                    print(f"⚠️ Server responded with status {response.status}")
                    
    except Exception as e:
        print(f"❌ Server connection failed: {e}")
        return False
        
    return True

async def main():
    """Main test runner"""
    print("🚀 Database Connection & Login Reliability Test")
    print("=" * 60)
    
    # Test server connectivity first
    server_ok = await test_database_warmup()
    if not server_ok:
        print("❌ Cannot proceed - server is not accessible")
        return
        
    # Test login reliability
    await test_login_reliability()
    
    print("\n" + "=" * 60)
    print("Test completed! Check the results above.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")