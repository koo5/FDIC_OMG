#!/usr/bin/env python3
"""
FDIC OMG CLI entry point

This allows running the CLI as: python -m fdic_omg
"""

if __name__ == "__main__":
    from .cli import cli
    cli()