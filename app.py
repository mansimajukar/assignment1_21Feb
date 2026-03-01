from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "realbanksecret"

# ---------- DATABASE ----------

def get_db():
    conn = sqlite3.connect("bank.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS accounts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acc_number TEXT,
        name TEXT,
        balance REAL DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER,
        type TEXT,
        amount REAL,
        date TEXT
    )
    """)

    conn.execute("INSERT OR IGNORE INTO users VALUES(1,'admin','admin123','admin')")
    conn.commit()
    conn.close()

init_db()

# ---------- LOGIN ----------

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p)).fetchone()
        conn.close()

        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            return redirect("/dashboard")
        else:
            return "Invalid login"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- DASHBOARD ----------

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    accounts = conn.execute("SELECT * FROM accounts").fetchall()
    conn.close()

    total_balance = sum(a["balance"] for a in accounts)

    labels = [a["name"] for a in accounts]
    balances = [a["balance"] for a in accounts]

    return render_template(
        "dashboard.html",
        accounts=accounts,
        total_balance=total_balance,
        labels_json=json.dumps(labels),
        balances_json=json.dumps(balances)
    )
# ---------- ADD ACCOUNT ----------

@app.route("/add", methods=["POST"])
def add():
    acc = request.form["acc"]
    name = request.form["name"]

    conn = get_db()
    conn.execute("INSERT INTO accounts(acc_number,name,balance) VALUES(?,?,0)",(acc,name))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------- DELETE ----------

@app.route("/delete/<int:id>")
def delete(id):
    conn = get_db()
    conn.execute("DELETE FROM accounts WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ---------- EDIT ----------

@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit(id):
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"]
        conn.execute("UPDATE accounts SET name=? WHERE id=?",(name,id))
        conn.commit()
        conn.close()
        return redirect("/dashboard")

    account = conn.execute("SELECT * FROM accounts WHERE id=?",(id,)).fetchone()
    conn.close()
    return render_template("edit.html", account=account)

# ---------- DEPOSIT ----------

@app.route("/deposit/<int:id>", methods=["POST"])
def deposit(id):
    amount = float(request.form["amount"])

    conn = get_db()
    conn.execute("UPDATE accounts SET balance = balance + ? WHERE id=?",(amount,id))
    conn.execute("INSERT INTO transactions(account_id,type,amount,date) VALUES(?,?,?,?)",
                 (id,"Deposit",amount,str(datetime.now())))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ---------- WITHDRAW ----------

@app.route("/withdraw/<int:id>", methods=["POST"])
def withdraw(id):
    amount = float(request.form["amount"])

    conn = get_db()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?",(id,)).fetchone()

    if acc["balance"] < amount:
        return "Insufficient balance"

    conn.execute("UPDATE accounts SET balance = balance - ? WHERE id=?",(amount,id))
    conn.execute("INSERT INTO transactions(account_id,type,amount,date) VALUES(?,?,?,?)",
                 (id,"Withdraw",amount,str(datetime.now())))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ---------- TRANSFER ----------

@app.route("/transfer", methods=["POST"])
def transfer():
    from_id = int(request.form["from"])
    to_id = int(request.form["to"])
    amount = float(request.form["amount"])

    conn = get_db()
    from_acc = conn.execute("SELECT * FROM accounts WHERE id=?",(from_id,)).fetchone()

    if from_acc["balance"] < amount:
        return "Not enough balance"

    conn.execute("UPDATE accounts SET balance=balance-? WHERE id=?",(amount,from_id))
    conn.execute("UPDATE accounts SET balance=balance+? WHERE id=?",(amount,to_id))

    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ---------- TRANSACTIONS ----------

@app.route("/transactions/<int:id>")
def transactions(id):
    conn = get_db()
    data = conn.execute("SELECT * FROM transactions WHERE account_id=?",(id,)).fetchall()
    conn.close()
    return render_template("transactions.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)