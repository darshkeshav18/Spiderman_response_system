"""
TEAM CLUB -- MISSION PLANNER

Given Spider-Man's current location and a set of active incidents,
works out the travel distance and route to each one, then recommends
the single best mission. Priority scoring is reused from Team Diamond
rather than reimplemented here.

No GPS, maps, or external services -- the neighbourhood is a fixed,
known graph of direct roads (ROAD_NETWORK below).
"""

import heapq
from typing import Dict, List, Optional, Tuple

from team_diamond import calculate_priority_score


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
    return distances[end], route


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
