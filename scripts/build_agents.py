#!/usr/bin/env python3
"""Build (create/update) Azure AI Foundry agents for the bed-management demo.

This script authenticates with Azure, initializes an AIProjectClient, and
creates the agent constellation defined in the spec. Run as a post-provision
hook via `azd provision` or manually.

Usage:
    python scripts/build_agents.py

Requires env vars:
    PROJECT_CONNECTION_STRING  — Azure AI Foundry project connection string
    MODEL_DEPLOYMENT_NAME      — Model deployment to use (default: gpt-4o)
"""

import json
import os
import sys
from pathlib import Path


def main() -> None:
    connection_string = os.environ.get("PROJECT_CONNECTION_STRING", "")
    model_deployment = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")

    if not connection_string:
        print("ERROR: PROJECT_CONNECTION_STRING not set. Skipping agent creation.", file=sys.stderr)
        sys.exit(1)

    # Authenticate
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient

    credential = DefaultAzureCredential()
    project_client = AIProjectClient.from_connection_string(
        conn_str=connection_string,
        credential=credential,
    )

    prompts_dir = Path(__file__).resolve().parent.parent / "src" / "api" / "app" / "agents" / "prompts"

    # TODO: Define agents — for each agent:
    #   1. Read system prompt from prompts_dir / "{agent_name}.txt"
    #   2. Define tool schemas from Python type annotations
    #   3. Create or update agent via project_client.agents
    #   4. Collect agent_name → agent_id mapping

    agent_definitions = [
        "flow-coordinator",
        "predictive-capacity",
        "bed-allocation",
        "evs-tasking",
        "transport-ops",
    ]

    agent_ids: dict[str, str] = {}

    for agent_name in agent_definitions:
        prompt_file = prompts_dir / f"{agent_name}.txt"
        system_prompt = prompt_file.read_text() if prompt_file.exists() else f"You are the {agent_name} agent."

        # TODO: Create agent via Foundry SDK
        # agent = project_client.agents.create_agent(
        #     model=model_deployment,
        #     name=agent_name,
        #     instructions=system_prompt,
        #     tools=[...],
        # )
        # agent_ids[agent_name] = agent.id
        print(f"  [TODO] Would create agent: {agent_name}")

    # Output the agent ID map as JSON (consumed by the app via AGENT_IDS_JSON env var)
    print(json.dumps(agent_ids, indent=2))


if __name__ == "__main__":
    main()
