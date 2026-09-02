"""
TEAM SPADE -- COMMAND CENTRE

The menu-driven front end Spider-Man actually operates. This module
does NOT reimplement incident intake, priority scoring, or mission
planning -- it only orchestrates calls into Team Heart, Team Diamond,
and Team Club and displays the results.
"""

from team_heart import (
    IncidentStore,
    prompt_incident_type,
    prompt_location,
    prompt_severity,
    prompt_people_affected,
    prompt_description,
    prompt_with_validator,
    validate_location,
)
from team_diamond import calculate_priority_score, rank_incidents, get_next_response
from team_club import plan_missions, recommend_mission


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
    current_location = prompt_with_validator("Spider-Man's current location: ", validate_location)

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
    print("Highest priority   :", ranked[0]["id"] if ranked else "NONE")
