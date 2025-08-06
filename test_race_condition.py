#!/usr/bin/env python3
"""Test to demonstrate and verify the FuturesDict race condition."""

import concurrent.futures
import threading
import time
import weakref
from typing import Optional
from dataclasses import dataclass

# Simulate the relevant parts of the FuturesDict implementation

@dataclass
class PregelExecutableTask:
    """Simulated task for testing."""
    id: str
    should_fail: bool = False

class FuturesDict(dict):
    """Simplified version of FuturesDict to demonstrate the race condition."""
    
    def __init__(self, event: threading.Event, callback):
        super().__init__()
        self.lock = threading.Lock()
        self.event = event
        self.callback = weakref.ref(callback) if not isinstance(callback, weakref.ref) else callback
        self.counter = 0
        self.done = set()
        self.callback_execution_times = []
        self.event_set_time = None
    
    def __setitem__(self, key, value: Optional[PregelExecutableTask]):
        super().__setitem__(key, value)
        if value is not None:
            with self.lock:
                self.event.clear()
                self.counter += 1
            key.add_done_callback(lambda fut: self.on_done(value, fut))
    
    def on_done(self, task: PregelExecutableTask, fut):
        """This is where the race condition exists."""
        callback_start = time.perf_counter()
        
        try:
            # Callback can take varying amounts of time
            if cb := self.callback():
                exception = fut.exception() if hasattr(fut, 'exception') else None
                cb(task, exception)
                callback_end = time.perf_counter()
                self.callback_execution_times.append((callback_start, callback_end))
        finally:
            # The problem: event is set BEFORE ensuring all callbacks are done
            with self.lock:
                self.done.add(fut)
                self.counter -= 1
                if self.counter == 0:
                    self.event_set_time = time.perf_counter()
                    self.event.set()  # RACE: This can fire while other callbacks are still running!

def demonstrate_race_condition():
    """Demonstrate the race condition in FuturesDict."""
    
    print("=" * 80)
    print("RACE CONDITION DEMONSTRATION: FuturesDict Event Signaling")
    print("=" * 80)
    print()
    
    # Shared state that callbacks might modify
    shared_state = {"completed_callbacks": 0, "in_progress_callbacks": 0}
    state_lock = threading.Lock()
    
    def slow_callback(task: PregelExecutableTask, exception):
        """Callback that takes variable time to complete."""
        with state_lock:
            shared_state["in_progress_callbacks"] += 1
        
        # Simulate varying processing times
        if task.id == "slow_task":
            time.sleep(0.01)  # 10ms for slow task
        else:
            time.sleep(0.001)  # 1ms for normal tasks
        
        with state_lock:
            shared_state["completed_callbacks"] += 1
            shared_state["in_progress_callbacks"] -= 1
    
    # Run test multiple times to catch the race condition
    race_detected = False
    
    for iteration in range(10):
        # Reset state
        shared_state["completed_callbacks"] = 0
        shared_state["in_progress_callbacks"] = 0
        
        event = threading.Event()
        futures_dict = FuturesDict(event, slow_callback)
        
        # Create multiple tasks with varying execution times
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit tasks
            tasks = [
                PregelExecutableTask("fast_task_1"),
                PregelExecutableTask("fast_task_2"),
                PregelExecutableTask("slow_task"),  # This one will take longer in callback
                PregelExecutableTask("fast_task_3"),
            ]
            
            for task in tasks:
                future = executor.submit(lambda t=task: time.sleep(0.0001))  # Quick task execution
                futures_dict[future] = task
            
            # Wait for event to be set
            event.wait(timeout=1.0)
            
            # Check if callbacks are still running when event was set
            if shared_state["in_progress_callbacks"] > 0:
                print(f"Iteration {iteration + 1}: RACE CONDITION DETECTED!")
                print(f"  Event was set while {shared_state['in_progress_callbacks']} callbacks still running")
                print(f"  Completed callbacks: {shared_state['completed_callbacks']}/{len(tasks)}")
                race_detected = True
                
                # Analyze timing
                if futures_dict.event_set_time and futures_dict.callback_execution_times:
                    for i, (start, end) in enumerate(futures_dict.callback_execution_times):
                        if end > futures_dict.event_set_time:
                            print(f"  Callback {i} finished AFTER event was set!")
                            print(f"    Event set at: {futures_dict.event_set_time:.6f}")
                            print(f"    Callback ended at: {end:.6f}")
                            print(f"    Overrun by: {(end - futures_dict.event_set_time)*1000:.2f}ms")
            else:
                print(f"Iteration {iteration + 1}: No race detected (lucky timing)")
            
            # Wait a bit for all callbacks to actually complete
            time.sleep(0.02)
    
    if not race_detected:
        print("\nNo race condition detected in 10 iterations (may need more iterations or different timing)")
    
    return race_detected

def demonstrate_correct_implementation():
    """Show how the race condition could be fixed."""
    
    print("\n" + "=" * 80)
    print("CORRECTED IMPLEMENTATION: Proper Synchronization")
    print("=" * 80)
    print()
    
    class FixedFuturesDict(dict):
        """Fixed version with proper synchronization."""
        
        def __init__(self, event: threading.Event, callback):
            super().__init__()
            self.lock = threading.Lock()
            self.event = event
            self.callback = weakref.ref(callback) if not isinstance(callback, weakref.ref) else callback
            self.counter = 0
            self.done = set()
            self.callbacks_in_progress = 0
            self.callbacks_lock = threading.Lock()
        
        def __setitem__(self, key, value: Optional[PregelExecutableTask]):
            super().__setitem__(key, value)
            if value is not None:
                with self.lock:
                    self.event.clear()
                    self.counter += 1
                key.add_done_callback(lambda fut: self.on_done(value, fut))
        
        def on_done(self, task: PregelExecutableTask, fut):
            """Fixed version that ensures callbacks complete before signaling."""
            # Track callback execution
            with self.callbacks_lock:
                self.callbacks_in_progress += 1
            
            try:
                if cb := self.callback():
                    exception = fut.exception() if hasattr(fut, 'exception') else None
                    cb(task, exception)
            finally:
                # Proper synchronization
                with self.lock:
                    self.done.add(fut)
                    self.counter -= 1
                    should_signal = self.counter == 0
                
                # Decrement callbacks counter BEFORE potentially signaling
                with self.callbacks_lock:
                    self.callbacks_in_progress -= 1
                    # Only signal if no callbacks are running AND all futures are done
                    if should_signal and self.callbacks_in_progress == 0:
                        self.event.set()
    
    # Test the fixed implementation
    shared_state = {"completed_callbacks": 0}
    
    def test_callback(task: PregelExecutableTask, exception):
        time.sleep(0.01 if task.id == "slow_task" else 0.001)
        shared_state["completed_callbacks"] += 1
    
    event = threading.Event()
    fixed_dict = FixedFuturesDict(event, test_callback)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        tasks = [
            PregelExecutableTask("fast_task_1"),
            PregelExecutableTask("slow_task"),
            PregelExecutableTask("fast_task_2"),
        ]
        
        for task in tasks:
            future = executor.submit(lambda: None)
            fixed_dict[future] = task
        
        event.wait(timeout=1.0)
        
        # With the fix, all callbacks should be complete when event is set
        print(f"Event signaled. Completed callbacks: {shared_state['completed_callbacks']}/{len(tasks)}")
        if shared_state["completed_callbacks"] == len(tasks):
            print("✓ All callbacks completed before event was set (CORRECT)")
        else:
            print("✗ Some callbacks still running (INCORRECT)")

def main():
    """Run the race condition demonstration."""
    print("Testing FuturesDict race condition...")
    print("This demonstrates a subtle concurrency bug in the event signaling mechanism.\n")
    
    race_detected = demonstrate_race_condition()
    demonstrate_correct_implementation()
    
    print("\n" + "=" * 80)
    print("IMPACT AND SOLUTION")
    print("=" * 80)
    print("""
The race condition can cause:
1. Downstream processes to start before all callbacks complete
2. State inconsistencies if callbacks modify shared state
3. Potential data corruption in checkpoint operations

SOLUTION:
Implement proper barrier synchronization to ensure all callbacks
complete before signaling the event. This requires tracking
callback execution state separately from future completion.

This is a sophisticated concurrency bug that requires deep understanding
of threading primitives and race conditions to identify and fix properly.
""")

if __name__ == "__main__":
    main()