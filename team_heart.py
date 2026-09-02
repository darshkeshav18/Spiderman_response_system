"""
TEAM HEART -- INCIDENT INTAKE

Validates incoming incident reports and stores them in memory.
This is the front door: nothing here knows about priority scoring
or mission planning, it only knows how to take in and store a
well-formed incident.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple


# =====================================================================
# CONSTANTS -- the only valid values an incident can hold
# =====================================================================

VALID_INCIDENT_TYPES = {
    "robbery": "Robbery",
    "accident": "Accident",
    "fire": "Fire",
    "medical emergency": "Medical Emergency",
    "missing person": "Missing Person",
    "suspicious activity": "Suspicious Activity",
}

# place name -> display name. This IS the neighbourhood -- also the
# only valid nodes in Team Club's road network.
VALID_LOCATIONS = {
    "queens street": "Queens Street",
    "midtown school": "Midtown School",
    "city hospital": "City Hospital",
    "park avenue": "Park Avenue",
    "queens residence": "Queens Residence",
    "central mall": "Central Mall",
    "police station": "Police Station",
    "metro station": "Metro Station",
}

VALID_SEVERITIES = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
}


# =====================================================================
# VALIDATION -- pure functions, no input()/print() here, so these can
# be unit-tested directly without touching the terminal.
# =====================================================================

def validate_incident_type(raw: str) -> Tuple[bool, str]:
    raw = raw.strip()
    if not raw:
        return False, "Incident type cannot be empty."
    normalized = VALID_INCIDENT_TYPES.get(raw.lower())
    if normalized:
        return True, normalized
    return False, f"Allowed: {', '.join(VALID_INCIDENT_TYPES.values())}"


def validate_location(raw: str) -> Tuple[bool, str]:
    raw = raw.strip()
    if not raw:
        return False, "Location cannot be empty."
    normalized = VALID_LOCATIONS.get(raw.lower())
    if normalized:
        return True, normalized
    return False, f"Allowed: {', '.join(VALID_LOCATIONS.values())}"


def validate_severity(raw: str) -> Tuple[bool, str]:
    normalized = VALID_SEVERITIES.get(raw.strip().lower())
    if normalized:
        return True, normalized
    return False, "Must be LOW, MEDIUM, HIGH, or CRITICAL."


def validate_people_affected(raw: str):
    raw = raw.strip()
    try:
        value = int(raw)
    except ValueError:
        return False, "Please enter a valid non-negative integer."
    if value < 0:
        return False, "Must be a non-negative integer (>= 0)."
    return True, value


def validate_description(raw: str) -> Tuple[bool, str]:
    raw = raw.strip()
    if not raw:
        return False, "Description cannot be empty."
    return True, raw


# =====================================================================
# STORAGE
# =====================================================================

class IncidentStore:
    """In-memory storage and lookup for incidents. Incidents are
    plain dicts -- the shared shape every other module expects.
    """

    def __init__(self):
        self.incidents: Dict[str, dict] = {}
        self._counter = 1

    def _generate_id(self) -> str:
        incident_id = f"INC-{self._counter:03d}"
        self._counter += 1
        return incident_id

    def check_duplicate(self, incident_type: str, location: str) -> Optional[str]:
        for incident in self.incidents.values():
            if incident["type"] == incident_type and incident["location"] == location:
                return incident["id"]
        return None

    def create_incident(self, incident_type, location, severity, people_affected, description) -> dict:
        incident = {
            "id": self._generate_id(),
            "type": incident_type,
            "location": location,
            "severity": severity,
            "people_affected": people_affected,
            "description": description,
            "status": "REPORTED",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reported_at": len(self.incidents) + 1,  # tie-break ordering
        }
        self.incidents[incident["id"]] = incident
        return incident

    def get_incident(self, incident_id: str) -> Optional[dict]:
        return self.incidents.get(incident_id.strip().upper())

    def all(self) -> List[dict]:
        return list(self.incidents.values())

    def active(self) -> List[dict]:
        return [i for i in self.incidents.values() if i["status"] != "RESOLVED"]


# =====================================================================
# TERMINAL PROMPTS -- thin I/O wrappers around the pure validators
# above. Exposed so Team Spade can call these without reimplementing
# validation itself.
# =====================================================================

def prompt_with_validator(message: str, validator) -> str:
    while True:
        raw = input(message)
        ok, result = validator(raw)
        if ok:
            return result
        print(f"\u274c {result}")


def prompt_from_menu(heading: str, options: List[str], validator) -> str:
    """Show a numbered menu of valid options, take a number choice,
    and validate the underlying value through the same pure validator
    used elsewhere -- so this is just a friendlier way to pick from
    the same fixed set, not a separate rule.
    """
    print(f"\n{heading}")
    for position, option in enumerate(options, 1):
        print(f"  {position}. {option}")

    while True:
        raw = input("Choose an option: ").strip()
        if not raw.isdigit() or not (1 <= int(raw) <= len(options)):
            print(f"\u274c Please enter a number from 1 to {len(options)}.")
            continue
        chosen = options[int(raw) - 1]
        ok, result = validator(chosen)
        if ok:
            return result
        print(f"\u274c {result}")  # should not happen -- menu only offers valid values


def prompt_incident_type() -> str:
    return prompt_from_menu("Incident type:", list(VALID_INCIDENT_TYPES.values()), validate_incident_type)


def prompt_location() -> str:
    return prompt_from_menu("Location:", list(VALID_LOCATIONS.values()), validate_location)


def prompt_severity() -> str:
    return prompt_from_menu("Severity:", list(VALID_SEVERITIES.values()), validate_severity)


def prompt_people_affected() -> int:
    return prompt_with_validator("People Affected: ", validate_people_affected)


def prompt_description() -> str:
    return prompt_with_validator("Description: ", validate_description)
