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

Password sign-in is not supported: the UW portal completes a browser-only
device check after the password is entered, which Home Assistant cannot do. The
integration reuses a session you already created instead.

1. Sign in at <https://myaccount.uw.co.uk> in any browser.
2. Open the developer tools (F12) → **Network**, reload the page, click the
   first request to `myaccount.uw.co.uk`, and copy the whole `Cookie` request
   header. In Chrome/Edge: right-click the request → **Copy** →
   **Copy as cURL**, then take the value after `-H 'cookie: '`. In Firefox:
   **Copy Value** on the `Cookie` header.
3. Settings → Devices & Services → Add Integration → Utility Warehouse, and
   paste the header.

The session lasts about a month. When it expires the integration raises a
**Repair** asking for a fresh header — no reinstall needed.

### If Cloudflare blocks the requests

Paste the browser's user agent into the optional field on the same form
(DevTools console: `navigator.userAgent`). Cloudflare's clearance cookie is
bound to the user agent that solved the challenge, so the integration must send
the same one. Leave it blank unless you see `429`/challenge errors in the log.


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

`auth_error` during browser-session setup means the pasted header was rejected.
Check that you copied the `Cookie` **request** header from `myaccount.uw.co.uk`
while signed in, and that it still contains `_csrf` and `uw-user-session`.

If the integration has been running and starts failing, the session has expired:
Home Assistant raises a **Repair** ("Utility Warehouse session has expired") with
a **Fix** button that asks for a fresh header. Sensors keep their last values for
two hours, then become unavailable until the repair is applied.

`connection_error` (including rate limiting) is transient: wait a few minutes
and retry. If it persists, enable debug logging and include the
`custom_components.utility_warehouse` lines (they never contain your
password or cookies) when reporting an issue:

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
- `uw-api==0.3.1` Python package
