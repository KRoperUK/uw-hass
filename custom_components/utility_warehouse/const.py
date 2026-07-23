from __future__ import annotations

from typing import Final

DOMAIN = "utility_warehouse"
NAME = "Utility Warehouse"
VERSION = "0.2.0"  # x-release-please-version

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

DEFAULT_SCAN_INTERVAL = 3600  # 1 hour
MIN_SCAN_INTERVAL = 900  # 15 minutes
MAX_SCAN_INTERVAL = 86400  # 24 hours

AVAILABILITY_GRACE_SECONDS = 7200  # 2 hours

ATTR_SERVICE_TYPE: Final = "service_type"
ATTR_ACCOUNT_NUMBER: Final = "account_number"
ATTR_TARIFF_NAME: Final = "tariff_name"
ATTR_UNIT_RATE: Final = "unit_rate_pence"
ATTR_STANDING_CHARGE: Final = "standing_charge_pence"
ATTR_BILL_STATUS: Final = "bill_status"
ATTR_DUE_DATE: Final = "due_date"
ATTR_PERIOD_START: Final = "period_start"
ATTR_PERIOD_END: Final = "period_end"
ATTR_METER_NUMBER: Final = "meter_number"
ATTR_READING_DATE: Final = "reading_date"
ATTR_READING_TYPE: Final = "reading_type"
