#!/usr/bin/env python3
"""
Deep analysis of Channel usage patterns in LangGraph to evaluate CoW optimization potential.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json

class ChannelUsageAnalyzer(ast.NodeVisitor):
    """Analyze how channels are used in the codebase."""
    
    def __init__(self):
        self.copy_calls = []
        self.update_calls = []
        self.get_calls = []
        self.channel_creations = []
        self.local_read_patterns = []
        
    def visit_Call(self, node):
        # Check for .copy() calls
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr == 'copy'):
            self.copy_calls.append({
                'line': node.lineno,
                'context': self._get_context(node)
            })
        
        # Check for .update() calls
        elif (isinstance(node.func, ast.Attribute) and 
              node.func.attr == 'update'):
            self.update_calls.append({
                'line': node.lineno,
                'context': self._get_context(node)
            })
        
        # Check for .get() calls
        elif (isinstance(node.func, ast.Attribute) and 
              node.func.attr == 'get'):
            self.get_calls.append({
                'line': node.lineno,
                'context': self._get_context(node)
            })
        
        self.generic_visit(node)
    
    def _get_context(self, node):
        """Get context about where the call is made."""
        parent = node
        depth = 0
        while depth < 3:
            if hasattr(parent, '_parent'):
                parent = parent._parent
                if isinstance(parent, ast.FunctionDef):
                    return f"function:{parent.name}"
                elif isinstance(parent, ast.ClassDef):
                    return f"class:{parent.name}"
            depth += 1
        return "unknown"

def analyze_file(filepath: Path) -> Dict:
    """Analyze a single Python file for channel usage patterns."""
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        
        # Add parent references
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                child._parent = parent
        
        analyzer = ChannelUsageAnalyzer()
        analyzer.visit(tree)
        
        return {
            'file': str(filepath),
            'copy_calls': len(analyzer.copy_calls),
            'update_calls': len(analyzer.update_calls),
            'get_calls': len(analyzer.get_calls),
            'details': {
                'copies': analyzer.copy_calls,
                'updates': analyzer.update_calls,
                'gets': analyzer.get_calls
            }
        }
    except Exception as e:
        return {'file': str(filepath), 'error': str(e)}

def analyze_critical_path():
    """Analyze the critical execution path in _algo.py."""
    print("\n" + "="*80)
    print("CRITICAL PATH ANALYSIS: local_read() function")
    print("="*80)
    
    algo_file = Path("/home/chiliu/pr/langgraph/libs/langgraph/langgraph/pregel/_algo.py")
    
    with open(algo_file, 'r') as f:
        lines = f.readlines()
    
    # Find the local_read function
    local_read_start = None
    local_read_end = None
    for i, line in enumerate(lines):
        if "def local_read(" in line:
            local_read_start = i
        elif local_read_start and line.strip() and not line[0].isspace():
            local_read_end = i
            break
    
    if local_read_start:
        print("\nlocal_read() function (lines {}-{}):".format(
            local_read_start + 1, local_read_end or len(lines)))
        print("-" * 40)
        
        # Count operations
        copy_count = 0
        for i in range(local_read_start, local_read_end or len(lines)):
            if ".copy()" in lines[i]:
                copy_count += 1
                print(f"Line {i+1}: {lines[i].strip()}")
        
        print(f"\nCopies per local_read() call: {copy_count}")
        print("\nIMPACT: This function is called for EVERY conditional edge evaluation!")
        print("In a graph with N nodes and M conditional edges, this results in N*M copies!")

def analyze_channel_types():
    """Analyze different channel types and their copy behavior."""
    print("\n" + "="*80)
    print("CHANNEL TYPE ANALYSIS")
    print("="*80)
    
    channel_dir = Path("/home/chiliu/pr/langgraph/libs/langgraph/langgraph/channels")
    
    channel_types = {}
    for file in channel_dir.glob("*.py"):
        if file.name == "__init__.py":
            continue
        
        with open(file, 'r') as f:
            content = f.read()
        
        # Check for copy implementation
        has_custom_copy = "def copy(self)" in content
        uses_deepcopy = "deepcopy" in content
        simple_value = "self.value = " in content
        
        channel_types[file.stem] = {
            'has_custom_copy': has_custom_copy,
            'uses_deepcopy': uses_deepcopy,
            'simple_value': simple_value,
            'copy_complexity': 'deep' if uses_deepcopy else 'shallow' if has_custom_copy else 'unknown'
        }
    
    for name, info in channel_types.items():
        print(f"\n{name}:")
        print(f"  Copy complexity: {info['copy_complexity']}")
        print(f"  Custom copy: {info['has_custom_copy']}")
        print(f"  Uses deepcopy: {info['uses_deepcopy']}")

def analyze_test_patterns():
    """Analyze test patterns to understand expected behavior."""
    print("\n" + "="*80)
    print("TEST PATTERN ANALYSIS")
    print("="*80)
    
    test_dir = Path("/home/chiliu/pr/langgraph/libs/langgraph/tests")
    
    # Look for patterns that might break with CoW
    patterns_to_check = [
        "channels[",  # Direct channel access
        ".copy()",     # Explicit copy calls
        "id(channel",  # Identity checks
        "is not",      # Object identity comparisons
    ]
    
    risky_tests = []
    for test_file in test_dir.glob("test_*.py"):
        with open(test_file, 'r') as f:
            content = f.read()
        
        for pattern in patterns_to_check:
            if pattern in content:
                count = content.count(pattern)
                risky_tests.append({
                    'file': test_file.name,
                    'pattern': pattern,
                    'count': count
                })
    
    print("\nTests that might be affected by CoW:")
    for test in risky_tests:
        if test['count'] > 5:  # Only show significant usage
            print(f"  {test['file']}: {test['pattern']} ({test['count']} times)")

def estimate_memory_impact():
    """Estimate the real memory impact of CoW optimization."""
    print("\n" + "="*80)
    print("MEMORY IMPACT ESTIMATION")
    print("="*80)
    
    # Analyze a typical execution pattern
    print("\nTypical Graph Execution Pattern:")
    print("-" * 40)
    
    scenarios = [
        {
            'name': 'Small Agent (5 nodes)',
            'nodes': 5,
            'edges': 8,
            'state_size_kb': 10,
            'updates_per_node': 0.2  # 20% of nodes update state
        },
        {
            'name': 'Medium Workflow (20 nodes)',
            'nodes': 20,
            'edges': 35,
            'state_size_kb': 100,
            'updates_per_node': 0.3
        },
        {
            'name': 'Large Multi-Agent (50 nodes)',
            'nodes': 50,
            'edges': 120,
            'state_size_kb': 500,
            'updates_per_node': 0.25
        }
    ]
    
    for scenario in scenarios:
        # Current implementation: every local_read creates copies
        current_copies = scenario['edges']  # One copy per edge evaluation
        current_memory = current_copies * scenario['state_size_kb']
        
        # CoW implementation: only copy on write
        cow_copies = int(scenario['nodes'] * scenario['updates_per_node'])
        cow_memory = cow_copies * scenario['state_size_kb']
        
        savings = ((current_memory - cow_memory) / current_memory) * 100
        
        print(f"\n{scenario['name']}:")
        print(f"  Current: {current_copies} copies, {current_memory/1024:.1f} MB")
        print(f"  CoW: {cow_copies} copies, {cow_memory/1024:.1f} MB")
        print(f"  Memory savings: {savings:.1f}%")

def analyze_langgraph_patterns():
    """Analyze LangGraph-specific patterns that affect CoW feasibility."""
    print("\n" + "="*80)
    print("LANGGRAPH-SPECIFIC PATTERN ANALYSIS")
    print("="*80)
    
    # Check for checkpoint/serialization dependencies
    print("\nCheckpoint Integration:")
    checkpoint_files = [
        "/home/chiliu/pr/langgraph/libs/langgraph/langgraph/pregel/_checkpoint.py",
        "/home/chiliu/pr/langgraph/libs/langgraph/langgraph/pregel/_algo.py"
    ]
    
    for filepath in checkpoint_files:
        with open(filepath, 'r') as f:
            content = f.read()
        
        if "channels[" in content and ".copy()" in content:
            # Count co-occurrences
            lines = content.split('\n')
            checkpoint_copies = 0
            for i, line in enumerate(lines):
                if "checkpoint" in line.lower() and ".copy()" in line:
                    checkpoint_copies += 1
            
            if checkpoint_copies > 0:
                print(f"  {Path(filepath).name}: {checkpoint_copies} checkpoint-related copies")
    
    print("\nThread Safety Concerns:")
    print("  Checking for concurrent access patterns...")
    
    executor_file = "/home/chiliu/pr/langgraph/libs/langgraph/langgraph/pregel/_executor.py"
    with open(executor_file, 'r') as f:
        content = f.read()
    
    if "ThreadPoolExecutor" in content or "asyncio" in content:
        print("  ⚠️  Found concurrent execution - CoW must be thread-safe!")
    
    if "Lock" in content or "RLock" in content:
        print("  ✓ Existing locking mechanisms found - can be adapted for CoW")

def main():
    """Run comprehensive analysis."""
    print("\nCOMPREHENSIVE CHANNEL USAGE ANALYSIS FOR CoW OPTIMIZATION")
    print("="*80)
    
    # 1. Analyze critical path
    analyze_critical_path()
    
    # 2. Analyze channel types
    analyze_channel_types()
    
    # 3. Analyze test patterns
    analyze_test_patterns()
    
    # 4. Estimate memory impact
    estimate_memory_impact()
    
    # 5. Analyze LangGraph-specific patterns
    analyze_langgraph_patterns()
    
    # Summary statistics
    print("\n" + "="*80)
    print("OVERALL STATISTICS")
    print("="*80)
    
    # Count total channel operations in core files
    core_files = [
        "/home/chiliu/pr/langgraph/libs/langgraph/langgraph/pregel/_algo.py",
        "/home/chiliu/pr/langgraph/libs/langgraph/langgraph/pregel/_loop.py",
        "/home/chiliu/pr/langgraph/libs/langgraph/langgraph/pregel/_runner.py"
    ]
    
    total_copies = 0
    total_updates = 0
    
    for filepath in core_files:
        result = analyze_file(Path(filepath))
        if 'error' not in result:
            total_copies += result['copy_calls']
            total_updates += result['update_calls']
            print(f"\n{Path(filepath).name}:")
            print(f"  Copies: {result['copy_calls']}")
            print(f"  Updates: {result['update_calls']}")
            print(f"  Read/Write ratio: {result['get_calls']}/{result['update_calls'] if result['update_calls'] > 0 else 'N/A'}")

if __name__ == "__main__":
    main()