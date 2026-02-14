"""
Shared utilities for PaperIgnition backend services.

This module contains common functionality shared between:
- Backend Service (backend/app/)
- Index Service (backend/index_service/)

Last updated: 2025-02-12
"""

from .config_utils import load_config, load_config_from_environment

__all__ = ['load_config', 'load_config_from_environment']
