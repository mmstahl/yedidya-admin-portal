"""
Post & Event action.

Flow:
  1. Fetch the event template post by slug (raw Gutenberg content).
  2. Replace 'Date' and 'Description' placeholder strings in the content.
  3. Upload the provided image to the WordPress media library.
  4. Replace the first embedded image block with the uploaded image.
  5. Create a new draft post with the modified content and given title.
"""
import os
import re
import requests

from portal.actions.base_action import BaseAction, ActionResult
from portal.credentials.credential_manager import get as get_cred

TEMPLATE_SLUG = 'event-template-1'


class PostEventAction(BaseAction):
    name = "Post & Event"
    description = "Create a new event post from the template"

    def run(self, title: str, date: str, description: str,
            image_path: str, env: str = 'staging') -> ActionResult:

        wp_url  = get_cred('wp_url',      env)
        wp_user = get_cred('wp_user',     env)
        wp_pass = get_cred('wp_password', env)
        auth    = (wp_user, wp_pass)
        base    = wp_url.rstrip('/')

        # ── 1. Fetch template ──────────────────────────────────────────────
        try:
            resp = requests.get(
                f"{base}/wp-json/wp/v2/posts",
                params={'slug': TEMPLATE_SLUG, 'context': 'edit', 'status': 'any'},
                auth=auth, timeout=30,
            )
            if resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            resp.raise_for_status()
            posts = resp.json()
        except Exception as e:
            return ActionResult(False, f"Failed to fetch template: {e}")

        if not posts:
            return ActionResult(False, f"Template post '{TEMPLATE_SLUG}' not found.")

        content = posts[0].get('content', {}).get('raw', '')
        if not content:
            return ActionResult(False, "Template post has no raw content. "
                                       "Make sure the REST API returns raw content.")

        # ── 2. Replace text placeholders ──────────────────────────────────
        content = content.replace('Hebrew-and-Gregorian-dates', date)
        content = content.replace('Description-of-this-event', description)

        # ── 3. Upload image ────────────────────────────────────────────────
        try:
            filename = os.path.basename(image_path)
            ext      = os.path.splitext(filename)[1].lower()
            mime_map = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png',  '.gif': 'image/gif',
                '.webp': 'image/webp',
            }
            mime = mime_map.get(ext, 'image/jpeg')

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
            media = media_resp.json()
        except Exception as e:
            return ActionResult(False, f"Failed to upload image: {e}")

        new_id  = media['id']
        new_url = media['source_url']

        # ── 4. Replace first image block ───────────────────────────────────
        new_block = (
            f'<!-- wp:image {{"id":{new_id},"sizeSlug":"large","linkDestination":"none"}} -->\n'
            f'<figure class="wp-block-image size-large">'
            f'<img src="{new_url}" alt="" class="wp-image-{new_id}"/>'
            f'</figure>\n'
            f'<!-- /wp:image -->'
        )
        content, n_replaced = re.subn(
            r'<!-- wp:image[^\n]*-->([\s\S]*?)<!-- /wp:image -->',
            new_block,
            content,
            count=1,
        )
        if n_replaced == 0:
            return ActionResult(False, "No image block found in the template content.")

        # ── 5. Create or update draft post ────────────────────────────────
        # Check if a post with this title already exists.
        existing_id = None
        try:
            search_resp = requests.get(
                f"{base}/wp-json/wp/v2/posts",
                params={'search': title, 'status': 'any', 'context': 'edit', 'per_page': 20},
                auth=auth, timeout=30,
            )
            search_resp.raise_for_status()
            for p in search_resp.json():
                if p.get('title', {}).get('raw', '').strip() == title:
                    existing_id = p['id']
                    break
        except Exception as e:
            return ActionResult(False, f"Failed to search for existing post: {e}")

        post_body = {'title': title, 'content': content, 'status': 'draft'}

        try:
            if existing_id:
                url = f"{base}/wp-json/wp/v2/posts/{existing_id}"
                post_resp = requests.post(url, json=post_body, auth=auth, timeout=30)
                verb = "updated"
            else:
                url = f"{base}/wp-json/wp/v2/posts"
                post_resp = requests.post(url, json=post_body, auth=auth, timeout=30)
                verb = "created"

            if post_resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            post_resp.raise_for_status()
            saved_post = post_resp.json()
        except Exception as e:
            return ActionResult(False, f"Failed to save post: {e}")

        post_url = saved_post.get('link', '')
        return ActionResult(True, f"Draft post {verb}. ID: {saved_post['id']}", data=post_url)
