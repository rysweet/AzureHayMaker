"""
Repositories package for monitoring API.

Contains data access layer implementations for Azure Storage.
"""

from .monitoring_repository import MonitoringRepository

__all__ = ["MonitoringRepository"]
