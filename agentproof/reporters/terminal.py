from .render import render_markdown


def render_terminal(receipt) -> str:
    return render_markdown(receipt)
