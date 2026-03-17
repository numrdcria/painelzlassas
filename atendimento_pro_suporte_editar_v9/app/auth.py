from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.models import User

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("E-mail ou senha invalidos.", "danger")
        elif not user.active:
            flash("Usuario inativo. Fale com o administrador.", "warning")
        else:
            login_user(user, remember=True)
            flash(f"Bem-vindo, {user.name}.", "success")
            next_url = request.args.get("next") or url_for("main.dashboard")
            return redirect(next_url)

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Voce saiu do sistema.", "info")
    return redirect(url_for("auth.login"))
