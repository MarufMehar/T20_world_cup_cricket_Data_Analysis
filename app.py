from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2

app = Flask(__name__)
app.secret_key = "your_secret_key"

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        dbname="vector_database",
        user="postgres",
        password="1202",
        port="5432"
    )

@app.route("/")
def home():
    return redirect("/login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id", (username, password))
        user_id = cur.fetchone()[0]
        conn.commit()
        conn.close()

        session["user_id"] = user_id
        # Redirect to Streamlit with user_id param
        return redirect(f"http://localhost:8501/?user_id={user_id}")

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect(f"http://localhost:8501/?user_id={user[0]}")
        else:
            return "Invalid username or password"

    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)
