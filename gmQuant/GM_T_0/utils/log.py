import logging
import logging.handlers

LOG_FILE = 'gm_t_0.log'

handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=4 * 1024 * 1024, backupCount=5)
fmt = '%(asctime)s - %(name)s - %(message)s'

formatter = logging.Formatter(fmt)
handler.setFormatter(formatter)

logger = logging.getLogger('GM')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
