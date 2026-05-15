from datetime import date

APP_NAME = "nhtsa_metadata"
DEFAULT_ENVIRONMENT = "local"
DEFAULT_DATABASE_URL = "sqlite:///data/full_2011plus_metadata_filter_ready_2026-05-04.sqlite"
DEFAULT_NHTSA_BASE_URL = "https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/api/v1"
DEFAULT_ALLOW_LIVE = False
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRY_COUNT = 2
DEFAULT_RATE_LIMIT_DELAY_SECONDS = 0.0
DEFAULT_MIN_TEST_DATE = date(2011, 1, 1)
DEFAULT_DOWNLOAD_DIR = "data/downloads"
DEFAULT_MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
