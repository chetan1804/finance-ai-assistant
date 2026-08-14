import json

from dotenv import dotenv_values

from scripts.configure_api_token import configure_api_token


def test_configure_api_token_preserves_env_and_adds_mapping(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("GROQ_API_KEY=existing-provider-key\n", encoding="utf-8")
    token = "test-token-0000000000000000000000000000"

    result = configure_api_token(7, env_path, token=token)
    values = dotenv_values(env_path)

    assert result == token
    assert values["GROQ_API_KEY"] == "existing-provider-key"
    assert json.loads(values["FINANCE_API_TOKENS"]) == {token: 7}
    assert env_path.stat().st_mode & 0o777 == 0o600


def test_configure_api_token_preserves_existing_token_map(tmp_path):
    env_path = tmp_path / ".env"
    first_token = "first-token-000000000000000000000000000"
    second_token = "second-token-00000000000000000000000000"
    env_path.write_text(
        f'FINANCE_API_TOKENS={{"{first_token}":1}}\n',
        encoding="utf-8",
    )

    configure_api_token(2, env_path, token=second_token)
    token_users = json.loads(dotenv_values(env_path)["FINANCE_API_TOKENS"])

    assert token_users == {first_token: 1, second_token: 2}
