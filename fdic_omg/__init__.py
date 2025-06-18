"""
FDIC OMG Semantic Augmentation Package

This package provides tools for converting FDIC CSV data to RDF with semantic mappings
for the OMG Semantic Augmentation Challenge 2025.
"""

__version__ = "1.0.0"
__author__ = "Lodgeit Labs"

from .core import FDICRDFGenerator
from .job import process_fdic_omg_job

__all__ = ["FDICRDFGenerator", "process_fdic_omg_job"]