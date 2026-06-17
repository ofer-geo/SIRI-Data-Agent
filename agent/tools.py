import json
import requests
from config import OPEN_BUS_BASE_URL, HEADERS


# --- Tool functions ---
# These are the actual functions the agent can call.
# Each one returns a plain string — the LLM reads that string as the tool result.

def get_open_bus_endpoints(filter_keyword: str = "") -> str:
    """Discover available Open Bus API endpoints and their query parameters."""
    url = OPEN_BUS_BASE_URL + "/openapi.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        paths = resp.json().get("paths", {})
        lines = []
        for path, methods in sorted(paths.items()):
            if filter_keyword and filter_keyword.lower() not in path.lower():
                continue
            get = methods.get("get")
            if not get:
                continue
            params = [p.get("name") for p in get.get("parameters", [])]
            lines.append(f"{path}\n    params: {', '.join(params) if params else '(none)'}")
        return "\n".join(lines) if lines else f"No endpoints matched '{filter_keyword}'."
    except Exception as e:
        return f"Error fetching API spec: {e}"


def query_open_bus_api(endpoint: str, params_json: str = "{}") -> str:
    """Query an Open Bus STRIDE API list endpoint."""
    try:
        params = json.loads(params_json) if params_json else {}
    except json.JSONDecodeError:
        return f"Invalid params_json (must be a JSON object string): {params_json!r}"
    try:
        resp = requests.get(OPEN_BUS_BASE_URL + endpoint, params=params, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            # Only return first 5 records to keep the response small for the LLM
            preview = data[:5]
            return (f"Returned {len(data)} record(s) (showing first {len(preview)}).\n"
                    + json.dumps(preview, ensure_ascii=False, default=str))
        return json.dumps(data, ensure_ascii=False, default=str)
    except requests.exceptions.HTTPError as e:
        body = resp.text[:500] if "resp" in dir() else ""
        return f"HTTP error: {e}. Response body: {body}"
    except requests.exceptions.RequestException as e:
        return f"Request error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


# --- Tools map ---
# Used by core.py to call the right function by name when the LLM requests a tool call.

tools_map = {
    "get_open_bus_endpoints": get_open_bus_endpoints,
    "query_open_bus_api": query_open_bus_api,
}


# --- Tools schema ---
# Sent to the LLM on every request so it knows what tools exist and how to use them.
# params_json is always a JSON string (not a dict) — that's how function-calling works.

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_open_bus_endpoints",
            "description": (
                "Discover the available Open Bus STRIDE API endpoints and their exact query "
                "parameter names by reading the live OpenAPI spec. Use this FIRST whenever you "
                "are unsure which endpoint or parameter to use, instead of guessing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_keyword": {
                        "type": "string",
                        "description": (
                            "Optional substring to filter endpoints by path, "
                            "e.g. 'siri', 'gtfs', 'vehicle', 'ride'. Leave empty to list all."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_open_bus_api",
            "description": (
                "Query an Open Bus STRIDE API list endpoint (Israeli public transport: "
                "real-time SIRI data and planned GTFS data). Returns JSON records. "
                "Use for bus stops, ride counts, live vehicle locations, and speed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {
                        "type": "string",
                        "description": (
                            "The API path to call, e.g. '/siri_vehicle_locations/list', "
                            "'/gtfs_ride_stops/list', '/gtfs_rides/list'."
                        ),
                    },
                    "params_json": {
                        "type": "string",
                        "description": (
                            "Query parameters as a JSON OBJECT STRING (not a nested object). "
                            "Example: '{\"gtfs_route__route_short_name\": \"189\", \"limit\": 5}'. "
                            "Use '{}' for no parameters."
                        ),
                    },
                },
                "required": ["endpoint"],
            },
        },
    },
]