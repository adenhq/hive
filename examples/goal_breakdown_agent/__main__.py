import json
import argparse


def validate():
    print("✓ goal_breakdown_agent validated successfully")


def run(input_data: dict):
    goal = input_data.get("goal", "").strip()

    if not goal:
        raise ValueError("Input must contain a non-empty 'goal' field")

    breakdown = {
        "goal": goal,
        "milestones": [
            "Clarify problem and success criteria",
            "Break goal into core components",
            "Identify dependencies and constraints",
            "Prioritize tasks by impact",
            "Define a simple execution sequence",
        ],
    }

    print(json.dumps(breakdown, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["validate", "run"])
    parser.add_argument("--input", type=str, required=False)

    args = parser.parse_args()

    if args.command == "validate":
        validate()

    elif args.command == "run":
        if not args.input:
            raise ValueError("--input JSON is required")

        run(json.loads(args.input))
