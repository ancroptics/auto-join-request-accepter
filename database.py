import logging
import asyncio
import os

logger = logging.getLogger(__name__)

_pool = None
pool = None  # public alias
