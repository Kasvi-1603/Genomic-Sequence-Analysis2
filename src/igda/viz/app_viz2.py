"""Entrypoint for the second-generation Flask dashboard."""

from igda.viz.flask_app_viz2 import create_app_viz2

app = create_app_viz2()


if __name__ == "__main__":
    app.run(debug=True)

