# Changelog

## [1.0.0](https://github.com/KRoperUK/uw-hass/compare/v0.4.0...v1.0.0) (2026-11-23)


### ⚠ BREAKING CHANGES

* password authentication and the email/password config step are removed. Existing password entries must be reauthenticated with a browser session.

### Features

* sign in with a browser session only ([4137da6](https://github.com/KRoperUK/uw-hass/commit/4137da64b2c1e6a4377b596d8927a38c0d026b5d))

## [0.4.0](https://github.com/KRoperUK/uw-hass/compare/v0.3.2...v0.4.0) (2026-11-23)


### Features

* add redacted diagnostics ([c5c7084](https://github.com/KRoperUK/uw-hass/commit/c5c708425e01a15e48c529a002693cd12622c602))
* add redacted diagnostics ([b1fe6cc](https://github.com/KRoperUK/uw-hass/commit/b1fe6cc093d32d74215c0f940e6613560ca0115b))

## [0.3.2](https://github.com/KRoperUK/uw-hass/compare/v0.3.1...v0.3.2) (2026-11-23)


### Bug Fixes

* **ci:** tolerate missing tags when pruning dev releases ([63ed94c](https://github.com/KRoperUK/uw-hass/commit/63ed94c60d09295f54db57024ea91a4ae87192f9))
* **ci:** tolerate missing tags when pruning dev releases ([801af9e](https://github.com/KRoperUK/uw-hass/commit/801af9ec2c2314d9be89d78145a2e184d7f4f9c3))
* report real meter readings and the newest bill ([16831b2](https://github.com/KRoperUK/uw-hass/commit/16831b27285a0bb68bcf20159314aea3f3e264c6))
* report real meter readings and the newest bill ([04c29da](https://github.com/KRoperUK/uw-hass/commit/04c29da66fa231baf06ee322fa4e17f212f9aa7a))

## [0.3.1](https://github.com/KRoperUK/uw-hass/compare/v0.3.0...v0.3.1) (2026-11-23)


### Bug Fixes

* degrade softly when the browser session expires ([9f70a73](https://github.com/KRoperUK/uw-hass/commit/9f70a7317e048ed03114536785a16f297fb2b4be))
* degrade softly when the browser session expires ([c227ec1](https://github.com/KRoperUK/uw-hass/commit/c227ec1612bfe4ca8aab2c941233efe6b9437465))

## [0.3.0](https://github.com/KRoperUK/uw-hass/compare/v0.2.1...v0.3.0) (2026-11-23)


### Features

* set up with an imported browser session ([2817147](https://github.com/KRoperUK/uw-hass/commit/281714750c4ab6df9f50442cbc58607545605552))
* set up with an imported browser session ([2cfb64f](https://github.com/KRoperUK/uw-hass/commit/2cfb64fd1ec785cd2d4c0d03c0fe51d77bab1725))


### Bug Fixes

* **config-flow:** log setup stage and map API errors without breaking auth ([2ec7f98](https://github.com/KRoperUK/uw-hass/commit/2ec7f981f9cbf9d785d0d9fb43ab2a2bd8354e5c)), closes [#23](https://github.com/KRoperUK/uw-hass/issues/23)

## [0.2.1](https://github.com/KRoperUK/uw-hass/compare/v0.2.0...v0.2.1) (2026-09-15)


### Bug Fixes

* bump uw-api to 0.2.1 (lazy client, blocking SSL fix) ([#5](https://github.com/KRoperUK/uw-hass/issues/5)) ([50c7a7e](https://github.com/KRoperUK/uw-hass/commit/50c7a7ef5b0d3cf7b6779579d7893a6fc70e24e5))
* use HA httpx_client helper to avoid blocking SSL init ([fd4b69b](https://github.com/KRoperUK/uw-hass/commit/fd4b69b0bd98b5f162257e27b23588318fe215a1))
