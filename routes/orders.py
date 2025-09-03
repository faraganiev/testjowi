from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import func
from flask_login import login_required, current_user
from extensions import db, socketio
from models import Product, Order, OrderItem

orders_bp = Blueprint("orders", __name__)

ALLOWED_STATUSES = ["новый", "подтвержден", "готовится", "готов", "выполнен", "отменен"]
ALLOWED_TRANSITIONS = {
    "новый":        ["подтвержден", "отменен"],
    "подтвержден":  ["готовится", "отменен"],
    "готовится":    ["готов", "отменен"],
    "готов":        ["выполнен", "отменен"],
    "выполнен":     [],
    "отменен":      []
}

@orders_bp.route("/")
@login_required
def index():
    status = request.args.get("status")
    q = Order.query.order_by(Order.created_at.desc())
    if status in ALLOWED_STATUSES:
        q = q.filter(Order.status == status)
    orders = q.all()
    return render_template("index.html", orders=orders, status=status, statuses=ALLOWED_STATUSES)

@orders_bp.route("/_partial/orders_table")
@login_required
def orders_table_partial():
    status = request.args.get("status")
    q = Order.query.order_by(Order.created_at.desc())
    if status in ALLOWED_STATUSES:
        q = q.filter(Order.status == status)
    orders = q.all()
    return render_template("partials/orders_table.html", orders=orders)

@orders_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_order():
    products = Product.query.filter_by(is_available=True).order_by(Product.category, Product.name).all()
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        contact = (request.form.get("contact") or "").strip()
        if not name or not contact:
            flash("Имя и контакт обязательны.", "danger")
            return render_template("create_order.html", products=products)

        selected = []
        total = 0.0
        for p in products:
            qty_raw = request.form.get(f"qty_{p.id}", "0")
            try:
                qty = max(0, min(int(qty_raw), 999))
            except ValueError:
                qty = 0
            if qty > 0:
                notes = (request.form.get(f"notes_{p.id}") or "").strip() or None
                selected.append((p, qty, notes))
                total += p.price * qty

        if not selected:
            flash("Выберите хотя бы один товар (увеличьте количество).", "warning")
            return render_template("create_order.html", products=products)

        order = Order(customer_name=name, contact=contact, status="новый", total=0, created_by=current_user.id)
        db.session.add(order)
        db.session.flush()

        for p, qty, notes in selected:
            db.session.add(OrderItem(order_id=order.id, product_name=p.name, quantity=qty, price=p.price, notes=notes))

        order.total = total
        db.session.commit()

        socketio.emit("order_update")
        flash(f"Заказ №{order.id} отправлен на печать (демо).", "success")
        return redirect(url_for("orders.index"))

    return render_template("create_order.html", products=products)

@orders_bp.route("/order/<int:order_id>")
@login_required
def order_detail(order_id: int):
    order = Order.query.get_or_404(order_id)
    items = OrderItem.query.filter_by(order_id=order.id).all()
    transitions = ALLOWED_TRANSITIONS.get(order.status, [])
    return render_template("order_detail.html", order=order, items=items, transitions=transitions)

# 🔒 Только POST — меняем статус
@orders_bp.route("/order/<int:order_id>/status/<status>", methods=["POST"])
@login_required
def update_status(order_id: int, status: str):
    if status not in ALLOWED_STATUSES:
        flash("Недопустимый статус.", "danger")
        return redirect(url_for("orders.order_detail", order_id=order_id))

    order = Order.query.get_or_404(order_id)
    allowed = ALLOWED_TRANSITIONS.get(order.status, [])
    if status not in allowed:
        flash(f"Переход {order.status} → {status} не разрешён.", "warning")
        return redirect(url_for("orders.order_detail", order_id=order_id))

    old = order.status
    order.status = status
    db.session.commit()
    current_app.logger.info("status_change order=%s from=%s to=%s by=%s",
                            order.id, old, status, getattr(current_user, "id", None))
    socketio.emit("order_update")
    return redirect(url_for("orders.order_detail", order_id=order_id))

# 🔒 Только POST — отмена
@orders_bp.route("/order/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id: int):
    order = Order.query.get_or_404(order_id)
    if order.status not in ["выполнен", "отменен"]:
        old = order.status
        order.status = "отменен"
        db.session.commit()
        current_app.logger.info("status_change order=%s from=%s to=%s by=%s",
                                order.id, old, "отменен", getattr(current_user, "id", None))
        socketio.emit("order_update")
    else:
        flash("Этот заказ уже нельзя отменить.", "info")
    return redirect(url_for("orders.order_detail", order_id=order_id))

@orders_bp.route("/stats")
@login_required
def stats():
    data = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    labels = [row[0] for row in data]
    values = [row[1] for row in data]
    pairs = list(zip(labels, values))
    return render_template("stats.html", labels=labels, values=values, pairs=pairs, statuses=ALLOWED_STATUSES)
