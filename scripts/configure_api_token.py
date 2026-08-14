import argparse
import json
import secrets
from pathlib import Path

from dotenv import dotenv_values

from src.security.validation import validate_positive_id


VARIABLE_NAME = "FINANCE_API_TOKENS"


def configure_api_token(user_id: int, env_path=Path(".env"), token=None):
    """Add a generated bearer token without replacing other environment keys."""
    user_id = validate_positive_id(user_id, "user_id")
    env_path = Path(env_path)
    token = token or secrets.token_urlsafe(32)

    if len(token) < 32:
        raise ValueError("API tokens must contain at least 32 characters.")

    existing_text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    existing_value = dotenv_values(env_path).get(VARIABLE_NAME)

    if existing_value:
        try:
            token_users = json.loads(existing_value)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Existing {VARIABLE_NAME} value is not valid JSON."
            ) from error
        if not isinstance(token_users, dict):
            raise ValueError(f"Existing {VARIABLE_NAME} must be a JSON object.")
    else:
        token_users = {}

    token_users[token] = user_id
    replacement = f"{VARIABLE_NAME}={json.dumps(token_users, separators=(',', ':'))}"
    lines = [
        line
        for line in existing_text.splitlines()
        if not line.startswith(f"{VARIABLE_NAME}=")
    ]
    lines.append(replacement)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    env_path.chmod(0o600)
    return token


def main():
    parser = argparse.ArgumentParser(
        description="Generate a local Finance API bearer token."
    )
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args()

    token = configure_api_token(args.user_id, args.env_file)
    print("API token created. Store it securely; it is shown only here:")
    print(token)


if __name__ == "__main__":
    main()
