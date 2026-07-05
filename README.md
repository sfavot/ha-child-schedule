# Child Schedule

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sfavot&repository=ha-child-schedule&category=integration)

Home Assistant integration to manage your child's schedule, including school, activities, holidays, custody, and custom events.

The integration answers one generic question: **"Where is the child right now?"** — whether that is home, school, daycare, an activity, grandparents, a camp, a holiday, or a custody arrangement.

## Concepts

- **Assigned location**: the underlying planned location/responsibility (e.g. `home`).
- **Effective location**: the actual current display location (e.g. `school` during school hours, while still assigned to `home`).
- **Rules**: independent, prioritized rules evaluated by a pure Python engine. The highest priority match wins; ties are broken by stable rule order.

Suggested priorities: default `0`, weekly schedule `10`, school `20`, vacation alternation `30`, date range `40`, exception `80`, manual override `100`.

## Features

- **Schedule editor** in the integration options (no YAML needed):
  - locations (free-form: home, school, father, grandparents, camp…),
  - recurring weekly slots, optionally restricted to odd/even ISO weeks, with optional extension across adjacent public holidays (e.g. a Monday holiday extends the weekend) and configurable handover times,
  - school/daycare settings (days, hours, first school day, bridge days),
  - week/week alternation during school holidays, starting on the first Monday of each holiday period, with the starting location depending on the calendar year parity,
  - one-off date ranges (camps, trips, specific summer arrangements),
  - school holiday dates entered manually **or fetched from the official French calendar** (data.education.gouv.fr) by zone (A, B, C, Corsica).
- **Manual override services** to force a location at any time. Overrides are **persisted** across restarts.
- **Schedule exceptions** (one-off date ranges) via services or the options editor, also persisted.
- French public holidays via the `holidays` package (with static fallback if unavailable).

## Entities

For each child (one config entry per child):

| Entity | Description |
| --- | --- |
| `sensor.<child>_location` | Effective location |
| `sensor.<child>_assigned_location` | Assigned location |
| `sensor.<child>_next_change` | Next schedule change (timestamp) |
| `binary_sensor.<child>_at_home` | On when effective location is `home` |
| `binary_sensor.<child>_at_school` | On when effective location is `school` |
| `device_tracker.<child>_tracker` | Schedule location as a device tracker (for Person entities) |
| `calendar.<child>_schedule` | Custody schedule as all-day calendar events |

All entities expose attributes: `child_name`, `effective_location`, `assigned_location`, `source`, `reason`, `priority`, `period_start`, `period_end`, `next_change`, `iso_week`, `metadata`, `school_holiday_source` (`manual`, `api`, or `api_fallback`).

## Services

- `child_schedule.set_override`: manually force a location (highest priority, persisted).
- `child_schedule.clear_override`: return to the planned schedule.
- `child_schedule.add_exception`: add a one-off exception for a date range (persisted).
- `child_schedule.remove_exception`: remove a persisted exception by ID.

## Installation

### HACS (recommended)

1. Click the badge at the top of this page (or [open in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=sfavot&repository=ha-child-schedule&category=integration)) from your Home Assistant instance. HACS adds the custom repository and opens the install page.
2. Install **Child Schedule** and restart Home Assistant.
3. Add the integration from **Settings → Devices & Services → Add Integration**.

If the link does not work, add `https://github.com/sfavot/ha-child-schedule` manually under **HACS** → **⋮** → **Custom repositories** (category **Integration**), then search for **Child Schedule**.

### Manual

1. Copy `custom_components/child_schedule` into the `custom_components` folder of your Home Assistant configuration.
2. Restart Home Assistant.
3. Add the **Child Schedule** integration from the UI (Settings → Devices & Services → Add Integration).
4. Enter the child's name and default location. Optionally load the demo schedule as a starting example.
5. Open the integration **options** to edit the schedule: locations, weekly slots, school, holidays, one-off periods. Saving applies the new schedule immediately.

## Architecture

- `models/`: pure dataclasses (`Child`, `ScheduleContext`, `ScheduleResult`, `TimelineSegment`).
- `rules/`: generic schedule rules (weekly, school, vacation alternation, date range, exception, manual override).
- `engine/`: pure evaluation engine — current result, next change, timeline. No Home Assistant dependency.
- `schedule_builder.py`: declarative JSON schedule format → engine rules, with validation. Also pure.
- `utils/`: datetime, public holiday, school holiday helpers, and the French school holiday API client.
- `coordinator.py`, `entity.py`, `entities/`, `config_flow.py`: Home Assistant layer (`ConfigEntry` + `DataUpdateCoordinator` + options flow editor). Entities contain no business logic.
- `demo.py`: fictional sample schedule ("Alex"), also used as the demo config in the config flow.

V0 computes `next_change` and the timeline by sampling every 15 minutes over 90 days; this can later be replaced with exact timeline segments. The architecture is ready for external calendar sync (iCloud/Google) and richer editors.

## Development

```bash
uv run --with pytest pytest tests/
```

Tests cover the pure engine, the schedule builder, and the API parsing, and run without Home Assistant.
