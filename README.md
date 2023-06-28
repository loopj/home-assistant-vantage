# Vantage InFusion integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

Home Assistant integration for Vantage InFusion home automation controllers, using [aiovantage](https://github.com/loopj/aiovantage).

The features of this integration include:

- Controlling Vantage devices (lights, shades, motion sensors, etc) as Home Assistant entities.
- Automatic Vantage controller discovery (via mDNS).
- UI-based configuration (config flow).
- Entity state updated using [Local Push](https://www.home-assistant.io/blog/2016/02/12/classifying-the-internet-of-things/#classifiers).
- Non-blocking I/O, via asyncio and [aiovantage](https://github.com/loopj/aiovantage).
- Uses SSL connections by default, with automatic reconnection.

## Prerequisites

If your Vantage controller requires authentication (most do by default) you'll need to know a username and password to continue.

If you don't know your username and password, you can reset the password for the *administrator* user if you have physical access to the controller. When resetting your password, it will revert to the serial number of your controller. Alternatively, if you are working with a Vantage dealer, they can provide these credentials.

If you aren't using the default *administrator* user, ensure that the following permissions are enabled for your user: *Read State*, *Write State*, *Read Config*.

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
