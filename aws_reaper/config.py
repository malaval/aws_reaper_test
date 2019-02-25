class Config:
    CONCURRENT_WORKERS = 20  # Number of concurrent threads to check or clean resources
    MAX_WAIT_UNTIL_DELETED = 5*60  # Maximum number of seconds to wait for resources to be deleted
    WAIT_BETWEEN_RETRIES = 10  # Number of seconds to wait between two attempts to delete resources
    NB_RETRIES = 3  # Number of retries when calling a function
    MIN_PASSES = 2
    MAX_PASSES = 5

    def __init__(self):
        pass
