# Plain Performance Notes

This note records the conditions for the main-flow integration test and the 1000-entry verification that were run in Issue #24 for MVP judgement.

## Date

- 2026-03-27

## Environment

- OS: Linux 6.17.0-19-generic
- Python: 3.12.3
- Command: `uv run pytest`

## Automated Checks

- `tests/test_app.py::test_app_main_flow_round_trip_on_live_filesystem`
  - Uses the real filesystem to verify launch, navigation, selection, copy, paste, filter, and sort switching in one scenario
- `tests/test_app.py::test_app_large_directory_smoke_with_1000_entries`
  - Creates 200 directories and 800 files for a total of 1000 entries
  - Verifies the initial render, a 1000-entry list, 150 cursor moves, and continued child-pane updates

## Observations

- `uv run pytest tests/test_app.py -k large_directory_smoke_with_1000_entries --durations=1 -q`
  - `20.30s call     tests/test_app.py::test_app_large_directory_smoke_with_1000_entries`
  - The time above includes test data creation, Textual headless startup, and 150 key sends
- `uv run pytest tests/test_app.py -k 'main_flow_round_trip_on_live_filesystem or large_directory_smoke_with_1000_entries'`
  - `2 passed, 38 deselected in 21.92s`
- Even at the 1000-entry scale, the headless integration smoke test completed successfully, and the symptom where list rendering or child-pane updates stopped midway did not reproduce

## Known Constraints

- The current measurement is a regression-oriented smoke check, not a CI benchmark
- The recorded time is for the full test execution, not an isolated rendering-only measurement
- Perceived speed and scroll rendering cost in a real terminal can vary with the terminal emulator and font settings

## Rerun Commands

```bash
uv run pytest tests/test_app.py -k large_directory_smoke_with_1000_entries --durations=1 -q
uv run pytest tests/test_app.py -k main_flow_round_trip_on_live_filesystem -q
```
