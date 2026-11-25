"""Creates the SQLite schema, product images (SVG) and demo data."""
import os, sqlite3
from werkzeug.security import generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "trufitz.db")
IMG = os.path.join(BASE, "static", "img")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, is_admin INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY, name TEXT, slug TEXT UNIQUE, tagline TEXT, badge TEXT, icon TEXT);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, category_id INTEGER, name TEXT, slug TEXT UNIQUE, description TEXT,
  price REAL, old_price REAL, badge TEXT, image TEXT, stock INTEGER, sizes TEXT, featured INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, phone TEXT, email TEXT, address TEXT, city TEXT,
  payment TEXT, subtotal REAL, shipping REAL, tax REAL, total REAL, status TEXT DEFAULT 'Pending', created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, name TEXT, size TEXT, price REAL, qty INTEGER);
"""

CATS = [
 ("Shirt","shirt","Sharp quality shirts for every occasion","TRENDING","▤"),
 ("Polo T-Shirt","polo","Premium polos with a classic feel","CLASSIC","◆"),
 ("T-Shirt","t-shirt","Casual, soft, all-day comfort","POPULAR","▲"),
 ("Punjabi","punjabi","Elegant traditional wear","TRADITIONAL","✦"),
 ("Pant","pant","Tailored fits, built to move","","■"),
 ("Footwear","footwear","Quality footwear for every step","","●"),
 ("Lifestyle","lifestyle","Accessories that finish the look","","❖"),
]
# name, cat, price, old, badge, color, accent, sizes, featured, desc
PRODUCTS = [
 ("Midnight Crest Tee","t-shirt",450,550,"HOT","#1d2433","#c9b27c","S,M,L,XL",1,"Heavyweight cotton tee with the TruFitZ crest print."),
 ("Sand Amrito Tee","t-shirt",450,520,"NEW","#d9c3a0","#2b3a67","S,M,L,XL",1,"Warm sand tone, soft-washed 180gsm cotton."),
 ("Noir Story Tee","t-shirt",500,600,"HOT","#141414","#e8e8e8","M,L,XL,XXL",1,"Graphic tee in washed black with a relaxed cut."),
 ("TruFitZ Trendy Tee","t-shirt",500,650,"NEW","#222","#ffffff","S,M,L,XL",1,"Our signature everyday tee — clean, bold, comfortable."),
 ("Harbor Polo","polo",850,1000,"CLASSIC","#26435e","#ffffff","S,M,L,XL",1,"Pique-knit polo with a structured collar."),
 ("Ash Polo","polo",800,950,"","#8d9399","#ffffff","S,M,L,XL",0,"Breathable pique polo in soft ash grey."),
 ("Oxford Blue Shirt","shirt",1400,1700,"TRENDING","#7ea0c7","#ffffff","M,L,XL",1,"Crisp oxford weave, button-down collar."),
 ("Linen Cream Shirt","shirt",1500,1800,"","#eadfc8","#7a6a4f","M,L,XL",0,"Lightweight linen for warm days."),
 ("Royal Maroon Punjabi","punjabi",2600,3200,"TRADITIONAL","#6b1f2a","#d8b56a","M,L,XL,XXL",1,"Embroidered placket, festive-ready."),
 ("Ivory Festive Punjabi","punjabi",2800,3400,"NEW","#f1ead8","#b08a3e","M,L,XL,XXL",0,"Ivory cotton-silk blend with gold detailing."),
 ("Stealth Joggers","pant",1200,1500,"","#161616","#ffffff","M,L,XL",1,"Tapered joggers with stretch waistband."),
 ("Khaki Chino","pant",1500,1900,"POPULAR","#a99062","#ffffff","30,32,34,36",0,"Slim-fit chino, garment-washed twill."),
 ("Street Runner Shoes","footwear",2800,3300,"","#101820","#ffffff","40,41,42,43,44",1,"Lightweight everyday sneakers."),
 ("Classic Court Shoes","footwear",3200,3800,"LIMITED","#f4f4f0","#1b1b1b","40,41,42,43,44",0,"Clean white leather court sneakers."),
 ("Everyday Cap","lifestyle",350,450,"","#2b2b2b","#c9b27c","Free",0,"Adjustable cotton cap with embroidered logo."),
 ("Canvas Tote","lifestyle",600,750,"NEW","#e6dcc6","#1b1b1b","Free",0,"Heavy canvas tote for daily carry."),
]

def slugify(s): return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")

def svg(cat, c, a):
    body = {
     "t-shirt": f'<path d="M150 70 L95 95 L60 160 L105 180 L120 150 L120 330 L280 330 L280 150 L295 180 L340 160 L305 95 L250 70 Q200 105 150 70Z" fill="{c}"/><circle cx="200" cx2="" cy="200" r="34" fill="none" stroke="{a}" stroke-width="5"/><path d="M185 200 h30 M200 185 v30" stroke="{a}" stroke-width="5"/>',
     "polo": f'<path d="M150 70 L95 95 L60 160 L105 180 L120 150 L120 330 L280 330 L280 150 L295 180 L340 160 L305 95 L250 70 L200 130Z" fill="{c}"/><path d="M150 70 L200 130 L250 70 L225 62 L200 90 L175 62Z" fill="{a}" opacity=".9"/><path d="M200 130 V200" stroke="{a}" stroke-width="4"/><circle cx="200" cy="150" r="4" fill="{a}"/><circle cx="200" cy="175" r="4" fill="{a}"/>',
     "shirt": f'<path d="M150 70 L90 95 L55 215 L100 225 L120 160 L120 340 L280 340 L280 160 L300 225 L345 215 L310 95 L250 70 L200 135Z" fill="{c}"/><path d="M150 70 L200 135 L250 70 L225 60 L200 95 L175 60Z" fill="{a}" opacity=".85"/><path d="M200 135 V340" stroke="{a}" stroke-width="3"/>' + "".join(f'<circle cx="200" cy="{y}" r="4" fill="{a}"/>' for y in (170,215,260,305)),
     "punjabi": f'<path d="M150 65 L90 92 L55 190 L100 200 L118 150 L112 370 L288 370 L282 150 L300 200 L345 190 L310 92 L250 65 Q200 90 150 65Z" fill="{c}"/><path d="M200 78 V200" stroke="{a}" stroke-width="10"/>' + "".join(f'<circle cx="200" cy="{y}" r="5" fill="{c}" stroke="{a}" stroke-width="2"/>' for y in (110,140,170)) + f'<path d="M150 75 Q200 110 250 75" fill="none" stroke="{a}" stroke-width="5"/>',
     "pant": f'<path d="M135 60 H265 L285 360 H215 L200 160 L185 360 H115Z" fill="{c}"/><path d="M135 60 H265 V85 H135Z" fill="{a}" opacity=".35"/><path d="M200 85 V160" stroke="{a}" stroke-width="3" opacity=".6"/>',
     "footwear": f'<path d="M60 250 Q60 180 120 175 L170 200 Q230 210 300 225 Q345 235 345 270 V285 H60Z" fill="{c}"/><rect x="60" y="280" width="285" height="22" rx="8" fill="{a}"/><path d="M130 190 l25 -10 M150 198 l25 -10 M170 206 l25 -10" stroke="{a}" stroke-width="5"/>',
     "lifestyle": f'<path d="M110 120 H290 L305 340 H95Z" fill="{c}"/><path d="M150 120 Q150 55 200 55 Q250 55 250 120" fill="none" stroke="{a}" stroke-width="10"/><circle cx="200" cy="230" r="28" fill="none" stroke="{a}" stroke-width="5"/>',
    }[cat]
    body = body.replace(' cx2=""', "")
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400"><rect width="400" height="400" fill="#f3f1ec"/><ellipse cx="200" cy="375" rx="110" ry="9" fill="#000" opacity=".08"/>{body}</svg>'

def run(reset=False):
    if reset and os.path.exists(DB): os.remove(DB)
    os.makedirs(IMG, exist_ok=True)
    db = sqlite3.connect(DB); db.executescript(SCHEMA)
    if db.execute("SELECT COUNT(*) FROM categories").fetchone()[0]: return db.close()
    db.executemany("INSERT INTO categories(name,slug,tagline,badge,icon) VALUES(?,?,?,?,?)", CATS)
    ids = {r[1]: r[0] for r in db.execute("SELECT id,slug FROM categories")}
    for n, cat, p, o, b, c, a, sz, f, d in PRODUCTS:
        slug = slugify(n); fn = f"{slug}.svg"
        open(os.path.join(IMG, fn), "w").write(svg(cat, c, a))
        db.execute("INSERT INTO products(category_id,name,slug,description,price,old_price,badge,image,stock,sizes,featured) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (ids[cat], n, slug, d, p, o, b, fn, 50, sz, f))
    db.execute("INSERT INTO users(name,email,password,is_admin) VALUES(?,?,?,1)", ("Admin", "admin@trufitz.com", generate_password_hash("admin123")))
    db.commit(); db.close()

if __name__ == "__main__":
    run(reset=True); print("Database seeded:", DB)
