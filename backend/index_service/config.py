# This module has been deprecated in favor of the enhanced load_config function in db_utils.py
# All configuration loading should now use backend.index_service.db_utils.load_config

import logging

logger = logging.getLogger(__name__)

# Import the enhanced load_config function from db_utils
from .db_utils import load_config

# For backward compatibility, we can still import load_config from this module
# but it will actually use the enhanced version from db_utils
__all__ = ['load_config']