import click
from flask import current_app
from app import db
from app.models.user import User


@click.command("create-admin")
def create_admin():
    username = current_app.config.get("ADMIN_BOOTSTRAP_USERNAME")
    password = current_app.config.get("ADMIN_BOOTSTRAP_PASSWORD")

    if not username or not password:
        click.echo("ADMIN_BOOTSTRAP_USERNAME / ADMIN_BOOTSTRAP_PASSWORD not set in .env")
        return

    existing = User.query.filter_by(username=username).first()
    if existing:
        if not existing.is_admin:
            existing.is_admin = True
            db.session.commit()
            click.echo(f"Existing user '{username}' promoted to admin.")
        else:
            click.echo(f"Admin '{username}' already exists.")
        return

    admin = User(username=username, is_admin=True)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Admin user '{username}' created.")