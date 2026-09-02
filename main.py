"""
SPIDER-MAN NEIGHBOURHOOD RESPONSE SYSTEM -- entry point.

Runs Team Heart (intake), Team Diamond (threat assessment), Team Club
(mission planner) and Team Spade (command centre) together as one
terminal program. This file only owns the top-level menu loop -- all
actual behaviour lives in the four team modules.
"""

from team_heart import IncidentStore
from team_spade import (
    handle_report_incident,
    handle_view_active,
    handle_view_priority,
    handle_next_mission,
    handle_update_incident,
    handle_dashboard,
)


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
