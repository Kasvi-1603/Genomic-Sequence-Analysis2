"""Flask app entrypoint (replaces Streamlit UI)."""

from igda.viz.flask_app import create_app

app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

