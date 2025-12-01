"""
Einfache Dienstplanung basierend auf individuellen Dienstwünschen.

Das Skript liest eine JSON-Konfiguration ein, berücksichtigt Wünsche, verteilt
Schichten fair und kann den fertigen Plan als CSV speichern.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class Assignment:
    day: str
    shift: str
    staff: Optional[str]
    preferred: bool


class DutyPlanner:
    def __init__(self, config: Dict):
        self.staff: List[str] = config.get("staff", [])
        self.days: List[str] = config.get("days", [])
        self.shifts: List[str] = config.get("shifts", [])
        self.preferences: Dict[str, Dict[str, List[str]]] = config.get(
            "preferences", {}
        )
        constraints = config.get("constraints", {})
        self.max_shifts_per_staff: Optional[int] = constraints.get(
            "max_shifts_per_staff"
        )

        if not self.staff or not self.days or not self.shifts:
            raise ValueError(
                "Config muss 'staff', 'days' und 'shifts' mit mindestens einem Eintrag enthalten."
            )

        self._assignment_counts: Dict[str, int] = {person: 0 for person in self.staff}

    def _is_under_limit(self, person: str) -> bool:
        if self.max_shifts_per_staff is None:
            return True
        return self._assignment_counts[person] < self.max_shifts_per_staff

    def _candidate_score(self, person: str, day: str, shift: str) -> tuple[int, int, str]:
        wishes = self.preferences.get(person, {}).get(day, [])
        prefers_shift = shift in wishes
        # lower score is better: prefer wished shifts, then fewer assignments, then name
        return (0 if prefers_shift else 1, self._assignment_counts[person], person)

    def generate_schedule(self) -> List[Assignment]:
        schedule: List[Assignment] = []
        for day in self.days:
            assigned_today: set[str] = set()
            for shift in self.shifts:
                candidates = [
                    person
                    for person in self.staff
                    if person not in assigned_today and self._is_under_limit(person)
                ]

                if not candidates:
                    schedule.append(Assignment(day, shift, None, False))
                    continue

                candidates.sort(key=lambda person: self._candidate_score(person, day, shift))
                chosen = candidates[0]
                self._assignment_counts[chosen] += 1
                assigned_today.add(chosen)
                preferred = shift in self.preferences.get(chosen, {}).get(day, [])
                schedule.append(Assignment(day, shift, chosen, preferred))
        return schedule

    @staticmethod
    def save_as_csv(assignments: Iterable[Assignment], destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(["Tag", "Schicht", "Mitarbeiter", "Wunsch erfüllt"])
            for entry in assignments:
                writer.writerow(
                    [
                        entry.day,
                        entry.shift,
                        entry.staff or "nicht besetzt",
                        "ja" if entry.preferred else "nein",
                    ]
                )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Erzeugt einen fairen Dienstplan basierend auf Dienstwünschen und begrenzten Schichten."
        )
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Pfad zur JSON-Konfiguration mit Mitarbeitern, Schichten und Wünschen.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optionaler Pfad zum Speichern des Dienstplans als CSV-Datei.",
    )
    return parser.parse_args()


def _load_config(config_path: Path) -> Dict:
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _print_schedule(schedule: List[Assignment]) -> None:
    print("Fertiger Dienstplan:")
    print("Tag            | Schicht       | Mitarbeiter       | Wunsch")
    print("-" * 62)
    for entry in schedule:
        staff = entry.staff or "nicht besetzt"
        preferred = "(Wunsch)" if entry.preferred else ""
        print(f"{entry.day:<14}| {entry.shift:<13}| {staff:<17}| {preferred}")


if __name__ == "__main__":
    args = _parse_args()
    config = _load_config(args.config)
    planner = DutyPlanner(config)
    result = planner.generate_schedule()
    _print_schedule(result)
    if args.output:
        DutyPlanner.save_as_csv(result, args.output)
        print(f"\nDienstplan gespeichert unter: {args.output}")
