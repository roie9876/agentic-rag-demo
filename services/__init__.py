"""
Services module for Agentic RAG Demo

This module contains business services and authentication handlers
that support both public and private Azure resources.
"""

from .azure_auth_service import azure_auth_service

__all__ = ['azure_auth_service']
