"""Test async agent concurrency."""

import asyncio
import time

from agents import Agent, Runner


async def test_async_concurrency():
    """Test that async Runner.run works with asyncio.gather."""

    # Create a simple test agent
    agent = Agent(
        name="TestAgent",
        instructions="You are a helpful assistant. Just say 'Hello {name}!' where name is from the input.",
        model="gpt-4o-mini",
    )

    prompts = [f"Name is User{i}" for i in range(5)]

    # Test sequential
    print("Testing sequential calls...")
    start = time.time()
    for prompt in prompts:
        result = await Runner.run(agent, prompt)
        print(f"  Result: {result.final_output[:50]}...")
    sequential_time = time.time() - start
    print(f"Sequential time: {sequential_time:.2f}s")

    # Test concurrent
    print("\nTesting concurrent calls...")
    start = time.time()

    async def run_one(prompt: str):
        result = await Runner.run(agent, prompt)
        return result.final_output

    results = await asyncio.gather(*[run_one(p) for p in prompts])
    concurrent_time = time.time() - start

    for r in results:
        print(f"  Result: {r[:50]}...")
    print(f"Concurrent time: {concurrent_time:.2f}s")

    print(f"\nSpeedup: {sequential_time / concurrent_time:.2f}x")


if __name__ == "__main__":
    asyncio.run(test_async_concurrency())
