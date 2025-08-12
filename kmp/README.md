Kotlin Multiplatform scaffolding for ImageFlowCanvas

This folder contains the Kotlin Multiplatform (KMP) module structure based on the design docs under `docs/0300_設計_アプローチ1`.

Structure highlights (aligned with 0310/0313 design):
- commonMain: models, repository, usecase, data (DB/sync/cache), network (gRPC/WebSocket/REST), workflow/state, QR decode, and placeholder UI.
- Platform source sets: androidMain, desktopMain, iosMain, thinkletMain, handheldMain for expect/actual implementations (camera, audio, sensor, file, notifications, monitoring, etc.).

Note: This is a file/folder scaffold for developers to fill in; build settings are placeholders.

