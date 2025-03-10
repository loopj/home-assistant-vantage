# Vantage InFusion integration for Home Assistant

[![GitHub release](https://img.shields.io/github/v/release/loopj/home-assistant-vantage?style=for-the-badge)](http://github.com/loopj/home-assistant-vantage/releases/latest)
[![Discord](https://img.shields.io/discord/1120862286576353370?style=for-the-badge)](https://discord.gg/psU7PxDyNQ)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

Home Assistant integration for Vantage InFusion home automation controllers, using [aiovantage](https://github.com/loopj/aiovantage).

## Features

The features of this integration include:

- Control Vantage devices (lights, shades, motion sensors, etc) as [Home Assistant entities](#platforms).
- Trigger automations based on Vantage keypad button presses, using [blueprints](#blueprints) or [events](#events).
- Start Vantage tasks from Home Assistant, using [services](#services).
- Automatic Vantage controller discovery (via mDNS).
- UI-based configuration (config flow).
- Entity state updated using [Local Push](https://www.home-assistant.io/blog/2016/02/12/classifying-the-internet-of-things/#classifiers).
- Entities and devices are automatically synchronized when the Vantage system is programmed.
- Non-blocking I/O, via asyncio and [aiovantage](https://github.com/loopj/aiovantage).
- Uses SSL connections by default, with automatic reconnection.
- Works with Vantage InFusion and IC-II controllers running firmware 2.3 and above.

## Prerequisites

If your Vantage controller requires authentication (most do by default) you'll need to know a username and password to continue.

If you don't know your username and password, you can reset the password for the *administrator* user if you have physical access to the controller. When resetting your password, it will revert to the serial number of your controller. Alternatively, if you are working with a Vantage dealer, they can provide these credentials.

If you aren't using the default *administrator* user, ensure that the following permissions are enabled for your user: *Read State*, *Write State*, *Read Config*.

## Installation

The easiest way to install this integration is by using [HACS](https://hacs.xyz).

If you have HACS installed, you can add the Vantage integration by using this My button:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=loopj&repository=home-assistant-vantage&category=integration)

<details>
<summary>
<h4>Manual installation</h4>
</summary>

If you aren't using HACS, you can download the [latest release](https://github.com/loopj/home-assistant-vantage/releases/latest/download/vantage.zip) and extract the contents to your Home Assistant `config/custom_components` directory.
</details>

## Configuration

Adding Vantage to your Home Assistant instance can be done via the user interface, by using this My button:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=vantage)

Vantage can be auto-discovered by Home Assistant. If an instance was found, it will be shown as **Discovered**. You can then set it up right away.

<details>
<summary>
<h4>Manual configuration</h4>
</summary>

If it wasn’t discovered automatically, you can set up a manual integration entry:

- Go to [**Settings > Devices & Services**](https://my.home-assistant.io/redirect/integrations).
- In the bottom right corner, select the [**Add Integration**](https://my.home-assistant.io/redirect/config_flow_start?domain=vantage) button.
- From the list, select **Vantage InFusion**.
- Follow the instructions on screen to complete the setup.

</details>

## Platforms

### Lights

Vantage *Load* and *Load Group* objects will appear as lights in Home Assistant, except for loads labeled as *Relay* or *Motor* in Design Center.

Additionally, color loads connected to a Vantage DMX or DMX/DALI Gateway will appear as lights in Home Assistant.

> [!TIP]
> By default, lights turn on instantly to 100% brightness without ramping. If you'd like to change this behavior, you can use Home Assistant's [light profiles](https://www.home-assistant.io/integrations/light/#default-turn-on-values) feature.

### Switches

Vantage *Load* objects labeled as *Relay* or *Motor* will appear as switches in Home Assistant.

> [!TIP]
> If you have a relay or motor load that you'd like to show up as a different type of entity, you can use the [change device type of a switch](https://www.home-assistant.io/integrations/switch_as_x/) integration.

### Climate

Vantage *Thermostat*, *VirtualThermostat*, *Generic HVAC RS485*, and *HVAC-IU* objects will appear as climate devices in Home Assistant.

### Covers

Vantage *Blind*, *BlindGroup*, *QISBlind*, *QubeBlind*, *RelayBlind*, *Somfy.RS-485*, and *Somfy.URTSI_2* objects will appear as covers in Home Assistant.

### Binary Sensors

Vantage *DryContact* objects (motion sensors, etc) will appear as binary sensors in Home Assistant.

### Sensors

Vantage *AnemoSensor* (wind speed), *LightSensor*, *Temperature*, and *OmniSensor* objects will appear as sensors in Home Assistant.

Certain Vantage dimmer modules have built-in power, current, and temperature sensors exposed as *OmniSensor* objects. These are created as sensors in Home Assistant, but are not enabled by default to reduce clutter. You can enable them from the Home Assistant settings.

### Other Entities

Vantage *GMem* objects (variables) will be created as entities in Home Assistant, but are hidden by default.

Variables with numeric types will be created as number entities, variables with a type of *Boolean* will be created as binary sensor entities, and variables with a type of *Text* will be created as text entities.

## Blueprints

Automation blueprints are pre-made automations that you can easily add to your Home Assistant instance. See the [Home Assistant documentation](https://www.home-assistant.io/docs/automation/using_blueprints/) for more information on how to use blueprints.

This integration provides some pre-made blueprints that are helpful for working with Vantage systems.

### Trigger Actions on Vantage Button Press

See [blueprints/vantage_button_press.yaml](blueprints/vantage_button_press.yaml) for a blueprint that allows you to trigger actions in Home Assistant when a button is pressed or held on a Vantage keypad.

## Events

This integration will fire events on the Home Assistant event bus which can be used to trigger automations. You can test events using the [events developer tools](https://my.home-assistant.io/redirect/developer_events/) page in the Home Assistant UI.

### `vantage_button_pressed`

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

### `vantage_button_released`

This event is fired when a button is released on a Vantage keypad. It has the same payload as the `vantage_button_pressed` event.

### `vantage_task_started`

This event is fired when a Vantage task is started. It's worth noting that this event can be fired multiple times for a single button press, since buttons have press, release, and hold actions, and tasks can be configured to start on any of these actions.

The following is an example of the payload:

```json
{
    "task_id": 683,
    "task_name": "Toggle Office Lights"
}
```

| Attribute | Description |
| --- | --- |
| `task_id` | The Vantage ID of the task that was started. |
| `task_name` | The name of the task that was started. |

### `vantage_task_stopped`

This event is fired when a Vantage task is stopped. It has the same payload as the `vantage_task_started` event.

### `vantage_task_state_changed`

This event is fired when a Vantage task changes it's LED state. The following is an example of the payload:

```json
{
    "task_id": 683,
    "task_name": "Toggle Office Lights",
    "task_state": 1
}
```

| Attribute | Description |
| --- | --- |
| `task_id` | The Vantage ID of the task that changed state. |
| `task_name` | The name of the task that changed state. |
| `task_state` | The new LED state of the task. |

## Services

This integration exposes the following services which can be called from automations.

### `vantage.start_task`

You can start a Vantage task by calling the `vantage.start_task` service, with either the Vantage ID of the task, or the task's name.

### `vantage.stop_task`

You can stop a Vantage task by calling the `vantage.stop_task` service, with either the Vantage ID of the task, or the task's name.
