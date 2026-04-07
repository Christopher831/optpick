"""
An Optimal Samples Selection System
Flask web application for CS360/SE360 AI Group Project
"""

import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.middleware.proxy_fix import ProxyFix
from authlib.integrations.flask_client import OAuth

from algorithm import compute_optimal_groups, random_select_samples, validate_params

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_for=1)

# Persistent secret key
SECRET_KEY_FILE = os.path.join(os.path.dirname(__file__), ".secret_key")
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, "rb") as f:
        app.secret_key = f.read()
else:
    app.secret_key = os.urandom(32)
    with open(SECRET_KEY_FILE, "wb") as f:
        f.write(app.secret_key)
    os.chmod(SECRET_KEY_FILE, 0o600)

# Google OAuth
oauth = OAuth(app)
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

DB_PATH = os.path.join(os.path.dirname(__file__), "samples.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            name TEXT NOT NULL,
            picture TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            m INTEGER NOT NULL,
            n INTEGER NOT NULL,
            k INTEGER NOT NULL,
            j INTEGER NOT NULL,
            s INTEGER NOT NULL,
            run_number INTEGER NOT NULL,
            num_groups INTEGER NOT NULL,
            samples TEXT NOT NULL,
            groups_data TEXT NOT NULL,
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migrate: add user_id column if missing
    cols = [row[1] for row in conn.execute("PRAGMA table_info(results)").fetchall()]
    if "user_id" not in cols:
        conn.execute("ALTER TABLE results ADD COLUMN user_id INTEGER REFERENCES users(id)")
    conn.commit()
    conn.close()


def get_next_run_number(m, n, k, j, s, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(MAX(run_number), 0) + 1 FROM results WHERE m=? AND n=? AND k=? AND j=? AND s=? AND user_id=?",
        (m, n, k, j, s, user_id)
    ).fetchone()
    conn.close()
    return row[0]


@app.context_processor
def inject_user():
    return {"current_user": session.get("user")}


# --------------- Auth Routes ---------------

@app.route("/")
def index():
    if session.get("user"):
        return redirect(url_for("app_index"))
    return render_template("login.html")


@app.route("/app")
def app_index():
    if not session.get("user"):
        return redirect(url_for("index"))
    return render_template("index.html")


@app.route("/auth/login")
def auth_login():
    redirect_uri = url_for("auth_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def auth_callback():
    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo")
    if not userinfo:
        flash("Login failed.", "error")
        return redirect(url_for("index"))

    google_id = userinfo["sub"]
    email = userinfo.get("email", "")
    name = userinfo.get("name", "")
    picture = userinfo.get("picture", "")

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE google_id=?", (google_id,)).fetchone()
    if existing:
        conn.execute("UPDATE users SET last_login=?, name=?, email=?, picture=? WHERE google_id=?",
                      (datetime.now(), name, email, picture, google_id))
        user_id = existing["id"]
    else:
        cur = conn.execute("INSERT INTO users (google_id, email, name, picture) VALUES (?,?,?,?)",
                           (google_id, email, name, picture))
        user_id = cur.lastrowid
    conn.commit()
    conn.close()

    session["user"] = {"id": user_id, "name": name, "email": email, "picture": picture, "is_guest": False}
    return redirect(url_for("app_index"))


@app.route("/auth/guest")
def auth_guest():
    session["user"] = {"id": None, "name": "Guest", "email": None, "picture": None, "is_guest": True}
    return redirect(url_for("app_index"))


@app.route("/auth/logout")
def auth_logout():
    session.pop("user", None)
    return redirect(url_for("index"))


# --------------- App Routes ---------------

@app.route("/execute", methods=["POST"])
def execute():
    lang = request.form.get("lang", "en")
    zh = lang == "zh"

    try:
        m = int(request.form["m"])
        n = int(request.form["n"])
        k = int(request.form["k"])
        j = int(request.form["j"])
        s = int(request.form["s"])
    except (KeyError, ValueError):
        flash("请输入有效的整数参数。" if zh else "Please enter valid integers for all parameters.", "error")
        return redirect(url_for("app_index"))

    error = validate_params(m, n, k, j, s, lang)
    if error:
        flash(error, "error")
        return redirect(url_for("app_index"))

    mode = request.form.get("mode", "random")

    if mode == "manual":
        try:
            raw = request.form.get("manual_samples", "")
            samples = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            flash("手动输入的样本必须是逗号分隔的整数。" if zh else "Manual samples must be comma-separated integers.", "error")
            return redirect(url_for("app_index"))

        if len(samples) != n:
            flash(f"必须输入 {n} 个数字，当前输入了 {len(samples)} 个。" if zh else f"You must enter exactly {n} numbers, got {len(samples)}.", "error")
            return redirect(url_for("app_index"))

        for val in samples:
            if val < 1 or val > m:
                flash(f"每个样本必须在 1 到 {m} 之间。" if zh else f"Each sample must be between 1 and {m}.", "error")
                return redirect(url_for("app_index"))

        if len(set(samples)) != n:
            flash("样本不能重复。" if zh else "Samples must be unique.", "error")
            return redirect(url_for("app_index"))
    else:
        samples = random_select_samples(m, n)

    # Run algorithm with timeout
    groups, elapsed_ms, timed_out = compute_optimal_groups(samples, k, j, s, timeout=30)
    num_groups = len(groups)

    # Format groups for display
    groups_list = [list(g) for g in groups]

    if timed_out:
        flash("算法超时，返回当前最优解。" if zh else "Algorithm timed out, returning current best solution.", "warning")

    # Look up historical best for same parameters
    user = session.get("user")
    historical_best = None
    if user and not user.get("is_guest"):
        conn = get_db()
        row = conn.execute(
            "SELECT MIN(num_groups) FROM results WHERE m=? AND n=? AND k=? AND j=? AND s=? AND user_id=?",
            (m, n, k, j, s, user["id"])
        ).fetchone()
        conn.close()
        if row and row[0] is not None:
            historical_best = row[0]

    return render_template(
        "results.html",
        m=m, n=n, k=k, j=j, s=s,
        samples=samples,
        groups=groups_list,
        num_groups=num_groups,
        groups_json=json.dumps(groups_list),
        samples_json=json.dumps(samples),
        elapsed_ms=elapsed_ms,
        timed_out=timed_out,
        historical_best=historical_best,
    )


@app.route("/store", methods=["POST"])
def store():
    user = session.get("user")
    zh = request.form.get("lang") == "zh"
    if not user or user.get("is_guest"):
        flash("请登录后保存结果。" if zh else "Please log in to save results.", "error")
        return redirect(url_for("app_index"))

    m = int(request.form["m"])
    n = int(request.form["n"])
    k = int(request.form["k"])
    j = int(request.form["j"])
    s = int(request.form["s"])
    samples = json.loads(request.form["samples_json"])
    groups = json.loads(request.form["groups_json"])
    num_groups = len(groups)

    user_id = user["id"]
    run_number = get_next_run_number(m, n, k, j, s, user_id)
    label = f"{m}-{n}-{k}-{j}-{s}-{run_number}-{num_groups}"

    conn = get_db()
    conn.execute(
        "INSERT INTO results (label, m, n, k, j, s, run_number, num_groups, samples, groups_data, user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (label, m, n, k, j, s, run_number, num_groups, json.dumps(samples), json.dumps(groups), user_id)
    )
    conn.commit()
    conn.close()

    flash(f"结果已保存为 {label}" if zh else f"Results saved as {label}", "success")
    return redirect(url_for("database"))


@app.route("/database")
def database():
    user = session.get("user")
    if not user or user.get("is_guest"):
        return redirect(url_for("index"))
    conn = get_db()
    records = conn.execute("SELECT * FROM results WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
    conn.close()
    return render_template("database.html", records=records)


@app.route("/database/view/<int:record_id>")
def view_record(record_id):
    user = session.get("user")
    if not user or user.get("is_guest"):
        return redirect(url_for("index"))
    conn = get_db()
    record = conn.execute("SELECT * FROM results WHERE id=? AND user_id=?", (record_id, user["id"])).fetchone()
    conn.close()
    if not record:
        flash("记录未找到。" if request.args.get("lang") == "zh" else "Record not found.", "error")
        return redirect(url_for("database"))

    groups = json.loads(record["groups_data"])
    samples = json.loads(record["samples"])
    return render_template(
        "results.html",
        m=record["m"], n=record["n"], k=record["k"],
        j=record["j"], s=record["s"],
        samples=samples, groups=groups,
        num_groups=record["num_groups"],
        groups_json=record["groups_data"],
        samples_json=record["samples"],
        from_db=True, label=record["label"],
    )


@app.route("/database/delete/<int:record_id>", methods=["POST"])
def delete_record(record_id):
    user = session.get("user")
    if not user or user.get("is_guest"):
        return redirect(url_for("index"))
    conn = get_db()
    conn.execute("DELETE FROM results WHERE id=? AND user_id=?", (record_id, user["id"]))
    conn.commit()
    conn.close()
    flash("记录已删除。" if request.form.get("lang") == "zh" else "Record deleted.", "success")
    return redirect(url_for("database"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=8081)
