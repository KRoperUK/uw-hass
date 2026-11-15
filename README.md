# UW Home Assistant Integration

Custom Home Assistant integration for Utility Warehouse account data (energy, bills, meter readings).

## Installation

### Manual

1. Install the Python library:

```bash
pip install uw-api
```

2. Copy the integration to your Home Assistant `custom_components` directory:

```bash
cp -r custom_components/utility_warehouse/ /config/custom_components/
```

### HACS

Add this repository as a custom repository in HACS.

## Configuration

1. Settings → Devices & Services → Add Integration → Utility Warehouse
2. Enter your email/account number and password
3. Credentials are validated against the UW portal

## Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Electricity consumption | kWh | Total electricity meter reading |
| Electricity cost | GBP | Estimated electricity cost |
| Gas consumption | kWh | Total gas meter reading |
| Gas cost | GBP | Estimated gas cost |
| Electricity meter reading | kWh | Latest electricity reading |
| Gas meter reading | kWh | Latest gas reading |
| Last reading date | timestamp | Most recent meter read date |
| Electricity meter number | — | Meter serial number |
| Gas meter number | — | Meter serial number |
| Energy tariff | — | Current tariff name |
| Unit rate | p/kWh | Price per kWh |
| Standing charge | p/day | Daily standing charge |
| Last bill amount | GBP | Most recent bill total |
| Last bill date | date | Most recent bill date |
| Bill status | — | paid / pending / overdue |

## Binary Sensors

| Sensor | Description |
|--------|-------------|
| Bill overdue | On when the latest bill is overdue |
| Smart meter | On when at least one meter is smart |

## Troubleshooting

`auth_error` during setup means the UW portal rejected the credentials.
Check the log for the stage that failed (`login` vs `account fetch`):

- Use the email address you log into the UW website with, not just the
  account number, and confirm that password still works on the website.
- `connection_error` (including rate limiting) is transient: wait a few
  minutes and retry.
- If it persists, enable debug logging and include the
  `custom_components.utility_warehouse` lines (they never contain your
  password) when reporting an issue:

```yaml
logger:
  logs:
    custom_components.utility_warehouse: debug
```

## Energy Dashboard

The `electricity_consumption` and `gas_consumption` sensors are compatible with the HA Energy Dashboard. Add them as consumption sources.

## Requirements

- Home Assistant 2024.1+
- Python 3.12+
- `uw-api==0.2.0` Python package
