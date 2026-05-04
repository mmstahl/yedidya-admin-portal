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
    'event-with-static-image': {
        'label':  'Event with Static Image',
        'fields': ['date', 'description', 'image'],
        'placeholders': {
            'date':        'Hebrew-and-Gregorian-dates',
            'description': 'Description-of-this-event',
        },
    },
    'event-with-clickable-image': {
        'label':  'Event with Clickable Image',
        'fields': ['image', 'caption'],
        'placeholders': {
            'title_content': 'Event Template 2 (Header, Description, Image link)',
        },
        # When True, the rendered image block links to the media file itself
        # (opens in a new tab). Suitable for posts whose main purpose is to
        # display a single shareable image.
        'image_link': True,
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

    def get_post_media_id(self, post_id: int, env: str = 'staging') -> int:
        """Return the first image block's media ID from a post's raw content, or 0 if not found."""
        base = get_cred('wp_url', env).rstrip('/')
        auth = self._auth(env)
        try:
            resp = requests.get(
                f"{base}/wp-json/wp/v2/posts/{post_id}",
                params={'context': 'edit'},
                auth=auth, timeout=30,
            )
            resp.raise_for_status()
            raw = resp.json().get('content', {}).get('raw', '')
            m = re.search(r'<!-- wp:image \{"id":(\d+)', raw)
            return int(m.group(1)) if m else 0
        except Exception:
            return 0

    def delete_media(self, media_id: int, env: str = 'staging') -> ActionResult:
        """Permanently delete a media item (bypasses trash)."""
        base = get_cred('wp_url', env).rstrip('/')
        auth = self._auth(env)
        try:
            resp = requests.delete(
                f"{base}/wp-json/wp/v2/media/{media_id}",
                params={'force': True},
                auth=auth, timeout=30,
            )
            if resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            resp.raise_for_status()
            return ActionResult(True, f"Image {media_id} permanently deleted.")
        except Exception as e:
            return ActionResult(False, f"Image delete failed: {e}")

    def run(self, template: str, title: str, categories: list,
            date: str = '', description: str = '', image_path: str = '',
            caption: str = '', lang: str = '', env: str = 'staging',
            is_new_image: bool = False) -> ActionResult:
        """Create or update one post in one language. Fully self-contained:
        every call is treated as an independent entity — no cross-language
        state, no shared image uploads, no shared create/update flags.

        Image resolution rules (per this single post):
          - image_path provided AND (is_new_image OR no existing post)
              → upload image_path  (user picked it, OR creating from a loaded default)
          - else, existing post found
              → reuse media already embedded in the existing post (Option C)
          - else
              → return error: a new post needs an image
        """

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

        # ── 4. Find existing post (needed before image step) ──────────────
        find_result = self.find_post(title, env, lang=lang)
        if not find_result.success:
            return find_result
        existing_id = find_result.data

        # ── 5. Resolve or upload image (per this post — fully independent) ────
        if 'image' in tpl_config.get('fields', []):
            new_id = new_url = None

            # Decide what to do with the image, based on the state of THIS post only:
            #   - Upload the local file if the user picked a new one this session,
            #     OR if there is no existing post to reuse from.
            #   - Otherwise reuse the image already embedded in the existing post.
            #   - If neither applies (new post, no image at all) — error out.
            should_upload = bool(image_path) and (is_new_image or not existing_id)

            if should_upload:
                filename = os.path.basename(image_path)
                ext      = os.path.splitext(filename)[1].lower()
                mime_map = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png',  '.gif': 'image/gif',
                    '.webp': 'image/webp',
                }
                mime = mime_map.get(ext, 'image/jpeg')
                try:
                    with open(image_path, 'rb') as f:
                        media_resp = requests.post(
                            f"{base}/wp-json/wp/v2/media",
                            headers={
                                'Content-Disposition': f'attachment; filename="{filename}"',
                                'Content-Type': mime,
                            },
                            data=f.read(),
                            auth=auth, timeout=60,
                        )
                    if media_resp.status_code == 401:
                        return ActionResult(False, "401 Unauthorized — check credentials.")
                    media_resp.raise_for_status()
                    media   = media_resp.json()
                    new_id  = media['id']
                    new_url = media['source_url']
                except Exception as e:
                    return ActionResult(False, f"Failed to upload image: {e}")

            elif existing_id:
                # No new image; reuse the one already embedded in the existing post (Option C).
                try:
                    post_resp = requests.get(
                        f"{base}/wp-json/wp/v2/posts/{existing_id}",
                        params={'context': 'edit'},
                        auth=auth, timeout=30,
                    )
                    post_resp.raise_for_status()
                    existing_content = post_resp.json().get('content', {}).get('raw', '')
                    m = re.search(r'<!-- wp:image \{"id":(\d+)', existing_content)
                    if m:
                        existing_media_id = int(m.group(1))
                        media_resp = requests.get(
                            f"{base}/wp-json/wp/v2/media/{existing_media_id}",
                            auth=auth, timeout=30,
                        )
                        if media_resp.status_code == 200:
                            media_data = media_resp.json()
                            new_id  = media_data['id']
                            new_url = media_data['source_url']
                except Exception:
                    pass  # fall through to the error below
                if new_id is None:
                    return ActionResult(
                        False,
                        f"Could not retrieve the existing image from post {existing_id}. "
                        f"Please select an image and try again.",
                    )

            else:
                # New post with no image at all
                return ActionResult(
                    False,
                    "An image is required for a new post. Please select or paste an image.",
                )

            if new_id:
                # ── Replace first image block ──────────────────────────
                figcaption = (
                    f'<figcaption class="wp-element-caption">{caption}</figcaption>'
                    if caption else ''
                )

                # Some templates want the image to be a clickable link to the
                # media file itself, opening in a new tab. Controlled per
                # template via the 'image_link' flag in TEMPLATES.
                if tpl_config.get('image_link'):
                    block_attrs = (
                        f'{{"id":{new_id},"sizeSlug":"large",'
                        f'"linkDestination":"media","linkTarget":"_blank",'
                        f'"rel":"noreferrer noopener"}}'
                    )
                    img_html = (
                        f'<a href="{new_url}" target="_blank" rel="noreferrer noopener">'
                        f'<img src="{new_url}" alt="" class="wp-image-{new_id}"/>'
                        f'</a>'
                    )
                else:
                    block_attrs = (
                        f'{{"id":{new_id},"sizeSlug":"large","linkDestination":"none"}}'
                    )
                    img_html = f'<img src="{new_url}" alt="" class="wp-image-{new_id}"/>'

                new_block = (
                    f'<!-- wp:image {block_attrs} -->\n'
                    f'<figure class="wp-block-image size-large">'
                    f'{img_html}'
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
