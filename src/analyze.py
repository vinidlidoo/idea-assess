#!/usr/bin/env python3
"""
Business Idea Analyzer - Main entry point.

This module delegates to the modular CLI implementation.
For direct usage, see cli.py or use the agents module directly.
"""

if __name__ == "__main__":
    import sys
    import os
    # Add parent directory to path so imports work
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from src.cli import main
    import asyncio
    asyncio.run(main())