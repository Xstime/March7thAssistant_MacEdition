# March7thAssistant Mac Edition — native-port status

This is an **unofficial Apple Silicon macOS port** of [moesnow/March7thAssistant](https://github.com/moesnow/March7thAssistant). Keep upstream `main` synchronized; all port modifications belong on `macos-native` or feature branches.

## Product decisions

- Distribute an ARM64 native `.app` (and eventually `.dmg`) without Docker, Colima, Rosetta, or a separately installed Python runtime.
- Reuse the existing Python automation and PySide6 GUI wherever practicable.
- Default cloud automation to Chromium headless mode **after** verifying it works on native macOS; do not override explicit user settings.
- Prefer existing CPU OCR engines (ONNX Runtime and OpenVINO after ARM64 correctness testing). No custom Metal development.
- Support a visible-browser fallback for tasks that cannot operate headlessly; never silently report unsupported tasks as successful.
- Preserve user data and the existing Docker installation until a native release is verified.

## First increment (committed)

- `utils/macos_paths.py`: deterministic native per-user paths, with restrictive user-data-directory permissions.
- `module/game/cloud.py`: on macOS, persist Selenium's managed browser profile in Application Support instead of a writable project/bundle directory. Linux and Windows paths are unchanged.
- `tests/test_utils/test_macos_paths.py`: basic path and permissions contract tests.

**Not yet completed:** wiring configuration/logs/resources to macOS writable directories; native GUI/CLI launch; in-app QR login; browser installation; task-mode fallback; signed bundle build; integration/real-game tests.

## Required security review before running the code

The upstream `module/config/__init__.py` contains a platform-gated Base64-decoded `exec` expression. Do not blindly run an unreviewed upstream release or claim a security audit is complete. Determine what the decoded code does, confirm whether it is safe/necessary, and make any proposed changes transparently. Avoid leaking cookies, QR payloads, or session credentials into CI artifacts and logs.

## Integration milestones

1. Audit imports, Windows-only features, frozen-app paths and platform-gated executable code; make `app.py` and `main.py` reliably launch on macOS.
2. Decouple bundled readonly assets from writable configuration, session data, downloads, caches, diagnostics and logs.
3. Make ARM64 Chrome/ChromeDriver lifecycle and Selenium screenshot/input functional; confirm real headless cloud streaming with changing frames.
4. Implement in-app local QR presentation and first-login/persistent-session UX, with bounded retries and privacy precautions.
5. Validate OCR accuracy, coordinates and one actual cloud-game task. Provide per-task headless-compatibility policy.
6. Add repeatable macOS ARM64 packaging and CI smoke tests, then native long-run tests and a distributable bundle.

## Test disclosure

All files in this initial increment are source changes only. GitHub commits do **not** imply that the program has been run or that a usable .app/.dmg exists. Record actual test commands, runner OS/architecture and results separately.
