#!/usr/bin/env python3
"""Test to analyze the impact of broad exception handling."""

import traceback
from typing import Literal, get_type_hints, get_origin, get_args
import sys
import io

# Simulate the actual code patterns from the codebase

def test_branch_type_hints():
    """Test the exception handling in _branch.py type hint extraction."""
    
    class TestClass:
        def method_with_literal(self) -> Literal["a", "b", "c"]:
            return "a"
        
        def method_without_hints(self):
            return "x"
        
        def method_with_complex_hint(self) -> dict[str, list[int]]:
            return {}
    
    test_cases = [
        TestClass().method_with_literal,
        TestClass().method_without_hints,
        TestClass().method_with_complex_hint,
        lambda: "test",  # lambda without hints
        None,  # None object
        "not_a_function",  # String instead of function
    ]
    
    print("Testing _branch.py type hint extraction pattern:")
    print("-" * 50)
    
    for i, func in enumerate(test_cases):
        print(f"\nTest case {i+1}: {func}")
        
        # Original pattern (broad exception)
        path_map_broad = None
        try:
            if func:
                if rtn_type := get_type_hints(func).get("return"):
                    if get_origin(rtn_type) is Literal:
                        path_map_broad = {name: name for name in get_args(rtn_type)}
        except Exception as e:
            print(f"  Broad catch: Silently swallowed {type(e).__name__}")
            pass
        
        # Improved pattern (specific exceptions)
        path_map_specific = None
        try:
            if func:
                if rtn_type := get_type_hints(func).get("return"):
                    if get_origin(rtn_type) is Literal:
                        path_map_specific = {name: name for name in get_args(rtn_type)}
        except (AttributeError, TypeError, NameError) as e:
            print(f"  Specific catch: Expected error {type(e).__name__}: {e}")
        except Exception as e:
            print(f"  Specific catch: UNEXPECTED error {type(e).__name__}: {e}")
            traceback.print_exc()
        
        print(f"  Results - Broad: {path_map_broad}, Specific: {path_map_specific}")

def test_module_lookup():
    """Test the exception handling in _call.py module lookup."""
    
    import types
    
    def _getattribute(module, name):
        """Simulate the actual _getattribute function."""
        # This could fail in various ways
        if not hasattr(module, name):
            raise AttributeError(f"module has no attribute {name}")
        return (getattr(module, name), module)
    
    # Create test scenarios
    test_modules = [
        (types.ModuleType("test_module"), "nonexistent_attr"),
        (None, "attr"),  # None module
        ("not_a_module", "attr"),  # Wrong type
        (types.ModuleType("test_module"), None),  # None attribute name
    ]
    
    print("\n\nTesting _call.py module lookup pattern:")
    print("-" * 50)
    
    for i, (module, name) in enumerate(test_modules):
        print(f"\nTest case {i+1}: module={module}, name={name}")
        
        # Original pattern
        result_broad = None
        try:
            if _getattribute(module, name)[0] is object:
                result_broad = "found"
        except Exception:
            pass
        
        # Improved pattern
        result_specific = None
        try:
            if _getattribute(module, name)[0] is object:
                result_specific = "found"
        except (AttributeError, TypeError) as e:
            # These are expected errors that we handle
            print(f"  Expected error: {type(e).__name__}: {e}")
        except Exception as e:
            # Unexpected errors should be logged
            print(f"  UNEXPECTED error: {type(e).__name__}: {e}")
            
        print(f"  Results - Broad: {result_broad}, Specific: {result_specific}")

def test_binop_initialization():
    """Test the exception handling in binop.py initialization."""
    
    print("\n\nTesting binop.py initialization pattern:")
    print("-" * 50)
    
    # Test different types that might fail initialization
    test_types = [
        dict,  # Should work
        list,  # Should work
        set,   # Should work
        lambda: None,  # Callable, will fail
        type("CustomType", (), {"__init__": lambda self: 1/0}),  # Init raises error
        None,  # Not a type
    ]
    
    for typ in test_types:
        print(f"\nTesting with type: {typ}")
        
        # Original pattern
        value_broad = "MISSING"
        try:
            value_broad = typ() if typ else None
        except Exception:
            value_broad = "MISSING"
        
        # Improved pattern
        value_specific = "MISSING"
        try:
            value_specific = typ() if typ else None
        except (TypeError, ValueError) as e:
            print(f"  Expected initialization error: {e}")
            value_specific = "MISSING"
        except Exception as e:
            print(f"  UNEXPECTED error during initialization: {type(e).__name__}: {e}")
            value_specific = "MISSING"
            
        print(f"  Results - Broad: {value_broad}, Specific: {value_specific}")

def main():
    """Run all exception handling tests."""
    print("=" * 60)
    print("EXCEPTION HANDLING ANALYSIS")
    print("=" * 60)
    
    test_branch_type_hints()
    test_module_lookup()
    test_binop_initialization()
    
    print("\n" + "=" * 60)
    print("FINDINGS:")
    print("=" * 60)
    print("""
1. Broad 'except Exception:' can hide unexpected errors
2. Most caught exceptions are actually AttributeError or TypeError
3. Specific exception handling provides better debugging information
4. Some edge cases might raise unexpected exceptions that should be logged

RECOMMENDATION:
Replace broad exception handlers with specific ones and add logging for 
unexpected exceptions to improve debuggability without breaking functionality.
""")

if __name__ == "__main__":
    main()