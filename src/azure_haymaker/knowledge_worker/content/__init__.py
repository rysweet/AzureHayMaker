"""Email content generation module for Knowledge Workers.

This module provides AI-powered email content generation with custom directives
and fallback strategies for Knowledge Worker deployments.

Public Interface:
    - EmailContent: Dataclass for email subject, body, and metadata
    - EmailGenerationConfig: Configuration for AI email generation
    - EmailContentGenerator: AI-powered email generator using Anthropic
    - FallbackEmailGenerator: Simple fallback when AI is unavailable
"""

from azure_haymaker.knowledge_worker.content.email_generator import (
    EmailContent,
    EmailContentGenerator,
    EmailGenerationConfig,
)
from azure_haymaker.knowledge_worker.content.fallback import FallbackEmailGenerator

__all__ = [
    "EmailContent",
    "EmailGenerationConfig",
    "EmailContentGenerator",
    "FallbackEmailGenerator",
]
