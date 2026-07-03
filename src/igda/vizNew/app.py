"""Entrypoint: python src/igda/vizNew/app.py"""

from igda.vizNew.flask_app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5003)
