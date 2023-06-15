# Home Assistant integration for Vantage

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

Home Assistant integration for Vantage InFusion home automation controllers, using [aiovantage](https://github.com/loopj/aiovantage).


## Features

- Supports lights, shades, and dry contacts.
- Automatic Vantage controller discovery via mDNS.
- UI-based configuration (config flow).
- Uses Python asyncio for non-blocking I/O, via [aiovantage](https://github.com/loopj/aiovantage).
- Uses SSL connections by default, with automatic reconnection.


## Installation

### Install via HACS

Add <https://github.com/loopj/hass-vantage> as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/).

### Manual Install

Place the the folder `custom_components/vantage` in `YOUR_CONFIG_DIR/custom_components/`.


## Configuration

### Auto discovery

Vantage controllers should be auto-discovered by Home Assistant. If an instance was found, it will be shown as **Discovered**. You can then set it up right away.

### Manual configuration

If it wasn’t discovered automatically, you can set up a manual integration entry:

- Go to [**Settings > Devices & Services**](https://my.home-assistant.io/redirect/integrations).
- In the bottom right corner, select the [**Add Integration**](https://my.home-assistant.io/redirect/config_flow_start?domain=vantage) button.
- From the list, select **Vantage InFusion**.
- Follow the instructions on screen to complete the setup.
