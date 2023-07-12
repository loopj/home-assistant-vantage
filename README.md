# Vantage InFusion integration for Home Assistant

[![GitHub release](https://img.shields.io/github/v/release/loopj/hass-vantage?style=for-the-badge)](http://github.com/loopj/hass-vantage/releases/latest)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Discord](https://img.shields.io/discord/1120862286576353370?style=for-the-badge)](https://discord.gg/j6xdqPJJ)

Home Assistant integration for Vantage InFusion home automation controllers, using [aiovantage](https://github.com/loopj/aiovantage).

## Features

The features of this integration include:

- Control Vantage devices (lights, shades, motion sensors, etc) as [Home Assistant entities](#platforms).
- Trigger automations based on Vantage keypad button presses, using [events](#events).
- Start Vantage tasks from Home Assistant, using [services](#services).
- Automatic Vantage controller discovery (via mDNS).
- UI-based configuration (config flow).
- Entity state updated using [Local Push](https://www.home-assistant.io/blog/2016/02/12/classifying-the-internet-of-things/#classifiers).
- Entities and devices are automatically synchronized upon restart of Home Assistant when changed in Vantage.
- Non-blocking I/O, via asyncio and [aiovantage](https://github.com/loopj/aiovantage).
- Uses SSL connections by default, with automatic reconnection.

## Prerequisites

If your Vantage controller requires authentication (most do by default) you'll need to know a username and password to continue.

If you don't know your username and password, you can reset the password for the *administrator* user if you have physical access to the controller. When resetting your password, it will revert to the serial number of your controller. Alternatively, if you are working with a Vantage dealer, they can provide these credentials.

If you aren't using the default *administrator* user, ensure that the following permissions are enabled for your user: *Read State*, *Write State*, *Read Config*.

## Installation

### Install via HACS

The easiest way to install this integration is by using [HACS](https://hacs.xyz). Once you have HACS installed, simply add <https://github.com/loopj/hass-vantage> as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/), and then restart Home Assistant.

### Manual Install

Alternatively, you can download the [latest release](https://github.com/loopj/hass-vantage/releases/latest/download/vantage.zip) and extract the contents to your Home Assistant `config/custom_components` directory.

## Configuration

### Auto discovery

Vantage controllers should be auto-discovered by Home Assistant. If an instance was found, it will be shown as **Discovered**. You can then set it up right away.

### Manual configuration

If it wasn’t discovered automatically, you can set up a manual integration entry:

- Go to [**Settings > Devices & Services**](https://my.home-assistant.io/redirect/integrations).
- In the bottom right corner, select the [**Add Integration**](https://my.home-assistant.io/redirect/config_flow_start?domain=vantage) button.
- From the list, select **Vantage InFusion**.
- Follow the instructions on screen to complete the setup.

## Platforms

### Lights

Vantage *loads* and *load groups* will appear as lights in Home Assistant, except for loads labeled as *relays* or *motors* in Design Center.

Additionally, color loads connected to a Vantage DMX or DMX/DALI Gateway will appear as lights in Home Assistant.

### Switches

Vantage *loads* labeled as *relays* will appear as switches in Home Assistant. If you have a relay load that you'd like to show up as a different type of entity, you can use the [Change device type of a switch](https://www.home-assistant.io/integrations/switch_as_x/) integration.

Additionally, Vantage *variables* with a type of *Boolean* will appear as switches in Home Assistant.

### Binary Sensors

Vantage *dry contacts* will appear as binary sensors in Home Assistant.

### Numbers

Vantage *variables* with numeric types will appear as numbers in Home Assistant.

### Text

Vantage *variables* with a type of *Text* will appear as text sensors in Home Assistant.

### Sensors

Certain Vantage dimmer modules have built-in power, current, and temperature sensors. These are created as sensors in Home Assistant, but are not enabled by default to reduce clutter. You can enable them from the Home Assistant UI.

### Covers

Supported Vantage *blinds* and *blind groups* will appear as covers in Home Assistant.

## Events

This integration will fire events on the Home Assistant event bus which can be used to trigger automations. You can test events using the [events developer tools](https://my.home-assistant.io/redirect/developer_events/) page in the Home Assistant UI.

### vantage_button_pressed

This event is fired when a button is pressed on a Vantage keypad. The following is an example of the payload:

```json
{
    "button_id": 250,
    "button_name": "Lights",
    "button_position": 1,
    "button_text1": "lights",
    "button_text2": "",
    "station_id": 249,
    "station_name": "Office Keypad"
}
```

| Attribute | Description |
| --- | --- |
| `button_id` | The Vantage ID of the button that was pressed. |
| `button_name` | The name of the button that was pressed. |
| `button_position` | The position on the keypad of the button that was pressed. |
| `button_text1` | The first line of text on the button that was pressed. |
| `button_text2` | The second line of text on the button that was pressed. |
| `station_id` | The Vantage ID of the keypad containing the button that was pressed. |
| `station_name` | The name of the keypad containing the button that was pressed. |

### vantage_button_released

This event is fired when a button is released on a Vantage keypad. It has the same payload as the `vantage_button_pressed` event.

## Services

This integration exposes the following services which can be called from automations.

### vantage.start_task

You can start a Vantage task by calling the `vantage.start_task` service, with either the Vantage ID of the task, or the task's name.

### vantage.stop_task

You can start a Vantage task by calling the `vantage.start_task` service, with either the Vantage ID of the task, or the task's name.
