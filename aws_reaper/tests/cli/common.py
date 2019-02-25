import logging


def get_cli_logger(debug=False):
    """
    Args:
        debug (bool): Set to True to enable debug logs.

    Returns:
        :obj:`logging.Logger`

    """
    logger = logging.getLogger('aws_reaper')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    stream_handler = logging.StreamHandler()
    if debug:
        log_format = '%(levelname)s %(name)s:%(funcName)s %(message)s'
    else:
        log_format = '%(levelname)s %(message)s'
    formatter = logging.Formatter(log_format)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger
