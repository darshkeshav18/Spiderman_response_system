"""
TEAM DIAMOND -- THREAT ASSESSMENT

Works out which incidents Spider-Man should respond to, and in what
order. Takes incidents as plain dicts (the shape Team Heart stores
them in) -- no user input is read here.

priority score = severity score + (people affected x 2) + location importance
"""

from typing import Dict, List, Optional


SEVERITY_SCORES = {"LOW": 10, "MEDIUM": 20, "HIGH": 30, "CRITICAL": 40}
POINTS_PER_PERSON_AFFECTED = 2

# Bridges Team Heart's place name (e.g. "City Hospital") to the
# location CATEGORY this scoring model actually cares about.
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

# NOTE: only SCHOOL/HOSPITAL/RESIDENTIAL/PUBLIC/STREET were defined in
# the original Threat Assessment brief. POLICE and TRANSPORT don't
# appear there -- these two values are a placeholder, since Police
# Station / Metro Station only showed up later in Team Club's
# neighbourhood map. Confirm the real numbers before treating as final.
LOCATION_SCORES = {
    "SCHOOL": 4, "HOSPITAL": 4, "RESIDENTIAL": 3, "PUBLIC": 2, "STREET": 1,
    "POLICE": 2, "TRANSPORT": 1,
}


def calculate_priority_score(incident: dict) -> int:
    """Work out one incident's priority score."""
    category = LOCATION_CATEGORY.get(incident["location"], "STREET")
    severity_score = SEVERITY_SCORES[incident["severity"]]
    people_score = incident["people_affected"] * POINTS_PER_PERSON_AFFECTED
    location_score = LOCATION_SCORES.get(category, 0)
    return severity_score + people_score + location_score


def rank_incidents(incidents: List[dict]) -> List[dict]:
    """Return active incidents in response-priority order.

    - A RESOLVED incident is dropped and never appears.
    - Higher priority score comes first.
    - Equal scores are broken by: more people affected wins, then --
      if still equal -- the older incident (smaller reported_at) wins.
    """
    active_incidents = [i for i in incidents if i["status"] != "RESOLVED"]

    # Python's sort is stable, so sorting on the least important key
    # first and the most important key last preserves each earlier
    # tie-break in the final order.
    active_incidents.sort(key=lambda incident: incident["reported_at"])
    active_incidents.sort(key=lambda incident: incident["people_affected"], reverse=True)
    active_incidents.sort(key=calculate_priority_score, reverse=True)

    return active_incidents


def get_next_response(ranked_incidents: List[dict]) -> Optional[dict]:
    """Return the single incident Spider-Man should respond to next."""
    return ranked_incidents[0] if ranked_incidents else None
