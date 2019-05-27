import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
from helper import cap, lookup


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["cap"] = cap

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/", methods=["GET"])
@login_required
def index():

    user = session["user_id"]

    balanceCheck = db.execute("SELECT cash FROM users WHERE id = :user", user=user)

    cash = balanceCheck[0]['cash']

    # pull a query that returns the shares they own and the quantity
    portfolio = db.execute(
        "SELECT symbol, sum(quantity) as number_of_shares FROM transactions WHERE userid = :user GROUP BY symbol HAVING sum(quantity)>0", user=user)

    quotes = {}

    total = cash

    for investment in portfolio:
        symbol = str(investment["symbol"])
        quantity = int(investment["number_of_shares"])
        quotes[symbol] = lookup(symbol)
        price = quotes[symbol].get("price")
        total = total + (price * quantity)


    return render_template("index.html", cash=cash, portfolio=portfolio, quotes=quotes, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("must provide stock ticker", 400)

        # record stock ticket provided
        ticker = request.form.get("symbol")

        quote = lookup(ticker)

        if not quote:
            return apology("provide valid stock ticker", 400)

        # get share quantity and calculate order total
        shares = int(float(request.form.get("shares")))

        if shares < 0 or not isinstance(shares, int):
            return apology("provide positive integer quantity to buy", 400)

        price = quote.get("price")

        cost = float(shares * price)

        # check customer account balance
        user = session["user_id"]

        balanceCheck = db.execute("SELECT cash FROM users WHERE id = :user", user=user)

        balance = balanceCheck[0]["cash"]

        # if current cash balance < desired transaction amount, return error
        if balance < cost:
            return apology("insufficient funds", 403)

        # execute the purchase by writing a row to the database
        purchase = db.execute("INSERT INTO 'transactions' ('userid','ordertype', 'symbol', 'price', 'quantity') VALUES (:userid, 'BUY', :symbol, :price, :quantity)",
                              userid=user, symbol=quote.get("symbol"), price=quote.get("price"), quantity=shares)

        # adjust downward the cash balance
        payment = db.execute("UPDATE users SET 'cash' = :newBalance WHERE id = :user", user=user, newBalance=balance - cost)

        flash("Bought!")

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():

    if not request.form.get("username"):
        return;

    username = request.form.get("username")

    if username < 1:
        return;

    rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

    if len(rows) >= 1:
        return jsonify(False);

    else:
        return jsonify(True);

@app.route("/deposit", methods=["GET", "POST"])
@login_required

def deposit():
    if request.method == "POST":

        flash("Mo Money, Mo Money, Mo Money!")


        return redirect("/")


    else:
        return render_template("deposit.html")


@app.route("/history")
@login_required
def history():

    user = session["user_id"]

    history = db.execute(
        "SELECT ordertype, symbol, price, quantity, transactiondate FROM transactions WHERE userid = :user ORDER BY transactiondate", user=user)

    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    if request.method == 'POST':

        if not request.form.get("symbol"):
            return apology("must provide stock ticker", 400)

        # record stock ticket provided
        ticker = request.form.get("symbol")

        # obtain the price of the input stock ticker
        quote = lookup(ticker)

        if not quote:
            return apology("provide valid stock ticker", 400)

        price = quote.get("price")

        return render_template("quoted.html", quote=quote, price=price)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """ register user """
    # Forget any user_id
    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 400)

        username = request.form.get("username")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        if len(rows) >= 1:
            return apology("username already exists", 400)

        if not request.form.get("password"):
            return apology("please provide a password", 400)

        if not request.form.get("password") == request.form.get("confirmation"):
            return apology("your passwords do not match", 400)

        password = request.form.get("password")

        # hash the password using the imported generate_password_hash function
        passwordHash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=2)

        create = db.execute("INSERT INTO 'users' ('username','hash') VALUES (:username, :passwordHash)",
                            username=request.form.get("username"), passwordHash=passwordHash)

        flash("Registered!")

        # Redirect user to home page
        return redirect("/login")

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        # define user variable
        user = session["user_id"]

        if not request.form.get("symbol"):
            return apology("must provide stock ticker", 400)

        # record stock ticket provided
        ticker = request.form.get("symbol")

        quote = lookup(ticker)

        if not quote:
            return apology("provide valid stock ticker", 400)

        # get share quantity and verify that user owns sufficient shares
        sellQuantity = int(request.form.get("quantity"))

        rows = db.execute(
            "SELECT sum(quantity) as number_of_shares FROM transactions WHERE userid = :user AND symbol = :ticker", user=user, ticker=ticker)

        ownQuantity = rows[0]['number_of_shares']

        if sellQuantity > ownQuantity:
            return apology("you dont own that many shares", 403)

        # calculate the sale proceeds
        price = quote.get("price")

        # execute the sale by writing a row to the transaction database
        sale = db.execute(
            "INSERT INTO 'transactions' ('userid','ordertype', 'symbol', 'price', 'quantity') VALUES (:userid, 'SALE', :symbol, :price, :quantity)",
            userid=user, symbol=quote.get("symbol"), price=quote.get("price"), quantity=-1*sellQuantity)

        # check the cash balance
        balanceCheck = db.execute("SELECT cash FROM users WHERE id = :user", user=user)

        balance = balanceCheck[0]["cash"]

        # adjust upward the cash balance
        proceeds = float(sellQuantity * price)

        payment = db.execute("UPDATE users SET 'cash' = :newBalance WHERE id = :user", user=user, newBalance=balance + proceeds)

        flash("Sold!")

        return redirect("/")

    else:
        user = session["user_id"]

        portfolio = db.execute(
            "SELECT symbol, sum(quantity) as number_of_shares FROM transactions WHERE userid = :user GROUP BY symbol HAVING sum(quantity)>0", user=user)

        for investment in portfolio:
            symbol = str(investment["symbol"])

        return render_template("sell.html", portfolio=portfolio)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)





# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


