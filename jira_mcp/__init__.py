"""
Jira MCP Tools Package

This package provides comprehensive Jira integration tools including:
- Issue retrieval and management
- Attachment listing and downloading
- Project exploration
- LLM agent integration for intelligent Jira operations
"""

# Only import what actually exists
try:
    from .utils import JiraClient, JiraUtils
    __all__ = ['JiraClient', 'JiraUtils']
except ImportError:
    __all__ = []

__version__ = "1.0.0"