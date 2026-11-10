# Changelog

Rendered by CI and committed back at the end of a release -- do not edit by
hand. Release notes also appear on the GitHub Releases page, one per tag.

## [1.0.16](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.15...v1.0.16) (2026-11-10)

### Bug Fixes

* **pins:** seed new deployments on the 2.2.2-rc.3 stack ([8d8b598](https://github.com/hyperi-io/dfe-deploy/commit/8d8b5989166bcf249fb912004e4bdaef9b31ebb3))

## [1.0.15](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.14...v1.0.15) (2026-11-10)

### Bug Fixes

* **pins:** seed new deployments on the 2.2.2-rc.2 stack ([380b979](https://github.com/hyperi-io/dfe-deploy/commit/380b97967e7b261fc4d20a3bd008e695aef407ae))

## [1.0.14](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.13...v1.0.14) (2026-11-10)

### Bug Fixes

* **docs:** call the search component dfe-hyperdx ([726876a](https://github.com/hyperi-io/dfe-deploy/commit/726876a4cd668f1132455abe414b4e924430092c))

## [1.0.13](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.12...v1.0.13) (2026-11-09)

### Bug Fixes

* **pins:** seed new deployments on the 2.2.2-rc.1 stack ([7addf20](https://github.com/hyperi-io/dfe-deploy/commit/7addf209f6e31fc7448c627fc10bcb1adb1e78de))

## [1.0.12](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.11...v1.0.12) (2026-11-02)

### Bug Fixes

* **pins:** seed new deployments on the 2.2.2 stack ([#21](https://github.com/hyperi-io/dfe-deploy/issues/21)) ([cc422c3](https://github.com/hyperi-io/dfe-deploy/commit/cc422c3363e3d79ed08cdf94b0a9e69e99305c07))

## [1.0.11](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.10...v1.0.11) (2026-11-02)

### Bug Fixes

* **deps:** update actions/setup-python action to v7 ([#20](https://github.com/hyperi-io/dfe-deploy/issues/20)) ([d7ff517](https://github.com/hyperi-io/dfe-deploy/commit/d7ff517b2238902d5b45f6cc5d60d1e210295e10))
* **deps:** update dependency python to 3.15 ([#19](https://github.com/hyperi-io/dfe-deploy/issues/19)) ([e59afb2](https://github.com/hyperi-io/dfe-deploy/commit/e59afb24f106a649fc08f7653b3e32b895e7e175))

## [1.0.10](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.9...v1.0.10) (2026-11-01)

### Bug Fixes

* **governance:** correct validation and release push failures ([#18](https://github.com/hyperi-io/dfe-deploy/issues/18)) ([e3cffa0](https://github.com/hyperi-io/dfe-deploy/commit/e3cffa00960e65b36dd7acaadf357e7f11180342))

## [1.0.9](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.8...v1.0.9) (2026-10-31)

### Bug Fixes

* hold the governance validator to the engine loader and return the receiver to its tier's ceiling ([#16](https://github.com/hyperi-io/dfe-deploy/issues/16)) ([738ba45](https://github.com/hyperi-io/dfe-deploy/commit/738ba45e7b9d2692426b627c7842efb2440bdb83))

## [1.0.8](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.7...v1.0.8) (2026-10-11)

### Bug Fixes

* hunts-pause switches the engine's hunt-runner secret group off too ([#10](https://github.com/hyperi-io/dfe-deploy/issues/10)) ([09a4e56](https://github.com/hyperi-io/dfe-deploy/commit/09a4e569adb0840cd2b0296c8fa9962084e26fd2))

## [1.0.7](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.6...v1.0.7) (2026-10-06)

### Bug Fixes

* drop the cnpg-cluster overlay from the infra README ([#9](https://github.com/hyperi-io/dfe-deploy/issues/9)) ([2b26c08](https://github.com/hyperi-io/dfe-deploy/commit/2b26c088b4744e64f289714030d63f8b41301cc8))

## [1.0.6](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.5...v1.0.6) (2026-10-02)

### Bug Fixes

* **governance:** mirror the engine's KEDA-aware replicaCount rule ([#8](https://github.com/hyperi-io/dfe-deploy/issues/8)) ([a28368c](https://github.com/hyperi-io/dfe-deploy/commit/a28368c472396afb2863487896c242fdc536ffe8)), closes [#710](https://github.com/hyperi-io/dfe-deploy/issues/710)

## [1.0.5](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.4...v1.0.5) (2026-10-02)

### Bug Fixes

* **governance:** lock the sizing keys a chart carries and explain the sizing directory ([#3](https://github.com/hyperi-io/dfe-deploy/issues/3)) ([36a2d5f](https://github.com/hyperi-io/dfe-deploy/commit/36a2d5f8237757dbcd90093ebf55a41113d2536c))

## [1.0.4](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.3...v1.0.4) (2026-09-19)

### Bug Fixes

* **docs:** give the README a Context section and write the architecture doc ([#5](https://github.com/hyperi-io/dfe-deploy/issues/5)) ([31d622d](https://github.com/hyperi-io/dfe-deploy/commit/31d622d1bf16d60aebfda9678c52cc5857cde406))

## [1.0.3](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.2...v1.0.3) (2026-09-17)

### Bug Fixes

* **config:** config/schemas is the engine's additive overlay, not a DDL Job ([#4](https://github.com/hyperi-io/dfe-deploy/issues/4)) ([e3b2ca9](https://github.com/hyperi-io/dfe-deploy/commit/e3b2ca9955b9f805db97c0dea0211e034def0c80))

## [1.0.2](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.1...v1.0.2) (2026-08-30)

### Bug Fixes

* **governance:** follow the storage vocabulary into the template ([83cb869](https://github.com/hyperi-io/dfe-deploy/commit/83cb869ac2ea00ce4ec1b5a984c7ab26e6b3e0fd))

## [1.0.1](https://github.com/hyperi-io/dfe-deploy/compare/v1.0.0...v1.0.1) (2026-08-30)

### Bug Fixes

* document the receiver ingest door in the values standard ([7cae6f6](https://github.com/hyperi-io/dfe-deploy/commit/7cae6f658433459d938338ffb4975f5c84974357))
* document what an instance values file must carry ([1874994](https://github.com/hyperi-io/dfe-deploy/commit/1874994fc0deb428e184f97f80db67baf5452c2b))
* give the substrate and platform charts an overlay of their own ([976a898](https://github.com/hyperi-io/dfe-deploy/commit/976a898787721b5e939a7bf6b3c1f3062853bf63))
* lock the disk too, and write down that counts only go up ([a37b60f](https://github.com/hyperi-io/dfe-deploy/commit/a37b60f202441020b8bba1456b1247dcce86de60))
* name the credential-binding keys beside the seeding instruction ([7f3bea2](https://github.com/hyperi-io/dfe-deploy/commit/7f3bea2c2fa714c262664a48aec85a798bc4be20))

## 1.0.0 (2026-08-06)
