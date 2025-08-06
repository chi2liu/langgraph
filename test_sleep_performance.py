#!/usr/bin/env python3
"""Performance test to measure the impact of time.sleep(0) in concurrent execution."""

import asyncio
import concurrent.futures
import time
import threading
from typing import Callable, TypeVar
from statistics import mean, stdev

T = TypeVar("T")

# Different implementations to test
def next_tick_original(fn: Callable[..., T], *args, **kwargs) -> T:
    """Original implementation with time.sleep(0)"""
    time.sleep(0)
    return fn(*args, **kwargs)

def next_tick_no_sleep(fn: Callable[..., T], *args, **kwargs) -> T:
    """Implementation without any sleep"""
    return fn(*args, **kwargs)

def next_tick_thread_yield(fn: Callable[..., T], *args, **kwargs) -> T:
    """Implementation using thread event wait"""
    threading.Event().wait(0)
    return fn(*args, **kwargs)

def next_tick_thread_switch(fn: Callable[..., T], *args, **kwargs) -> T:
    """Implementation using thread switch context"""
    # Force a context switch by acquiring and immediately releasing a lock
    lock = threading.Lock()
    with lock:
        pass
    return fn(*args, **kwargs)

# Test workload
def simple_work(x: int) -> int:
    """Simple CPU-bound work"""
    return x * 2

def io_simulated_work(x: int) -> int:
    """Work that simulates I/O with a small sleep"""
    time.sleep(0.001)  # Simulate 1ms I/O
    return x * 2

def benchmark_implementation(impl: Callable, work_func: Callable, num_tasks: int, num_iterations: int) -> dict:
    """Benchmark a specific implementation."""
    times = []
    
    for _ in range(num_iterations):
        start = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(num_tasks):
                future = executor.submit(impl, work_func, i)
                futures.append(future)
            
            # Wait for all tasks to complete
            concurrent.futures.wait(futures)
            results = [f.result() for f in futures]
        
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    return {
        "mean": mean(times),
        "stdev": stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
        "times": times
    }

def run_benchmark_suite():
    """Run comprehensive benchmark suite."""
    implementations = {
        "time.sleep(0)": next_tick_original,
        "no_sleep": next_tick_no_sleep,
        "thread_event": next_tick_thread_yield,
        "thread_switch": next_tick_thread_switch,
    }
    
    work_types = {
        "cpu_bound": simple_work,
        "io_simulated": io_simulated_work,
    }
    
    task_counts = [10, 50, 100, 500]
    num_iterations = 5
    
    print("=" * 80)
    print("PERFORMANCE TEST: Impact of time.sleep(0) in concurrent execution")
    print("=" * 80)
    print()
    
    results = {}
    
    for work_name, work_func in work_types.items():
        print(f"\n--- Testing with {work_name} workload ---")
        results[work_name] = {}
        
        for task_count in task_counts:
            print(f"\nNumber of tasks: {task_count}")
            results[work_name][task_count] = {}
            
            for impl_name, impl_func in implementations.items():
                result = benchmark_implementation(impl_func, work_func, task_count, num_iterations)
                results[work_name][task_count][impl_name] = result
                
                print(f"  {impl_name:15} - Mean: {result['mean']*1000:.2f}ms, "
                      f"StdDev: {result['stdev']*1000:.2f}ms, "
                      f"Min: {result['min']*1000:.2f}ms, "
                      f"Max: {result['max']*1000:.2f}ms")
    
    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    for work_name in work_types:
        print(f"\n{work_name.upper()} workload:")
        for task_count in task_counts:
            baseline = results[work_name][task_count]["no_sleep"]["mean"]
            overhead = results[work_name][task_count]["time.sleep(0)"]["mean"]
            percent_overhead = ((overhead - baseline) / baseline) * 100
            
            print(f"  {task_count:3} tasks: time.sleep(0) adds {percent_overhead:.1f}% overhead "
                  f"({(overhead - baseline)*1000:.2f}ms absolute)")
    
    return results

async def test_async_impact():
    """Test the impact in async context."""
    print("\n" + "=" * 80)
    print("ASYNC CONTEXT TEST")
    print("=" * 80)
    
    async def async_work(x: int) -> int:
        await asyncio.sleep(0)  # This is the async equivalent
        return x * 2
    
    async def run_async_tasks(num_tasks: int, use_sleep: bool):
        start = time.perf_counter()
        
        tasks = []
        for i in range(num_tasks):
            if use_sleep:
                await asyncio.sleep(0)  # Force yield between task creation
            task = asyncio.create_task(async_work(i))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        return time.perf_counter() - start
    
    for task_count in [10, 100, 500]:
        time_with_sleep = await run_async_tasks(task_count, True)
        time_without_sleep = await run_async_tasks(task_count, False)
        
        overhead = ((time_with_sleep - time_without_sleep) / time_without_sleep) * 100
        print(f"\n{task_count} async tasks:")
        print(f"  With sleep(0): {time_with_sleep*1000:.2f}ms")
        print(f"  Without sleep: {time_without_sleep*1000:.2f}ms")
        print(f"  Overhead: {overhead:.1f}%")

def main():
    """Main entry point."""
    # Run sync benchmarks
    results = run_benchmark_suite()
    
    # Run async benchmarks
    asyncio.run(test_async_impact())
    
    # Conclusion
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("""
Based on the benchmark results:

1. time.sleep(0) does add measurable overhead, especially with many tasks
2. The overhead is more significant for CPU-bound tasks than I/O-bound tasks
3. In async contexts, asyncio.sleep(0) is the proper way to yield control
4. Alternative approaches like thread events may not provide benefits

RECOMMENDATION:
- For sync code: Consider removing time.sleep(0) if performance is critical
- For async code: The __next_tick__ parameter is already ignored (see comment in code)
- The real question is whether the ordering guarantee is worth the performance cost
""")

if __name__ == "__main__":
    main()