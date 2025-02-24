# Home Assistant Integration Quality Checklist

See <https://developers.home-assistant.io/docs/core/integration-quality-scale/> for more information.

## Bronze

- [ ] `action-setup` - Service actions are registered in async_setup
- [ ] `appropriate-polling` - If it's a polling integration, set an appropriate polling interval
- [ ] `brands` - Has branding assets available for the integration
- [ ] `common-modules` - Place common patterns in common modules
- [ ] `config-flow-test-coverage` - Full test coverage for the config flow
- [ ] `config-flow` - Integration needs to be able to be set up via the UI
  - [ ] Uses `data_description` to give context to fields
  - [ ] Uses `ConfigEntry.data` and `ConfigEntry.options` correctly
- [ ] `dependency-transparency` - Dependency transparency
- [ ] `docs-actions` - The documentation describes the provided service actions that can be used
- [ ] `docs-high-level-description` - The documentation includes a high-level description of the integration brand, product, or service
- [ ] `docs-installation-instructions` - The documentation provides step-by-step installation instructions for the integration, including, if needed, prerequisites
- [ ] `docs-removal-instructions` - The documentation provides removal instructions
- [ ] `entity-event-setup` - Entities event setup
- [ ] `entity-unique-id` - Entities have a unique ID
- [ ] `has-entity-name` - Entities use has_entity_name = True
- [ ] `runtime-data` - Use ConfigEntry.runtime_data to store runtime data
- [ ] `test-before-configure` - Test a connection in the config flow
- [ ] `test-before-setup` - Check during integration initialization if we are able to set it up correctly
- [ ] `unique-config-entry` - Don't allow the same device or service to be able to be set up twice

## Silver

- [ ] `action-exceptions` - Service actions raise exceptions when encountering failures
- [ ] `config-entry-unloading` - Support config entry unloading
- [ ] `docs-configuration-parameters` - The documentation describes all integration configuration options
- [ ] `docs-installation-parameters` - The documentation describes all integration installation parameters
- [ ] `entity-unavailable` - Mark entity unavailable if appropriate
- [ ] `integration-owner` - Has an integration owner
- [ ] `log-when-unavailable` - If internet/device/service is unavailable, log once when unavailable and once when back connected
- [ ] `parallel-updates` - Set Parallel updates
- [ ] `reauthentication-flow` - Reauthentication flow
- [ ] `test-coverage` - Above 95% test coverage for all integration modules

## Gold

- [ ] `devices` - The integration creates devices
- [ ] `diagnostics` - Implements diagnostics
- [ ] `discovery-update-info` - Integration uses discovery info to update network information
- [ ] `discovery` - Can be discovered
- [ ] `docs-data-update` - The documentation describes how data is updated
- [ ] `docs-examples` - The documentation provides automation examples the user can use.
- [ ] `docs-known-limitations` - The documentation describes known limitations of the integration (not to be confused with bugs)
- [ ] `docs-supported-devices` - The documentation describes known supported / unsupported devices
- [ ] `docs-supported-functions` - The documentation describes the supported functionality, including entities, and platforms
- [ ] `docs-troubleshooting` - The documentation provides troubleshooting information
- [ ] `docs-use-cases` - The documentation describes use cases to illustrate how this integration can be used
- [ ] `dynamic-devices` - Devices added after integration setup
- [ ] `entity-category` - Entities are assigned an appropriate EntityCategory
- [ ] `entity-device-class` - Entities use device classes where possible
- [ ] `entity-disabled-by-default` - Integration disables less popular (or noisy) entities
- [ ] `entity-translations` - Entities have translated names
- [ ] `exception-translations` - Exception messages are translatable
- [ ] `icon-translations` - Icon translations
- [ ] `reconfiguration-flow` - Integrations should have a reconfigure flow
- [ ] `repair-issues` - Repair issues and repair flows are used when user intervention is needed
- [ ] `stale-devices` - Clean up stale devices

## Platinum

- [ ] `async-dependency` - Dependency is async
- [ ] `inject-websession` - The integration dependency supports passing in a websession
- [ ] `strict-typing` - Strict typing
