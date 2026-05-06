from homeassistant.const import Platform


DOMAIN = "roborock_q10_map"

CONF_ROBOTS = "robots"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_NAME = "Roborock Q10 Map Bridge"
DEFAULT_POLL_INTERVAL = 5
DEFAULT_ROBOTS = "vacuum.example_q10_downstairs,vacuum.example_q10_upstairs"

PLATFORMS = [Platform.SENSOR, Platform.CAMERA]

DEFAULT_FLOORPLAN_WIDTH = 1920
DEFAULT_FLOORPLAN_HEIGHT = 1080

# Replace these placeholder values with calibration for the target installation.
# Keep entity IDs aligned with the vacuum entities configured in the integration.
DEFAULT_CALIBRATION = {
    "vacuum.example_q10_downstairs": {
        "map_id": None,
        "trace_bounds": {"min_x": -2000, "max_x": 2000, "min_y": -2000, "max_y": 2000},
        "floorplan_box_pct": {
            "center_x": 25.0,
            "center_y": 50.0,
            "width": 40.0,
            "height": 70.0,
            "rotate": 0,
            "source_width": 1000,
            "source_height": 1000,
        },
        "axis": {"flip_x": False, "flip_y": True},
        "marker": {"theme": "white", "scale": 1.25},
    },
    "vacuum.example_q10_upstairs": {
        "map_id": None,
        "trace_bounds": {"min_x": -2000, "max_x": 2000, "min_y": -2000, "max_y": 2000},
        "floorplan_box_pct": {
            "center_x": 75.0,
            "center_y": 50.0,
            "width": 40.0,
            "height": 70.0,
            "rotate": 0,
            "source_width": 1000,
            "source_height": 1000,
        },
        "axis": {"flip_x": False, "flip_y": True},
        "marker": {"theme": "black", "scale": 1.25},
    },
}
