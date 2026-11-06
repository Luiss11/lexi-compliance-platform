"""Crea una organización nueva con su primer administrador.

Uso (con la pila levantada; -it para poder escribir la contraseña sin que quede en el historial):
    docker compose exec -it api python -m app.tools.create_tenant \
        --name "Clínica Dental Sonrisa" --slug clinica-sonrisa --sector clinica \
        --admin-name "Dra. Ana López" --admin-email ana@clinica.mx

La contraseña se pide por teclado (mínimo 10 caracteres, con letras y números).
Para scripts, puede pasarse en la variable de entorno ADMIN_PASSWORD.
"""
import argparse
import asyncio
import getpass
import os
import sys

from app.core.errors import AppError
from app.db.session import SessionLocal, engine
from app.services import tenant_service


def _password() -> str:
    from_env = os.environ.get("ADMIN_PASSWORD")
    if from_env:
        return from_env
    first = getpass.getpass("Contraseña del administrador: ")
    if getpass.getpass("Repite la contraseña: ") != first:
        sys.exit("Las contraseñas no coinciden.")
    return first


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--name", required=True, help="Nombre de la organización")
    ap.add_argument("--slug", required=True, help="Identificador para iniciar sesión (minúsculas)")
    ap.add_argument("--sector", required=True, help="clinica, comercio u otro giro")
    ap.add_argument("--admin-name", required=True)
    ap.add_argument("--admin-email", required=True)
    args = ap.parse_args()

    password = _password()
    try:
        async with SessionLocal() as db:
            tenant, admin = await tenant_service.create_tenant(
                db, name=args.name, slug=args.slug, sector=args.sector,
                admin_name=args.admin_name, admin_email=args.admin_email,
                admin_password=password,
            )
    except AppError as exc:
        print(f"No se creó la organización: {exc.message}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()

    print(f"Organización creada: {tenant.name}")
    print(f"Identificador: {tenant.slug} · sector: {tenant.sector}")
    print(f"Administrador: {admin.email}")
    print("Para entrar en la web usa ese identificador, el correo y la contraseña elegida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
