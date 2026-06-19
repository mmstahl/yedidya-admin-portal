import keyring, requests

SERVICE = 'YedidyaPortal'
env = 'production'

wp_url  = keyring.get_password(SERVICE, f'{env}.wp_url')
wp_user = keyring.get_password(SERVICE, f'{env}.wp_user')
wp_pass = keyring.get_password(SERVICE, f'{env}.wp_password')

resp = requests.get(
    f"{wp_url.rstrip('/')}/wp-json/wp/v2/plugins",
    auth=(wp_user, wp_pass),
    timeout=15,
)
print(f"Status: {resp.status_code}\n")
if resp.ok:
    plugins = resp.json()
    for p in sorted(plugins, key=lambda x: x.get('name', '')):
        status = p.get('status', '')
        name   = p.get('name', '')
        version = p.get('version', '')
        print(f"[{status:8}] {name} ({version})")
else:
    print(resp.text[:500])
