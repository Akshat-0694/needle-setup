import argparse
from app.registry import run, AGENTS

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")

    r = sub.add_parser("run")
    r.add_argument("prompt", nargs="+")
    r.add_argument("--agent", default="research", choices=sorted(AGENTS))

    args = parser.parse_args()

    if args.command == "doctor":
        import needle
        print("Needle import: OK")
        print("Agents:", ", ".join(sorted(AGENTS)))
        return

    prompt = " ".join(args.prompt)
    result = run(args.agent, prompt)
    print(result)

if __name__ == "__main__":
    main()
