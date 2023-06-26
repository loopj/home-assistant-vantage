<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
## Table of Contents

- [Vantage InFusion integration for Home Assistant](#vantage-infusion-integration-for-home-assistant)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

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

If your Vantage controller has authentication enabled (most do by default) you'll need to know the username and password to continue. If you don't have your username and password, it is easy to reset them if you have physical access to the controller, do a google search for "vantage infusion reset password". Alternatively, if you are working with a Vantage dealer, they can provide these credentials.


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
