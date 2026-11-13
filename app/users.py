"""aemon accounts. Kept outside the repository, with salted scrypt hashes and never a plain password.

Accounts live in aemon's SQLite database (app/store.py), which imports an older ~/.config/lexsi/users.json once.
An account is a member of one or more companies and works in one company's workspace at a time. No default account
exists: create one with

    python app/users.py add NAME COMPANY      (asks for the password twice; the account joins COMPANY)
    python app/users.py join NAME COMPANY     (adds another company's workspace to the account)
    python app/users.py leave NAME COMPANY
    python app/users.py remove NAME
    python app/users.py list                  (accounts and their companies)
    python app/users.py companies             (the companies an account can join)

Companies are filled from the dossier when aemon starts.
"""

import getpass
import hashlib
import hmac
import re
import secrets
import sys

import store

NAME = re.compile(r'^[a-z0-9][a-z0-9_.-]{0,31}$')  # also a folder name for chat history, so nothing that can climb out
SCRYPT = {'n': 2**14, 'r': 8, 'p': 1, 'dklen': 32}
MIN_PASSWORD = 8
_DUMMY = {'salt': '00' * 16, 'hash': '00' * 32}


def _hash(password: str, salt: str) -> str:
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **SCRYPT).hex()


def add(name: str, password: str, company: str) -> None:
    if not NAME.match(name):
        raise ValueError('a name is 1 to 32 lower-case letters, digits, dots, dashes or underscores')
    if len(password) < MIN_PASSWORD:
        raise ValueError(f'a password needs at least {MIN_PASSWORD} characters')
    if company not in {c['id'] for c in store.companies()}:
        raise ValueError(f'no company {company}; start aemon once, then see: python app/users.py companies')
    salt = secrets.token_hex(16)
    store.put_user(name, salt, _hash(password, salt))
    store.join(name, company)


def remove(name: str) -> None:
    if not store.remove_user(name):
        raise ValueError(f'no user {name}')


def verify(name: str, password: str) -> bool:
    """Constant time either way: an unknown name still costs one scrypt, so timing does not reveal which names exist."""
    entry = store.user(name) if isinstance(name, str) and NAME.match(name) else None
    known = entry or _DUMMY
    ok = hmac.compare_digest(_hash(password if isinstance(password, str) else '', known['salt']), known['hash'])
    return bool(entry) and ok


def main(argv: list[str]) -> None:
    command, rest = (argv[1], argv[2:]) if len(argv) > 1 else ('', [])
    if command == 'list' and not rest:
        print('\n'.join(f'{a["name"]}: {", ".join(a["companies"]) or "no company"}' for a in store.accounts()) or 'no users yet')
    elif command == 'companies' and not rest:
        print('\n'.join(f'{c["id"]}: {c["name"]}' for c in store.companies()) or 'no companies yet: start aemon once')
    elif command == 'remove' and len(rest) == 1:
        remove(rest[0])
        print(f'removed {rest[0]}')
    elif command == 'join' and len(rest) == 2:
        store.join(rest[0], rest[1])
        print(f'{rest[0]} joined {rest[1]}')
    elif command == 'leave' and len(rest) == 2:
        print(f'{rest[0]} left {rest[1]}' if store.leave(rest[0], rest[1]) else f'{rest[0]} was not in {rest[1]}')
    elif command == 'add' and len(rest) == 2:
        password = getpass.getpass('Password: ')
        if password != getpass.getpass('Again: '):
            raise SystemExit('the passwords differ')
        add(rest[0], password, rest[1])
        print(f'added {rest[0]} for {rest[1]} to {store.database()}')
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except ValueError as error:
        raise SystemExit(str(error)) from None
