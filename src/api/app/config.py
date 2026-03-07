"""Application settings — read from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration for the Bed Management API.

    All values are read from environment variables (case-insensitive).
    """

    # Azure AI Foundry connection — provide one or both
    PROJECT_ENDPOINT: str = ""
    PROJECT_CONNECTION_STRING: str = ""

    # Model deployment used by agents
    MODEL_DEPLOYMENT_NAME: str = "gpt-4o"

    # Optional JSON string mapping agent name → agent ID (populated by build_agents.py)
    AGENT_IDS_JSON: str = "{}"

    # UI theme hint (passed to frontend via /api/state or similar)
    APP_THEME: str = "dark"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
