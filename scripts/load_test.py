import asyncio
import time
import httpx
import json
from typing import Dict, Any

class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def test_endpoint(self, endpoint: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            if payload:
                response = await self.client.post(url, json=payload)
            else:
                response = await self.client.get(url)

            response_time = time.time() - start_time

            return {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": response_time,
                "success": response.is_success,
                "response_size": len(response.content),
                "data": response.json() if response.is_success else None
            }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "error": str(e),
                "response_time": time.time() - start_time,
                "success": False
            }

    async def run_load_test(self, concurrent_requests: int = 10, duration: int = 60):
        print(f"Starting load test with {concurrent_requests} concurrent requests for {duration} seconds")

        start_time = time.time()
        results = []
        request_count = 0

        async def make_requests():
            nonlocal request_count
            while time.time() - start_time < duration:
                tasks = []

                # Generate different types of requests
                for _ in range(concurrent_requests):
                    endpoint = asyncio.run(self.get_random_endpoint())
                    task = asyncio.create_task(self.test_endpoint(*endpoint))
                    tasks.append(task)

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend([r for r in batch_results if not isinstance(r, Exception)])
                request_count += len(tasks)

                await asyncio.sleep(1)

        await make_requests()

        total_time = time.time() - start_time
        self.print_results(results, total_time, request_count)

    async def get_random_endpoint(self):
        import random

        endpoints = [
            ("/generate/users", {"count": 100, "stream": False}),
            ("/generate/products", {"count": 50, "stream": False}),
            ("/generate/interactions", {"count": 200, "stream": False}),
            ("/health", None),
            ("/stream/status", None)
        ]

        return random.choice(endpoints)

    def print_results(self, results, total_time, request_count):
        successful_requests = [r for r in results if r.get("success", False)]
        failed_requests = [r for r in results if not r.get("success", False)]

        print(f"\nLoad Test Results:")
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Total Requests: {request_count}")
        print(f"Requests/Second: {request_count / total_time:.2f}")
        print(f"Successful Requests: {len(successful_requests)}")
        print(f"Failed Requests: {len(failed_requests)}")
        print(f"Success Rate: {len(successful_requests) / len(results) * 100:.2f}%")

        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            print(f"Average Response Time: {sum(response_times) / len(response_times):.3f}s")
            print(f"Min Response Time: {min(response_times):.3f}s")
            print(f"Max Response Time: {max(response_times):.3f}s")

        if failed_requests:
            print(f"\nFailed Requests:")
            for result in failed_requests[:5]:
                print(f"  {result['endpoint']}: {result.get('error', 'Unknown error')}")

    async def benchmark_generation(self):
        print("\nRunning generation benchmark...")

        test_cases = [
            ("users", 1000),
            ("products", 500),
            ("interactions", 2000),
            ("interactions", 10000)
        ]

        for data_type, count in test_cases:
            payload = {"count": count, "stream": False}
            result = await self.test_endpoint(f"/generate/{data_type}", payload)

            if result["success"]:
                rate = count / result["response_time"]
                print(f"{data_type.capitalize()} - {count} items: {result['response_time']:.2f}s ({rate:.0f} items/s)")
            else:
                print(f"{data_type.capitalize()} - {count} items: FAILED")

    async def close(self):
        await self.client.aclose()

async def main():
    tester = LoadTester()

    try:
        # Run benchmark tests
        await tester.benchmark_generation()

        # Run load test
        await tester.run_load_test(concurrent_requests=20, duration=30)

    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())