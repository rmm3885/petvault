ok is this ready to go onto ec2 import sqlite3
import os
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for

# Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

# Database path (local default OR environment override)
DB_PATH = Path(
    os.environ.get(
        "PETVAULT_DB_PATH",
        Path(__file__).with_name("petvault.db")
    )
)

# Ensure database directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            species TEXT NOT NULL,
            breed TEXT,
            notes TEXT,
            deleted INTEGER DEFAULT 0,
            deleted_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/pets")
def pets_list():
    conn = get_db()
    pets = conn.execute(
        "SELECT id, name, species, breed, notes "
        "FROM pets WHERE deleted = 0 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("pets.html", pets=pets)


@app.route("/pets/new", methods=["GET", "POST"])
def pets_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        species = (request.form.get("species") or "").strip()
        breed = (request.form.get("breed") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        if not name or not species:
            return render_template(
                "pet_new.html",
                error="Name and species are required."
            )

        conn = get_db()
        conn.execute(
            "INSERT INTO pets (name, species, breed, notes) VALUES (?, ?, ?, ?)",
            (name, species, breed or None, notes or None),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("pets_list"))

    return render_template("pet_new.html", error=None)


@app.route("/pets/<int:pet_id>/delete", methods=["POST"])
def delete_pet(pet_id):
    conn = get_db()
    conn.execute(
        "UPDATE pets SET deleted = 1, deleted_at = datetime('now') WHERE id = ?",
        (pet_id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("pets_list"))


@app.route("/pets/deleted")
def pets_deleted():
    conn = get_db()
    pets = conn.execute(
        "SELECT id, name, species, breed "
        "FROM pets WHERE deleted = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("pets_deleted.html", pets=pets)


@app.route("/pets/<int:pet_id>/restore", methods=["POST"])
def restore_pet(pet_id):
    conn = get_db()
    conn.execute(
        "UPDATE pets SET deleted = 0, deleted_at = NULL WHERE id = ?",
        (pet_id,),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("pets_deleted"))


@app.route("/pets/<int:pet_id>/purge", methods=["POST"])
def purge_pet(pet_id):
    conn = get_db()
    conn.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("pets_deleted"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
