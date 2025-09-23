"""Test script for frontend API endpoints."""

import asyncio
import aiohttp
import json


async def test_frontend_api():
    """Test the frontend API endpoints."""
    base_url = "http://localhost:8002"
    
    async with aiohttp.ClientSession() as session:
        # Test getting system status
        print("=== Testing GET /api/status ===")
        try:
            async with session.get(f"{base_url}/api/status") as response:
                status_data = await response.json()
                print(f"Status: {status_data['system_status']}")
                print(f"Agents: {status_data['agents']}")
                if 'system_parameters' in status_data:
                    print(f"System parameters: {list(status_data['system_parameters'].keys())}")
        except Exception as e:
            print(f"Error getting status: {e}")
        
        # Test getting system parameters directly
        print("\n=== Testing GET /api/system_parameters ===")
        try:
            async with session.get(f"{base_url}/api/system_parameters") as response:
                params_data = await response.json()
                print(f"Parameters status: {params_data['status']}")
                if params_data['status'] == 'success':
                    print(f"Parameters: {params_data['parameters']}")
        except Exception as e:
            print(f"Error getting system parameters: {e}")
        
        # Test setting a system parameter
        print("\n=== Testing POST /api/system_parameters ===")
        try:
            parameter_update = {
                "parameter_name": "max_history_length",
                "parameter_value": "12"
            }
            async with session.post(f"{base_url}/api/system_parameters", 
                                  json=parameter_update) as response:
                result = await response.json()
                print(f"Set parameter result: {result}")
        except Exception as e:
            print(f"Error setting parameter: {e}")
        
        # Test getting system parameters after setting one
        print("\n=== Testing GET /api/system_parameters after setting ===")
        try:
            async with session.get(f"{base_url}/api/system_parameters") as response:
                params_data = await response.json()
                print(f"Parameters status: {params_data['status']}")
                if params_data['status'] == 'success':
                    print(f"Parameters: {params_data['parameters']}")
        except Exception as e:
            print(f"Error getting system parameters: {e}")


if __name__ == "__main__":
    asyncio.run(test_frontend_api())