
from flask import Flask, render_template, request, redirect, url_for, abort
import sqlite3
from datetime import date, datetime
from pathlib import Path

app = Flask(__name__)
DB_NAME = Path(__file__).resolve().parent / "expenses.db"

CATEGORIES = ["Food", "Travel", "Shopping", "Education", "Bills", "Health", "Other"]


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL
            )
        """)


def valid_expense(form):
    try:
        amount = round(float(form.get("amount", "")), 2)
        category = form.get("category", "").strip()
        description = form.get("description", "").strip()
        expense_date = form.get("date", "").strip()
        datetime.strptime(expense_date, "%Y-%m-%d")

        if amount <= 0 or amount > 100000000:
            raise ValueError("Invalid amount")

        if category not in CATEGORIES:
            raise ValueError("Invalid category")

        return amount, category, description, expense_date
    except (ValueError, TypeError):
        abort(400, description="Please enter valid expense details.")


@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    selected_category = request.args.get("category", "")

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if search:
        query += " AND (description LIKE ? OR category LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if selected_category in CATEGORIES:
        query += " AND category = ?"
        params.append(selected_category)

    query += " ORDER BY date DESC, id DESC"

    with get_connection() as conn:
        expenses = conn.execute(query, params).fetchall()

        all_expenses = conn.execute(
            "SELECT * FROM expenses ORDER BY date DESC, id DESC"
        ).fetchall()

        category_rows = conn.execute("""
            SELECT category, ROUND(SUM(amount), 2) AS total
            FROM expenses
            GROUP BY category
            ORDER BY total DESC
        """).fetchall()

        monthly_rows = conn.execute("""
            SELECT SUBSTR(date, 1, 7) AS month,
                   ROUND(SUM(amount), 2) AS total
            FROM expenses
            GROUP BY SUBSTR(date, 1, 7)
            ORDER BY month
        """).fetchall()

    total = round(sum(row["amount"] for row in all_expenses), 2)
    count = len(all_expenses)
    highest = max(
        (row["amount"] for row in all_expenses),
        default=0
    )
    categories_used = len(category_rows)

    return render_template(
        "index.html",
        expenses=expenses,
        recent=all_expenses[:5],
        total=total,
        count=count,
        highest=highest,
        categories_used=categories_used,
        categories=CATEGORIES,
        today=date.today().isoformat(),
        search=search,
        selected_category=selected_category,
        category_labels=[r["category"] for r in category_rows],
        category_values=[r["total"] for r in category_rows],
        monthly_labels=[r["month"] for r in monthly_rows],
        monthly_values=[r["total"] for r in monthly_rows]
    )


@app.route("/add", methods=["POST"])
def add_expense():
    amount, category, description, expense_date = valid_expense(
        request.form
    )

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO expenses (amount, category, description, date)
            VALUES (?, ?, ?, ?)
        """, (amount, category, description, expense_date))

    return redirect(url_for("index") + "#records")


@app.route("/edit/<int:expense_id>", methods=["POST"])
def edit_expense(expense_id):
    amount, category, description, expense_date = valid_expense(
        request.form
    )

    with get_connection() as conn:
        result = conn.execute("""
            UPDATE expenses
            SET amount=?, category=?, description=?, date=?
            WHERE id=?
        """, (amount, category, description, expense_date, expense_id))

        if result.rowcount == 0:
            abort(404)

    return redirect(url_for("index") + "#records")


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM expenses WHERE id=?",
            (expense_id,)
        )

    return redirect(url_for("index") + "#records")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
