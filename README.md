# arapy

[![Version](https://img.shields.io/badge/version-1.1.5-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()
[![License](https://img.shields.io/badge/license-Internal-orange.svg)]()

A modular Python CLI and GUI tool for interacting with the  
**Aruba ClearPass Policy Manager REST API**.

---

## 🚀 Overview

**arapy** provides:

- 🖥️ A powerful **command-line interface** for automation and scripting
- 🧩 A clean, modular architecture for extending ClearPass API support
- 🪟 A lightweight **Tkinter-based GUI** for operators
- 📂 Structured logging with configurable output
- 🔎 Clear and detailed API error reporting

Version: **1.1.3**

### What's New in v1.1.3

**Patch release** — Added missing `network-device get` action help text to `print_help()`. All features and functionality from v1.1.1 remain intact.

- **Device Accounts** — Manage device identities (MAC-based device registration)
- **Guest Users** — Provision and manage guest user accounts
- **API Clients** — Create OAuth clients for third-party integrations  
- **Authentication Methods** — Configure authentication sources (LDAP, AD, radius, etc)
- **Enforcement Profiles** — Query enforcement policy configurations

All services support:
- ✅ **CRUD operations** (Create, Read, Update, Delete)
- ✅ **Pagination & filtering** (limit, offset, sort, filter)  
- ✅ **Bulk imports** (JSON/CSV file uploads)
- ✅ **CSV export** with custom column selection
- ✅ **Structured logging** (JSON and CSV output formats)
- ✅ **Context-aware help** (`arapy <module> <service> --help`)

---

# ✨ Features (v1.1.5)

## 🔧 Modular Command Architecture

Command structure:

```bash
arapy <module> <service> <action> [--key=value] [-flags]
```

Example:

```bash
arapy policy-elements network-device list --csv_filenames=id,name,ip_address
arapy identities endpoint list --limit=5
```

Internally powered by a centralized `DISPATCH` routing table.

---

## 📦 Supported Modules

### policy-elements

#### network-device
- `list`
- `add`
- `delete`
- `get`

#### auth-method
- `list`
- `add`
- `delete`
- `get`

#### enforcement-profile
- `list`
- `get`

---

### identities

#### endpoint
- `list`
- `get`  
- `add`
- `delete`

#### device
- `list`
- `add`
- `delete`
- `get`

#### user (Guest Users)
- `list`
- `add`
- `delete`
- `get`

#### api-client
- `list`
- `add`
- `delete`
- `get`

---

# 🖥️ CLI Usage

## Network Devices (Policy Elements > Network Device)

### List
```bash
# List all network devices
arapy policy-elements network-device list

# List with limit and custom sort
arapy policy-elements network-device list --limit=10 --sort=+name

# List with server-side filter
arapy policy-elements network-device list --filter='{"vendor_name":"Aruba"}'

# Export to CSV with specific columns
arapy policy-elements network-device list --csv_fieldnames=id,name,ip_address,vendor_name

# Get total count
arapy policy-elements network-device list --calculate_count=true
```

### Add
```bash
# Add single device with required parameters
arapy policy-elements network-device add \
    --name=border-router --ip_address=10.0.0.1 --vendor_name=Aruba

# Add with optional RADIUS secret
arapy policy-elements network-device add \
    --name=switch-stack --ip_address=10.1.0.0 \
    --vendor_name=Hewlett-Packard-Enterprise --radius_secret=PSK123

# Bulk import from CSV
arapy policy-elements network-device add --file=devices.csv --verbose

# Bulk import from JSON
arapy policy-elements network-device add --file=devices.json
```

### Delete
```bash
# Delete by ID
arapy policy-elements network-device delete --id=1234

# Delete and log to JSON
arapy policy-elements network-device delete --id=1234 --out=./deleted.json
```

### Get
```bash
# Get single device details
arapy policy-elements network-device get --id=1234

# Get and export to JSON
arapy policy-elements network-device get --id=1234 --out=./device_details.json
```

---

## Endpoints (Identities > Endpoint)

### List
```bash
# List all endpoints
arapy identities endpoint list

# List with pagination
arapy identities endpoint list --limit=25 --offset=50

# Filter by status
arapy identities endpoint list --filter='{"status":"Known"}' --calculate_count=true

# Export to CSV with custom columns
arapy identities endpoint list --csv_fieldnames=id,mac_address,status,description --out=./endpoints.csv
```

### Get
```bash
# Get by endpoint ID
arapy identities endpoint get --id=1234

# Get by MAC address
arapy identities endpoint get --mac_address=aa:bb:cc:dd:ee:ff

# Export details
arapy identities endpoint get --id=1234 --out=./endpoint_detail.json
```

### Add
```bash
# Add endpoint with required fields
arapy identities endpoint add --mac_address=aa:bb:cc:dd:ee:ff --status=Known

# Add with description and tags  
arapy identities endpoint add \
    --mac_address=aa:bb:cc:dd:ee:ff --status=Known \
    --description="Guest Printer" --device_insight_tags=printer,guest

# Add with randomized MAC indicator
arapy identities endpoint add \
    --mac_address=aa:bb:cc:dd:ee:ff --status=Known --randomized_mac=true

# Bulk import from CSV
arapy identities endpoint add --file=endpoints.csv

# Bulk import from JSON
arapy identities endpoint add --file=endpoints.json
```

### Delete
```bash
# Delete by endpoint ID
arapy identities endpoint delete --id=1234

# Delete by MAC address
arapy identities endpoint delete --mac_address=aa:bb:cc:dd:ee:ff
```

---

## Device Accounts (Identities > Device)

### List
```bash
# List all device accounts
arapy identities device list

# List with pagination and sorting
arapy identities device list --limit=25 --offset=0 --sort=-id

# Filter by role  
arapy identities device list --filter='{"role_id":2}'

# Export to CSV
arapy identities device list --csv_fieldnames=id,mac,enabled,role_id --out=./devices.csv
```

### Add
```bash
# Add single device with required MAC
arapy identities device add --mac=aa:bb:cc:dd:ee:ff

# Add with role assignment
arapy identities device add --mac=aa:bb:cc:dd:ee:ff --role_id=2 --enabled=true

# Bulk import from JSON
arapy identities device add --file=devices.json
```

### Delete
```bash
# Delete by device ID
arapy identities device delete --id=123

# Delete by MAC address
arapy identities device delete --mac_address=aa:bb:cc:dd:ee:ff
```

### Get
```bash
# Get device details by ID
arapy identities device get --id=123

# Get device details by MAC
arapy identities device get --mac_address=aa:bb:cc:dd:ee:ff
```

---

## Guest Users (Identities > User)

### List
```bash
# List all guest users
arapy identities user list

# List with pagination
arapy identities user list --limit=25 --offset=0 --sort=+username

# Filter by expiry status
arapy identities user list --filter='{"enabled":true}'

# Get total count
arapy identities user list --calculate_count=true
```

### Add
```bash
# Add single user with credentials
arapy identities user add --username=guest1 --password=secret123

# Add with additional details
arapy identities user add \
    --username=guest2 --password=temppass123 \
    --role_id=101 --sponsor_name="John Doe"

# Bulk import from JSON
arapy identities user add --file=users.json
```

### Delete
```bash
# Delete guest user
arapy identities user delete --id=5001
```

### Get
```bash
# Get user details
arapy identities user get --id=5001
```

---

## API Clients (Identities > API Clients)

### List
```bash
# List all API clients
arapy identities api-client list

# List with pagination
arapy identities api-client list --limit=10 --sort=+client_id

# Filter by status
arapy identities api-client list --filter='{"enabled":true}'
```

### Add
```bash
# Create API client with client ID and secret
arapy identities api-client add \
    --client_id=automation-user --client_secret=RandomSecure123!

# Create with additional OAuth settings
arapy identities api-client add \
    --client_id=portal-sync --client_secret=secret --enabled=true \
    --client_public=false --client_refresh=true

# Bulk import from JSON
arapy identities api-client add --file=api_clients.json
```

### Delete
```bash
# Delete API client
arapy identities api-client delete --id=automation-user
```

### Get
```bash
# Get API client details
arapy identities api-client get --id=automation-user
```

---

## Authentication Methods (Policy Elements > Auth Method)

### List
```bash
# List all authentication methods
arapy policy-elements auth-method list

# List with pagination
arapy policy-elements auth-method list --limit=20 --sort=+name

# Filter by method type
arapy policy-elements auth-method list --filter='{"method_type":"LDAP"}'
```

### Add
```bash
# Create authentication method
arapy policy-elements auth-method add --name=internal-ldap --method_type=LDAP

# Create with details (JSON for details field)
arapy policy-elements auth-method add \
    --name=ad-auth --method_type=Active-Directory \
    --description="Active Directory authentication"

# Bulk import from JSON
arapy policy-elements auth-method add --file=auth_methods.json
```

### Delete
```bash
# Delete authentication method
arapy policy-elements auth-method delete --id=123
```

### Get
```bash
# Get authentication method details
arapy policy-elements auth-method get --id=123
```

---

## Enforcement Profiles (Policy Elements > Enforcement Profile)

### List
```bash
# List all enforcement profiles
arapy policy-elements enforcement-profile list

# List with pagination
arapy policy-elements enforcement-profile list --limit=50 --sort=+id

# Filter by name or other criteria
arapy policy-elements enforcement-profile list --filter='{"name":"Guest"}'

# Get total count
arapy policy-elements enforcement-profile list --calculate_count=true
```

### Get
```bash
# Get enforcement profile details
arapy policy-elements enforcement-profile get --id=1001

# Get and export to JSON
arapy policy-elements enforcement-profile get --id=1001 --out=./profile_details.json
```

---

# ⚙️ Global Options

| Option | Description |
|--------|------------|
| `--limit=N` | Limit results (1–1000, default 25) |
| `--offset=N` | Pagination offset (default 0) |
| `--sort=±id` | Sort ordering; prefix with `+` (ascending) or `-` (descending) |
| `--out=FILE` | Override default log output path |
| `--file=FILE` | Load bulk payload from JSON or CSV |
| `--filter=JSON` | Server-side JSON filter expression |
| `--calculate_count=yes/no` | Request total item count from server |
| `--csv_fieldnames=...` | Custom CSV columns (comma-separated) |
| `-vvv, --verbose` | Print output to console (plus log to file) |
| `--help` | Context-aware help for module/service/action |
| `--version` | Display installed version |

### Filter Expressions

`--filter` accepts ClearPass API JSON filter syntax:

```bash
# Simple equality
arapy identities endpoint list --filter='{"status":"Known"}'

# Multiple conditions (AND)
arapy identities device list --filter='{"enabled":true,"role_id":2}'

# With comparison operators
arapy policy-elements network-device list --filter='{"name":{"$contains":"border"}}'
```

Check ClearPass API documentation for supported operators like `$contains`, `$gt`, `$gte`, `$lt`, etc.

### Pagination & Limits

- `--limit` must be an integer 1–1000 (per ClearPass API constraints)
- Default limit: 25 items per request
- Use `--offset` to skip results for pagination
- Use `--calculate_count=true` to fetch total count (slower on large datasets)

Example pagination:
```bash
# First 25 items
arapy identities endpoint list --limit=25

# Next 25 items
arapy identities endpoint list --limit=25 --offset=25
```

### File Imports (Bulk Operations)

`--file` supports JSON and CSV bulk imports for `add` operations:

```bash
# JSON format: single object or array of objects
arapy identities endpoint add --file=endpoints.json

# CSV format: DictReader with header row
arapy policy-elements network-device add --file=devices.csv
```

Example CSV format:
```csv
name,ip_address,vendor_name
border-1,10.0.0.1,Aruba
border-2,10.0.0.2,Aruba
```

### CSV Export

Export list results to CSV with custom columns:

```bash
# Export with selected columns
arapy policy-elements network-device list \
    --csv_fieldnames=id,name,ip_address,vendor_name \
    --out=./devices_export.csv

# Available columns vary by service; defaults include id, name, enabled, etc.
```

### Sorting

Use `--sort=` with a plus (`+`) for ascending or minus (`-`) for descending:

```bash
# Sort by name (ascending)
arapy identities device list --sort=+name

# Sort by ID (descending)
arapy identities user list --sort=-id
```

---

# 🪟 GUI Mode

Launch GUI:

```bash
arapy-gui
```

Or:

```bash
arapy gui
```

### GUI Features

- Dropdown selection of:
  - Module
  - Service
  - Action
- Space-separated argument input (`--key=value`)
- Built-in **file picker button** for `--file=`
- Live command output display
- Verbose toggle
- Uses same backend as CLI
- Logs still written to disk

### If Tkinter is missing

```bash
sudo apt install python3-tk
```

---

# 📂 Logging

All commands log output to disk by default.

Default log directory:

```
arapy/arapy/logs/
```

Examples:
- `network_devices.csv`
- `network_device_created.json`
- `endpoints.csv`
- `endpoint_deleted.json`

Override output:

```bash
--out=./custom_file.json
```

---

# 🛠 Installation

## Development (editable)
```bash
pip install -e .
```

## Standard install
```bash
pip install .
```

## With GUI support
```bash
pip install .[gui]
```

---

# 🧠 Error Handling

arapy provides detailed HTTP error visibility:

- Status code
- URL
- Method
- Response body
- Request payload (sensitive fields masked)

Example:

```
HTTP 422 Unprocessable Entity
Vendor name is missing
```

---

# 🏗 Architecture

```
arapy/
├── api_endpoints.py
├── clearpass.py
├── commands.py
├── config.py
├── gui.py
├── io_utils.py
├── main.py
├── logs/
└── tests/
```

### Design Principles

- Clean separation of concerns
- Shared handler logic (CLI + GUI)
- Minimal dependencies
- Extensible module/service/action structure
- Production-safe error reporting

---

# 🛣 Roadmap

Future ideas:

- Token caching
- Auto-pagination handling
- Dynamic GUI forms per action
- Expanded ClearPass API coverage
- Standalone binary packaging
- Extended automated testing

---

# 📄 License

Internal / Custom Use  
© Mathias Granlund

---

**arapy v1.1.3**  
A clean, modular ClearPass API toolkit built for automation and operators alike.