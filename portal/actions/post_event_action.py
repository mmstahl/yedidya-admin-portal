"""
Post & Event action.

Flow:
  1. Fetch the selected template post by slug (raw Gutenberg content).
  2. Replace placeholder strings in the content based on the template config.
  3. Resolve selected category names to WordPress category IDs.
  4. Upload the provided image to the WordPress media library (if template uses image).
  5. Replace the first embedded image block with the uploaded image (if applicable).
  6. Create or update a published post with the modified content, title, and categories.
     If a post with the same title already exists it is updated, not duplicated.
"""
import os
import re
import requests
import unicodedata

from portal.actions.base_action import BaseAction, ActionResult
from portal.credentials.credential_manager import get as get_cred

# ---------------------------------------------------------------------------
# Template registry
#
# Each entry maps a WordPress post slug to its configuration:
#   label        — human-readable name shown in the Template dropdown
#   fields       — ordered list of field names the template uses
#                  ('title' is always required and not listed here)
#   placeholders — mapping from field name to the literal placeholder
#                  string in the template post content
# ---------------------------------------------------------------------------
TEMPLATES = {
    'event-template-1': {
        'label':  'Event Template 1',
        'fields': ['date', 'description', 'image'],
        'placeholders': {
            'date':        'Hebrew-and-Gregorian-dates',
            'description': 'Description-of-this-event',
        },
    },
    'event-template-2': {
        'label':  'Event Template 2',
        'fields': ['image', 'caption'],
        'placeholders': {
            'title_content': 'Event Template 2 (Header, Description, Image link)',
        },
    },
}


class PostEventAction(BaseAction):
    name = "Post/Update event"
    description = "Create or update an event post from a template"

    # ------------------------------------------------------------------
    # Helpers shared by run(), the window's title-check, and delete flow
    # ------------------------------------------------------------------

    def _auth(self, env):
        return (get_cred('wp_user', env), get_cred('wp_password', env))

    def find_post(self, title: str, env: str = 'staging', lang: str = '') -> ActionResult:
        """Return ActionResult with data=post_id (int) if found, data=None if not."""
        base = get_cred('wp_url', env).rstrip('/')
        auth = self._auth(env)
        try:
            params = {'search': title, 'status': 'any', 'context': 'edit', 'per_page': 20}
            if lang:
                params['lang'] = lang
            resp = requests.get(
                f"{base}/wp-json/wp/v2/posts",
                params=params,
                auth=auth, timeout=30,
            )
            if resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            resp.raise_for_status()
            for p in resp.json():
                if p.get('title', {}).get('raw', '').strip() == title:
                    return ActionResult(True, f"Found post ID {p['id']}", data=p['id'])
            return ActionResult(True, "Not found", data=None)
        except Exception as e:
            return ActionResult(False, f"Search failed: {e}")

    def delete(self, post_id: int, env: str = 'staging') -> ActionResult:
        """Permanently delete a post (bypasses trash)."""
        base = get_cred('wp_url', env).rstrip('/')
        auth = self._auth(env)
        try:
            resp = requests.delete(
                f"{base}/wp-json/wp/v2/posts/{post_id}",
                params={'force': True},
                auth=auth, timeout=30,
            )
            if resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            resp.raise_for_status()
            return ActionResult(True, f"Post {post_id} permanently deleted.")
        except Exception as e:
            return ActionResult(False, f"Delete failed: {e}")

    def run(self, template: str, title: str, categories: list,
            date: str = '', description: str = '', image_path: str = '',
            caption: str = '', lang: str = '', env: str = 'staging') -> ActionResult:

        base = get_cred('wp_url', env).rstrip('/')
        auth = self._auth(env)

        tpl_config   = TEMPLATES.get(template, {})
        placeholders = tpl_config.get('placeholders', {})

        # ── 1. Fetch template (posts then pages; each tried with and without lang=en) ──
        posts = []
        for post_type in ('posts', 'pages'):
            for lang in (None, 'en'):
                params = {'slug': template, 'context': 'edit', 'status': 'any'}
                if lang:
                    params['lang'] = lang
                try:
                    resp = requests.get(
                        f"{base}/wp-json/wp/v2/{post_type}",
                        params=params, auth=auth, timeout=30,
                    )
                    if resp.status_code == 401:
                        return ActionResult(False, "401 Unauthorized — check credentials.")
                    resp.raise_for_status()
                    posts = resp.json()
                    if posts:
                        break
                except Exception as e:
                    return ActionResult(False, f"Failed to fetch template: {e}")
            if posts:
                break

        if not posts:
            return ActionResult(False, f"Template post '{template}' not found.")

        content = posts[0].get('content', {}).get('raw', '')
        if not content:
            return ActionResult(False, "Template post has no raw content.")

        # ── 2. Replace text placeholders ──────────────────────────────────
        if 'title_content' in placeholders and title:
            content = content.replace(placeholders['title_content'], title)
        if 'date' in placeholders and date:
            content = content.replace(placeholders['date'], date)
        if 'description' in placeholders and description:
            content = content.replace(placeholders['description'], description)

        # ── 3. Resolve category names → IDs ───────────────────────────────
        cat_ids  = []
        warnings = []
        if categories:
            try:
                cat_resp = requests.get(
                    f"{base}/wp-json/wp/v2/categories",
                    params={'per_page': 100},
                    auth=auth, timeout=30,
                )
                cat_resp.raise_for_status()
                name_to_id = {c['name']: c['id'] for c in cat_resp.json()}
                for name in categories:
                    if name in name_to_id:
                        cat_ids.append(name_to_id[name])
                    else:
                        warnings.append(f"Category not found on site: '{name}'")
            except Exception as e:
                return ActionResult(False, f"Failed to fetch categories: {e}")

        # ── 4. Upload image ────────────────────────────────────────────────
        if image_path and 'image' in tpl_config.get('fields', []):
            try:
                filename = os.path.basename(image_path)
                ext      = os.path.splitext(filename)[1].lower()
                mime_map = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png',  '.gif': 'image/gif',
                    '.webp': 'image/webp',
                }
                mime = mime_map.get(ext, 'image/jpeg')

                # Header filename must be ASCII; strip non-ASCII chars, keep extension
                ascii_name = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii').strip()
                if not ascii_name or ascii_name == ext:
                    ascii_name = f"image{ext}"

                with open(image_path, 'rb') as f:
                    media_resp = requests.post(
                        f"{base}/wp-json/wp/v2/media",
                        headers={
                            'Content-Disposition': f'attachment; filename="{ascii_name}"',
                            'Content-Type': mime,
                        },
                        data=f.read(),
                        auth=auth, timeout=60,
                    )
                if media_resp.status_code == 401:
                    return ActionResult(False, "401 Unauthorized — check credentials.")
                media_resp.raise_for_status()
                media = media_resp.json()
            except Exception as e:
                return ActionResult(False, f"Failed to upload image: {e}")

            new_id  = media['id']
            new_url = media['source_url']

            # ── 5. Replace first image block ──────────────────────────────
            figcaption = (
                f'<figcaption class="wp-element-caption">{caption}</figcaption>'
                if caption else ''
            )
            new_block = (
                f'<!-- wp:image {{"id":{new_id},"sizeSlug":"large","linkDestination":"none"}} -->\n'
                f'<figure class="wp-block-image size-large">'
                f'<img src="{new_url}" alt="" class="wp-image-{new_id}"/>'
                f'{figcaption}'
                f'</figure>\n'
                f'<!-- /wp:image -->'
            )
            content, n_replaced = re.subn(
                r'<!-- wp:image[^\n]*-->([\s\S]*?)<!-- /wp:image -->',
                new_block, content, count=1,
            )
            if n_replaced == 0:
                return ActionResult(False, "No image block found in the template content.")

        # ── 6. Create or update published post ────────────────────────────
        find_result = self.find_post(title, env, lang=lang)
        if not find_result.success:
            return find_result
        existing_id = find_result.data

        post_body = {
            'title':      title,
            'content':    content,
            'status':     'publish',
            'categories': cat_ids,
        }
        if lang:
            post_body['lang'] = lang

        try:
            if existing_id:
                post_resp = requests.post(
                    f"{base}/wp-json/wp/v2/posts/{existing_id}",
                    json=post_body, auth=auth, timeout=30,
                )
                verb = "updated"
            else:
                post_resp = requests.post(
                    f"{base}/wp-json/wp/v2/posts",
                    json=post_body, auth=auth, timeout=30,
                )
                verb = "created"

            if post_resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            post_resp.raise_for_status()
            saved_post = post_resp.json()
        except Exception as e:
            return ActionResult(False, f"Failed to save post: {e}")

        msg = f"Post {verb}. ID: {saved_post['id']}"
        if warnings:
            msg += "\nWarnings: " + "; ".join(warnings)
        return ActionResult(True, msg, data=saved_post.get('link', ''))
