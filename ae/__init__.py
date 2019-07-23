import logging

# supported debugging levels    ONLY SHOWING logging levels equal or above:
DEBUG_LEVEL_DISABLED = 0        # ERROR/CRITICAL
DEBUG_LEVEL_ENABLED = 1         # WARNING
DEBUG_LEVEL_VERBOSE = 2         # INFO/DEBUG
DEBUG_LEVEL_TIMESTAMPED = 3     # -"- plus timestamp in logging format

debug_levels = {0: 'disabled', 1: 'enabled', 2: 'verbose', 3: 'timestamped'}

logging_levels = {DEBUG_LEVEL_DISABLED: logging.ERROR, DEBUG_LEVEL_ENABLED: logging.WARNING,
                  DEBUG_LEVEL_VERBOSE: logging.INFO, DEBUG_LEVEL_TIMESTAMPED: logging.DEBUG}

# default date/time formats in config files/variables
DATE_TIME_ISO = '%Y-%m-%d %H:%M:%S.%f'
DATE_ISO = '%Y-%m-%d'
