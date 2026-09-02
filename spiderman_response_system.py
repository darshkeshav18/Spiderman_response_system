"""
SPIDER-MAN NEIGHBOURHOOD RESPONSE SYSTEM -- Unified Command Centre

Combines all four modules into one terminal program, with each team's
logic living in exactly one place and everything else calling into it:

  - Team Heart   : incident intake, validation, storage, lookup
  - Team Diamond : threat assessment / priority scoring / ranking
  - Team Club    : mission planning -- routing + mission scoring
  - Team Spade   : the command centre -- menu, orchestration only

No database, no external services, no web. Everything lives in memory
for the lifetime of the running program.
"""

import heapq
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# =====================================================================
# SHARED CONSTANTS -- the neighbourhood, incident types, severities
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
# only valid nodes in the road network used by the Mission Planner.
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

# Bridges a place name (what incidents store) to the location
# CATEGORY that Threat Assessment's scoring model expects.
LOCATION_CATEGORY = {
    "Queens Street": "STREET",
    "Midtown School": "SCHOOL",
    "Park Avenue": "STREET",
    "Queens Residence": "RESIDENTIAL",
    "Central Mall": "PUBLIC",
    "City Hospital": "HOSPITAL",
    "Police Station": "POLICE",
    "Metro Station": "TRANSPORT",
}

# The only direct roads. Every step in a route must be a real road.
ROAD_NETWORK: Dict[str, Dict[str, int]] = {
    "Queens Street":    {"Midtown School": 4, "City Hospital": 6, "Queens Residence": 3},
    "Midtown School":   {"Queens Street": 4, "Park Avenue": 3, "City Hospital": 5},
    "City Hospital":    {"Queens Street": 6, "Midtown School": 5, "Police Station": 5},
    "Park Avenue":      {"Midtown School": 3, "Queens Residence": 2, "Central Mall": 4},
    "Queens Residence": {"Queens Street": 3, "Park Avenue": 2},
    "Central Mall":     {"Park Avenue": 4, "Police Station": 2, "Metro Station": 3},
    "Police Station":   {"City Hospital": 5, "Central Mall": 2, "Metro Station": 4},
    "Metro Station":    {"Central Mall": 3, "Police Station": 4},
}


# =====================================================================
# TEAM DIAMOND -- THREAT ASSESSMENT (priority scoring & ranking)
# =====================================================================

SEVERITY_SCORES = {"LOW": 10, "MEDIUM": 20, "HIGH": 30, "CRITICAL": 40}
POINTS_PER_PERSON_AFFECTED = 2

# NOTE: only SCHOOL/HOSPITAL/RESIDENTIAL/PUBLIC/STREET were defined in
# the original Threat Assessment brief. POLICE and TRANSPORT don't
# appear there -- these two values are a placeholder, not a spec'd
# number, since Police Station / Metro Station showed up later in the
# Mission Planner's neighbourhood. Confirm before treating as final.
LOCATION_SCORES = {
    "SCHOOL": 4, "HOSPITAL": 4, "RESIDENTIAL": 3, "PUBLIC": 2, "STREET": 1,
    "POLICE": 2, "TRANSPORT": 1,
}


def calculate_priority_score(incident: dict) -> int:
    """priority score = severity score + (people affected x 2) + location importance"""
    category = LOCATION_CATEGORY.get(incident["location"], "STREET")
    severity_score = SEVERITY_SCORES[incident["severity"]]
    people_score = incident["people_affected"] * POINTS_PER_PERSON_AFFECTED
    location_score = LOCATION_SCORES.get(category, 0)
    return severity_score + people_score + location_score


def rank_incidents(incidents: List[dict]) -> List[dict]:
    """Active incidents in response-priority order.
    RESOLVED incidents are dropped. Ties break by: more people
    affected wins, then the older incident (smaller reported_at) wins.
    """
    active = [i for i in incidents if i["status"] != "RESOLVED"]

    # Stable sorts, least important rule first -- each later sort only
    # rearranges the ties left over from the one before it.
    active.sort(key=lambda i: i["reported_at"])
    active.sort(key=lambda i: i["people_affected"], reverse=True)
    active.sort(key=calculate_priority_score, reverse=True)
    return active


def get_next_response(ranked_incidents: List[dict]) -> Optional[dict]:
    return ranked_incidents[0] if ranked_incidents else None


# =====================================================================
# TEAM CLUB -- MISSION PLANNER (routing + mission scoring)
# =====================================================================

def is_valid_location(location: str) -> bool:
    return location in ROAD_NETWORK


def find_route(start: str, end: str) -> Optional[Tuple[int, List[str]]]:
    """Shortest (distance, route) from start to end via ROAD_NETWORK,
    or None if either location is unknown or no path exists.
    Same start and end -> distance 0.
    """
    if start not in ROAD_NETWORK or end not in ROAD_NETWORK:
        return None
    if start == end:
        return 0, [start]

    distances = {node: float("inf") for node in ROAD_NETWORK}
    previous: Dict[str, Optional[str]] = {node: None for node in ROAD_NETWORK}
    distances[start] = 0
    queue = [(0, start)]
    visited = set()

    while queue:
        current_distance, current = heapq.heappop(queue)
        if current in visited:
            continue
        visited.add(current)
        if current == end:
            break
        for neighbour, road_length in ROAD_NETWORK[current].items():
            new_distance = current_distance + road_length
            if new_distance < distances[neighbour]:
                distances[neighbour] = new_distance
                previous[neighbour] = current
                heapq.heappush(queue, (new_distance, neighbour))

    if distances[end] == float("inf"):
        return None

    route, node = [], end
    while node is not None:
        route.append(node)
        node = previous[node]
    route.reverse()
    return int(distances[end]), route


def calculate_mission_score(incident: dict, distance: int) -> int:
    return calculate_priority_score(incident) - distance


def _mission_sort_key(plan: dict) -> tuple:
    """Highest mission score first. Ties: higher priority score wins,
    then shorter distance wins, then the older incident wins."""
    incident = plan["incident"]
    return (
        plan["mission_score"],
        calculate_priority_score(incident),
        -plan["distance"],
        -incident["reported_at"],
    )


def plan_missions(current_location: str, incidents: List[dict]) -> List[dict]:
    """Route + mission score for every reachable incident.
    Unreachable / invalid-location incidents are skipped, not crashed on.
    """
    plans = []
    for incident in incidents:
        result = find_route(current_location, incident["location"])
        if result is None:
            continue
        distance, route = result
        plans.append({
            "incident": incident,
            "distance": distance,
            "route": route,
            "mission_score": calculate_mission_score(incident, distance),
        })
    plans.sort(key=_mission_sort_key, reverse=True)
    return plans


def recommend_mission(current_location: str, incidents: List[dict]) -> Optional[dict]:
    plans = plan_missions(current_location, incidents)
    return plans[0] if plans else None


# =====================================================================
# TEAM HEART -- INCIDENT INTAKE (validation + storage)
# =====================================================================

# ---- pure validation: no input()/print() here, so these are testable
# on their own without touching the terminal. ----

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


class IncidentStore:
    """In-memory storage and lookup for incidents. Incidents are
    plain dicts (shared shape used by every module in this file).
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


# ---- thin I/O wrappers around the pure validators ----

def _prompt(message: str, validator) -> str:
    while True:
        raw = input(message)
        ok, result = validator(raw)
        if ok:
            return result
        print(f"\u274c {result}")


def prompt_incident_type() -> str:
    return _prompt("Type: ", validate_incident_type)


def prompt_location() -> str:
    return _prompt("Location: ", validate_location)


def prompt_severity() -> str:
    return _prompt("Severity (LOW/MEDIUM/HIGH/CRITICAL): ", validate_severity)


def prompt_people_affected() -> int:
    return int(_prompt("People Affected: ", validate_people_affected))


def prompt_description() -> str:
    return _prompt("Description: ", validate_description)


# =====================================================================
# TEAM SPADE -- COMMAND CENTRE (orchestration only, no reimplemented logic)
# =====================================================================

def handle_report_incident(store: IncidentStore) -> None:
    print("\n===== REPORT INCIDENT =====")
    incident_type = prompt_incident_type()
    location = prompt_location()

    duplicate_id = store.check_duplicate(incident_type, location)
    if duplicate_id:
        print(f"\n\u26a0  POSSIBLE DUPLICATE: {duplicate_id} ({incident_type} at {location})")
        if input("Continue anyway? (y/n): ").strip().lower() not in ("y", "yes"):
            print("Report not saved.")
            return

    severity = prompt_severity()
    people_affected = prompt_people_affected()
    description = prompt_description()

    incident = store.create_incident(incident_type, location, severity, people_affected, description)
    print(f"\n\u2713 Incident created: {incident['id']}  Status: {incident['status']}")
    if severity == "CRITICAL":
        print("\u26a0 SPIDER-SENSE: CRITICAL THREAT DETECTED!")


def handle_view_active(store: IncidentStore) -> None:
    print("\n===== ACTIVE INCIDENTS =====")
    active = store.active()
    if not active:
        print("\u2713 Neighbourhood clear.")
        return
    for incident in active:
        print(
            f"\n{incident['id']} | {incident['type']} | {incident['location']}"
            f"\nSeverity: {incident['severity']} | Affected: {incident['people_affected']}"
            f" | Status: {incident['status']}"
        )


def handle_view_priority(store: IncidentStore) -> None:
    print("\n===== RESPONSE PRIORITY =====")
    ranked = rank_incidents(store.all())
    if not ranked:
        print("No active incidents.")
        return
    for position, incident in enumerate(ranked, 1):
        score = calculate_priority_score(incident)
        print(f"{position}. {incident['id']}  {incident['severity']:<9}{incident['location']:<18}Score: {score}")

    print("\nNEXT RESPONSE:")
    next_incident = get_next_response(ranked)
    print(next_incident["id"] if next_incident else "None")


def handle_next_mission(store: IncidentStore) -> None:
    print("\n===== GET NEXT MISSION =====")
    current_location = _prompt("Spider-Man's current location: ", validate_location)

    active = store.active()
    if not active:
        print("\u2713 No active incidents available.")
        return

    plans_by_id = {p["incident"]["id"]: p for p in plan_missions(current_location, active)}
    print("\nAVAILABLE INCIDENTS\n")
    for incident in active:
        plan = plans_by_id.get(incident["id"])
        priority = calculate_priority_score(incident)
        if plan is None:
            print(f"{incident['id']}  {incident['location']}\nPriority: {priority}  Distance: unreachable\n")
        else:
            print(f"{incident['id']}  {incident['location']}\nPriority: {priority}  Distance: {plan['distance']} km\n")

    best = recommend_mission(current_location, active)
    if best is None:
        print("No reachable incidents. No mission can be recommended.")
        return

    print("\U0001f577 RECOMMENDED MISSION")
    print("----------------------------")
    print("Incident :", best["incident"]["id"])
    print("Type     :", best["incident"]["type"])
    print("Location :", best["incident"]["location"])
    print("Priority :", calculate_priority_score(best["incident"]))
    print("Distance :", best["distance"], "km")
    print("Score    :", best["mission_score"])
    print("Route    :", " -> ".join(best["route"]))
    print("----------------------------")


def handle_update_incident(store: IncidentStore) -> None:
    print("\n===== UPDATE INCIDENT =====")
    incident_id = input("Incident ID: ").strip()
    incident = store.get_incident(incident_id)

    if not incident:
        print("\u2717 Incident not found.")
        return

    if incident["status"] == "REPORTED":
        print("1. Move to IN_PROGRESS\n2. Cancel")
        if input("Choose: ").strip() == "1":
            incident["status"] = "IN_PROGRESS"
            print("\u2713 REPORTED \u2192 IN_PROGRESS")
    elif incident["status"] == "IN_PROGRESS":
        print("1. Move to RESOLVED\n2. Cancel")
        if input("Choose: ").strip() == "1":
            incident["status"] = "RESOLVED"
            print("\u2713 IN_PROGRESS \u2192 RESOLVED")
            print("\U0001f577 SPIDER-SENSE: THREAT NEUTRALIZED!")
    else:
        print("This incident is already resolved.")


def handle_dashboard(store: IncidentStore) -> None:
    print("\n===== OPERATIONAL DASHBOARD =====")
    all_incidents = store.all()
    active = store.active()

    print("Total incidents    :", len(all_incidents))
    print("Active incidents   :", len(active))
    print("Critical incidents :", sum(i["severity"] == "CRITICAL" for i in all_incidents))
    print("In progress        :", sum(i["status"] == "IN_PROGRESS" for i in all_incidents))
    print("Resolved           :", sum(i["status"] == "RESOLVED" for i in all_incidents))

    ranked = rank_incidents(all_incidents)
    if ranked:
        print("Highest priority   :", ranked[0]["id"])
    else:
        print("Highest priority   : NONE")


def main() -> None:
    store = IncidentStore()

    print("\n" + "=" * 50)
    print("       \U0001f577 SPIDER-MAN NEIGHBOURHOOD RESPONSE SYSTEM")
    print("=" * 50)

    while True:
        print("""
1. Report Incident
2. View Active Incidents
3. View Response Priority
4. Get Next Mission
5. Update Incident
6. View Dashboard
7. Exit
""")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            handle_report_incident(store)
        elif choice == "2":
            handle_view_active(store)
        elif choice == "3":
            handle_view_priority(store)
        elif choice == "4":
            handle_next_mission(store)
        elif choice == "5":
            handle_update_incident(store)
        elif choice == "6":
            handle_dashboard(store)
        elif choice == "7":
            print("\n\U0001f577 Command Centre offline. Stay safe!")
            break
        else:
            print("\u2717 Invalid option. Choose 1-7.")


if __name__ == "__main__":
    main()
