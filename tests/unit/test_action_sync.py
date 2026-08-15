from pathlib import Path


def test_root_and_derivative_actions_do_not_drift():
    root = Path(__file__).parents[2]
    root_action = (root / "action.yml").read_text(encoding="utf-8")
    derivative_action = (root / "action" / "action.yml").read_text(encoding="utf-8")
    normalized_root = root_action.replace('pip install "$GITHUB_ACTION_PATH"', 'pip install "$GITHUB_ACTION_PATH/.."')
    assert normalized_root == derivative_action
