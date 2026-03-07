#!/usr/bin/env python3
"""Build (create/update) Azure AI Foundry agents for the bed-management demo.

Authenticates with Azure, initializes an AIProjectClient, and creates or
updates the agent constellation. Run as a post-provision hook or manually.

Usage:
    python scripts/build_agents.py

Requires env vars (one of):
    PROJECT_ENDPOINT           — Azure AI Foundry project endpoint (preferred)
    PROJECT_CONNECTION_STRING  — Azure AI Foundry project connection string (fallback)

Optional:
    MODEL_DEPLOYMENT_NAME      — Model deployment to use (default: gpt-4o)
"""

import json
import os
import sys
from pathlib import Path

# Agent tool mapping — imported at runtime so we don't need the full app env
AGENT_NAMES = [
    "flow-coordinator",
    "predictive-capacity",
    "bed-allocation",
    "evs-tasking",
    "transport-ops",
    "policy-safety",
]

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "src" / "api" / "app" / "agents" / "prompts"


def _get_project_client():
    """Create an AIProjectClient using endpoint (preferred) or connection string."""
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()

    endpoint = os.environ.get("PROJECT_ENDPOINT", "").strip()
    conn_str = os.environ.get("PROJECT_CONNECTION_STRING", "").strip()

    if endpoint:
        print(f"Using PROJECT_ENDPOINT: {endpoint[:40]}...")
        return AIProjectClient(endpoint=endpoint, credential=credential)
    elif conn_str:
        print("Using PROJECT_CONNECTION_STRING")
        return AIProjectClient.from_connection_string(conn_str=conn_str, credential=credential)
    else:
        print("ERROR: Neither PROJECT_ENDPOINT nor PROJECT_CONNECTION_STRING is set.", file=sys.stderr)
        sys.exit(1)


def _load_tool_schemas() -> dict[str, list[dict]]:
    """Import tool schemas from the app package."""
    # Add the api source to path so we can import app modules
    api_src = Path(__file__).resolve().parent.parent / "src" / "api"
    if str(api_src) not in sys.path:
        sys.path.insert(0, str(api_src))

    from app.tools.tool_schemas import AGENT_TOOLS
    return AGENT_TOOLS


def _find_existing_agents(agents_client) -> dict[str, str]:
    """List existing agents and return a name→id mapping."""
    existing: dict[str, str] = {}
    try:
        agent_list = agents_client.list_agents()
        for agent in agent_list:
            if agent.name in AGENT_NAMES:
                existing[agent.name] = agent.id
    except Exception as exc:
        print(f"  Warning: Could not list existing agents: {exc}", file=sys.stderr)
    return existing


def main() -> None:
    model_deployment = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")

    project_client = _get_project_client()
    agents_client = project_client.agents

    tool_schemas = _load_tool_schemas()
    existing_agents = _find_existing_agents(agents_client)

    agent_ids: dict[str, str] = {}

    for agent_name in AGENT_NAMES:
        # Read system prompt
        prompt_file = PROMPTS_DIR / f"{agent_name}.txt"
        if prompt_file.exists():
            system_prompt = prompt_file.read_text().strip()
        else:
            print(f"  Warning: No prompt file for {agent_name}, using default", file=sys.stderr)
            system_prompt = f"You are the {agent_name} agent for the hospital bed management system."

        tools = tool_schemas.get(agent_name, [])

        if agent_name in existing_agents:
            # Update existing agent
            agent_id = existing_agents[agent_name]
            print(f"  Updating agent: {agent_name} (id={agent_id})")
            try:
                agent = agents_client.update_agent(
                    assistant_id=agent_id,
                    model=model_deployment,
                    name=agent_name,
                    instructions=system_prompt,
                    tools=tools,
                )
                agent_ids[agent_name] = agent.id
            except Exception as exc:
                print(f"  Error updating {agent_name}: {exc}", file=sys.stderr)
                agent_ids[agent_name] = agent_id  # keep old ID
        else:
            # Create new agent
            print(f"  Creating agent: {agent_name}")
            try:
                agent = agents_client.create_agent(
                    model=model_deployment,
                    name=agent_name,
                    instructions=system_prompt,
                    tools=tools,
                )
                agent_ids[agent_name] = agent.id
                print(f"  Created: {agent_name} → {agent.id}")
            except Exception as exc:
                print(f"  Error creating {agent_name}: {exc}", file=sys.stderr)

    # Output the agent ID map as JSON (consumed by the app via AGENT_IDS_JSON env var)
    output = json.dumps(agent_ids, indent=2)
    print(f"\nAgent IDs:\n{output}")

    # Also write to a file for convenience
    output_file = Path(__file__).resolve().parent / "agent_ids.json"
    output_file.write_text(output)
    print(f"Written to {output_file}")


if __name__ == "__main__":
    main()
