import keyring, requests

SERVICE = 'YedidyaPortal'
env = 'staging'  # or 'production'

wp_url  = keyring.get_password(SERVICE, f'{env}.wp_url')
wp_user = keyring.get_password(SERVICE, f'{env}.wp_user')
wp_pass = keyring.get_password(SERVICE, f'{env}.wp_password')

print("URL:", wp_url)

resp = requests.get(
    f"{wp_url.rstrip('/')}/wp-json/wc/v3/products",
    params={'per_page': 1},
    auth=(wp_user, wp_pass),
)
print(resp.status_code, resp.text[:300])