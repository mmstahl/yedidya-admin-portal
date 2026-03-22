"""
Windows Credential Manager wrapper (via keyring).

Credentials are stored per environment.
Keyring keys: "{env}.{field}", e.g. "staging.wp_url", "production.wp_password".

Environments: 'staging', 'production'
Fields: wp_url, wp_user, wp_password, sftp_host, sftp_user, sftp_password
"""
import keyring
import keyring.errors
from portal.config.settings import KEYRING_SERVICE

CREDENTIAL_KEYS = ['wp_url', 'wp_user', 'wp_password', 'sftp_host', 'sftp_user', 'sftp_password']
ENVIRONMENTS    = ['staging', 'production']


def _k(env, key):
    return f"{env}.{key}"


def has_credentials(env='staging'):
    """Return True if all credentials are stored for the given environment."""
    return all(keyring.get_password(KEYRING_SERVICE, _k(env, k)) for k in CREDENTIAL_KEYS)


def get(key, env='staging'):
    return keyring.get_password(KEYRING_SERVICE, _k(env, key)) or ''


def get_all(env='staging'):
    return {k: get(k, env) for k in CREDENTIAL_KEYS}


def save(credentials: dict, env='staging'):
    """Save a dict of {field: value} for the given environment."""
    for key, value in credentials.items():
        if key in CREDENTIAL_KEYS:
            keyring.set_password(KEYRING_SERVICE, _k(env, key), value)


def clear(env='staging'):
    """Remove all stored credentials for the given environment."""
    for key in CREDENTIAL_KEYS:
        try:
            keyring.delete_password(KEYRING_SERVICE, _k(env, key))
        except keyring.errors.PasswordDeleteError:
            pass
