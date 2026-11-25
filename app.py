import os, sqlite3, functools
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
import seed

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me")
TAX_RATE = 0.05
seed.run()

# ---------- db ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(seed.DB); g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def q(sql, args=(), one=False):
    cur = db().execute(sql, args); rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows

# ---------- helpers ----------
@app.template_filter("taka")
def taka(v): return f"৳{v:,.0f}" if float(v) == int(v) else f"৳{v:,.2f}"

def cart_items():
    items, subtotal, saved = [], 0, 0
    for key, qty in session.get("cart", {}).items():
        pid, size = key.split(":", 1)
        p = q("SELECT * FROM products WHERE id=?", (pid,), one=True)
        if not p: continue
        line = p["price"] * qty; subtotal += line
        saved += max((p["old_price"] or p["price"]) - p["price"], 0) * qty
        items.append(dict(key=key, p=p, size=size, qty=qty, line=line))
    return items, subtotal, saved

def totals(subtotal, city="Dhaka"):
    ship = 0 if subtotal == 0 else (60 if city.strip().lower() == "dhaka" else 120)
    tax = round(subtotal * TAX_RATE, 2)
    return ship, tax, subtotal + ship + tax

@app.context_processor
def inject():
    n = sum(session.get("cart", {}).values())
    return dict(cart_count=n, nav_cats=q("SELECT * FROM categories"), user=session.get("user"))

def login_required(f):
    @functools.wraps(f)
    def w(*a, **k):
        if not session.get("user"):
            flash("Please log in first."); return redirect(url_for("login", next=request.path))
        return f(*a, **k)
    return w

def admin_required(f):
    @functools.wraps(f)
    def w(*a, **k):
        if not (session.get("user") or {}).get("is_admin"): abort(403)
        return f(*a, **k)
    return w

# ---------- catalogue ----------
@app.route("/")
def home():
    picks = q("SELECT * FROM products WHERE featured=1 ORDER BY id LIMIT 8")
    return render_template("home.html", picks=picks)

@app.route("/categories/")
def categories():
    return render_template("categories.html")

@app.route("/products/")
@app.route("/category/<slug>/")
def products(slug=None):
    term = request.args.get("q", "").strip(); sort = request.args.get("sort", "new")
    sql, args, cat = "SELECT * FROM products WHERE 1=1", [], None
    if slug:
        cat = q("SELECT * FROM categories WHERE slug=?", (slug,), one=True) or abort(404)
        sql += " AND category_id=?"; args.append(cat["id"])
    if term:
        sql += " AND (name LIKE ? OR description LIKE ?)"; args += [f"%{term}%"] * 2
    sql += {"low": " ORDER BY price", "high": " ORDER BY price DESC"}.get(sort, " ORDER BY id DESC")
    return render_template("products.html", items=q(sql, args), cat=cat, term=term, sort=sort)

@app.route("/product/<slug>/")
def product(slug):
    p = q("SELECT p.*, c.name cat_name, c.slug cat_slug FROM products p JOIN categories c ON c.id=p.category_id WHERE p.slug=?", (slug,), one=True) or abort(404)
    related = q("SELECT * FROM products WHERE category_id=? AND id!=? LIMIT 4", (p["category_id"], p["id"]))
    return render_template("product.html", p=p, related=related)

# ---------- cart ----------
@app.post("/cart/add/<int:pid>")
def cart_add(pid):
    p = q("SELECT * FROM products WHERE id=?", (pid,), one=True) or abort(404)
    size = request.form.get("size") or p["sizes"].split(",")[0]
    qty = max(1, min(int(request.form.get("qty", 1) or 1), 10))
    cart = session.get("cart", {}); key = f"{pid}:{size}"
    cart[key] = min(cart.get(key, 0) + qty, 10); session["cart"] = cart
    flash(f"{p['name']} (Size {size}) × {qty} added to cart.")
    if request.form.get("buy"): return redirect(url_for("checkout"))
    return redirect(request.referrer or url_for("cart"))

@app.route("/cart/")
def cart():
    items, subtotal, saved = cart_items(); ship, tax, total = totals(subtotal)
    return render_template("cart.html", items=items, subtotal=subtotal, saved=saved, ship=ship, tax=tax, total=total)

@app.post("/cart/update/<key>")
def cart_update(key):
    cart = session.get("cart", {}); n = int(request.form.get("qty", 1))
    if n <= 0: cart.pop(key, None)
    elif key in cart: cart[key] = min(n, 10)
    session["cart"] = cart; return redirect(url_for("cart"))

# ---------- checkout: cart -> details -> payment -> complete ----------
@app.route("/checkout/", methods=["GET", "POST"])
def checkout():
    items, subtotal, _ = cart_items()
    if not items: flash("Your cart is empty."); return redirect(url_for("products"))
    if request.method == "POST":
        f = {k: request.form.get(k, "").strip() for k in ("name", "phone", "email", "address", "city")}
        if not all(f[k] for k in ("name", "phone", "address", "city")):
            flash("Please fill in name, phone, address and city."); return render_template("checkout.html", step=2, items=items, subtotal=subtotal, f=f, **dict(zip(("ship","tax","total"), totals(subtotal, f["city"]))))
        session["ship_info"] = f; return redirect(url_for("payment"))
    f = session.get("ship_info") or {"name": (session.get("user") or {}).get("name", ""), "email": (session.get("user") or {}).get("email", ""), "city": "Dhaka"}
    return render_template("checkout.html", step=2, items=items, subtotal=subtotal, f=f, **dict(zip(("ship","tax","total"), totals(subtotal, f.get("city", "Dhaka")))))

@app.route("/checkout/payment/", methods=["GET", "POST"])
def payment():
    items, subtotal, _ = cart_items(); f = session.get("ship_info")
    if not items or not f: return redirect(url_for("checkout"))
    ship, tax, total = totals(subtotal, f["city"])
    if request.method == "POST":
        method = request.form.get("method", "cod")
        if method not in ("cod", "bkash", "nagad", "card"): abort(400)
        d = db()
        cur = d.execute("INSERT INTO orders(user_id,name,phone,email,address,city,payment,subtotal,shipping,tax,total) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            ((session.get("user") or {}).get("id"), f["name"], f["phone"], f["email"], f["address"], f["city"], method, subtotal, ship, tax, total))
        oid = cur.lastrowid
        for it in items:
            d.execute("INSERT INTO order_items(order_id,product_id,name,size,price,qty) VALUES(?,?,?,?,?,?)", (oid, it["p"]["id"], it["p"]["name"], it["size"], it["p"]["price"], it["qty"]))
            d.execute("UPDATE products SET stock=MAX(stock-?,0) WHERE id=?", (it["qty"], it["p"]["id"]))
        d.commit(); session.pop("cart", None); session.pop("ship_info", None); session["last_order"] = oid
        return redirect(url_for("order_done", oid=oid))
    return render_template("payment.html", step=3, items=items, subtotal=subtotal, ship=ship, tax=tax, total=total, f=f)

@app.route("/order/<int:oid>/")
def order_done(oid):
    o = q("SELECT * FROM orders WHERE id=?", (oid,), one=True) or abort(404)
    u = session.get("user")
    owner = u and (u["id"] == o["user_id"] or u["is_admin"])
    if not (owner or session.get("last_order") == oid): abort(403)
    return render_template("order.html", o=o, items=q("SELECT * FROM order_items WHERE order_id=?", (oid,)), step=4)

@app.route("/orders/")
@login_required
def my_orders():
    return render_template("orders.html", orders=q("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (session["user"]["id"],)))

# ---------- auth ----------
def set_user(r): session["user"] = dict(id=r["id"], name=r["name"], email=r["email"], is_admin=bool(r["is_admin"]))

@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        r = q("SELECT * FROM users WHERE email=?", (request.form.get("email", "").lower().strip(),), one=True)
        if r and check_password_hash(r["password"], request.form.get("password", "")):
            set_user(r); nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("home"))
        flash("Invalid email or password.")
    return render_template("auth.html", mode="login")

@app.route("/register/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        n, e, p = request.form.get("name", "").strip(), request.form.get("email", "").lower().strip(), request.form.get("password", "")
        if not (n and e and len(p) >= 6): flash("Name, email and a 6+ character password are required.")
        elif q("SELECT 1 FROM users WHERE email=?", (e,), one=True): flash("That email is already registered.")
        else:
            d = db(); cur = d.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)", (n, e, generate_password_hash(p))); d.commit()
            set_user(q("SELECT * FROM users WHERE id=?", (cur.lastrowid,), one=True)); return redirect(url_for("home"))
    return render_template("auth.html", mode="register")

@app.route("/logout/")
def logout():
    session.pop("user", None); return redirect(url_for("home"))

# ---------- admin ----------
@app.route("/admin/")
@admin_required
def admin():
    return render_template("admin.html", orders=q("SELECT * FROM orders ORDER BY id DESC"), prods=q("SELECT * FROM products ORDER BY stock"))

@app.post("/admin/order/<int:oid>/")
@admin_required
def admin_order(oid):
    s = request.form.get("status")
    if s in ("Pending", "Confirmed", "Shipped", "Delivered", "Cancelled"):
        db().execute("UPDATE orders SET status=? WHERE id=?", (s, oid)); db().commit()
    return redirect(url_for("admin"))

@app.errorhandler(403)
@app.errorhandler(404)
def err(e): return render_template("error.html", e=e), e.code

if __name__ == "__main__":
    app.run(debug=True, port=8000)
