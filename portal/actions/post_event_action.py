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

    @staticmethod
    def _post(url, *, params=None, json=None, auth, timeout=30):
        """POST that re-issues as POST on redirects (not GET).

        requests follows 301/302 by switching to GET, which on the WordPress
        REST API returns a list of existing posts instead of creating a new
        one.  This wrapper follows redirects manually, always re-posting to
        the redirect target so the body is never lost.

        WordPress sometimes returns a relative Location header (e.g.
        /wp-json/wp/v2/posts/) — resolved against the current URL via
        urljoin so the scheme and host are never lost.
        """
        from urllib.parse import urljoin
        resp = requests.post(
            url, params=params, json=json, auth=auth,
            timeout=timeout, allow_redirects=False,
        )
        # Follow up to 5 redirects; re-POST each time.
        for _ in range(5):
            if resp.status_code not in (301, 302, 307, 308):
                break
            location = resp.headers.get('Location', '')
            if not location:
                break
            # Resolve relative redirects (e.g. /wp-json/...) against the
            # URL that issued the redirect so scheme+host are always present.
            location = urljoin(resp.url, location)
            resp = requests.post(
                location, json=json, auth=auth,
                timeout=timeout, allow_redirects=False,
            )
        return resp

    @staticmethod
    def _clean_title(s: str) -> str:
        """Strip Unicode format characters (category Cf) and whitespace.

        Browsers and other apps embed invisible directional marks such as
        U+200F RIGHT-TO-LEFT MARK in copied Hebrew text.  WordPress never
        stores these, so a naive equality check fails.  Stripping Cf chars
        from both sides before comparing fixes the mismatch.
        """
        import unicodedata
        return ''.join(c for c in s if unicodedata.category(c) != 'Cf').strip()

    def find_post(self, title: str, env: str = 'staging', lang: str = '',
                  log_cb=None) -> ActionResult:
        """Return ActionResult with data=post_id (int) if found, data=None if not.

        log_cb: optional callable(str) — receives diagnostic lines so the
                caller can surface them in the UI log.  Pass None to suppress.

        Search strategy:
          1. Search with ?lang=<lang> (WPML-aware, preferred).
          2. If nothing matches, retry without ?lang (catches posts not
             registered in WPML's language table, or posts where WPML's
             REST filter blocks the search result).
        Both passes use per_page=100 to handle large archives where
        WordPress's recency ranking would bury older posts.
        """
        def _log(msg):
            if log_cb:
                log_cb(f"[find_post] {msg}\n")

        base  = get_cred('wp_url', env).rstrip('/')
        auth  = self._auth(env)
        clean = self._clean_title(title)

        _log(f"title (original) : {repr(title)}")
        _log(f"title (cleaned)  : {repr(clean)}")
        _log(f"lang hint        : {repr(lang)}")

        # Build the list of lang values to try.  Always end with '' (no filter)
        # as a fallback.  Deduplicate in case lang is already ''.
        lang_tries = [lang, ''] if lang else ['']

        # NOTE: ?search= is broken on WordPress.com staging — it returns HTTP 200
        # with an empty array [] regardless of the query.  We fetch posts
        # page-by-page and match the title locally instead.
        try:
            for lang_try in lang_tries:
                _log(f"--- pass lang={repr(lang_try)} ---")
                page = 1
                while True:
                    params = {'per_page': 100, 'page': page}
                    if lang_try:
                        params['lang'] = lang_try

                    url = f"{base}/wp-json/wp/v2/posts"
                    _log(f"GET {url}  params={params}")

                    resp = requests.get(url, params=params, auth=auth, timeout=30)
                    _log(f"HTTP {resp.status_code}  ({len(resp.content)} bytes)")

                    if resp.status_code == 401:
                        return ActionResult(False, "401 Unauthorized — check credentials.")
                    resp.raise_for_status()

                    posts      = resp.json()
                    total_pages = max(int(resp.headers.get('X-WP-TotalPages', 1)), 1)
                    total_posts = resp.headers.get('X-WP-Total', '?')
                    _log(f"page {page}/{total_pages}  posts this page: {len(posts)}  total: {total_posts}")

                    for p in posts:
                        t          = p.get('title', {}) or {}
                        rendered   = self._clean_title(t.get('rendered', ''))
                        is_match   = rendered == clean
                        _log(f"  post {p['id']:>7}  rendered={repr(t.get('rendered','')[:70])}  match={is_match}")
                        if is_match:
                            _log(f"  → MATCH")
                            return ActionResult(True, f"Found post ID {p['id']}", data=p['id'])

                    if page >= total_pages or not posts:
                        break
                    page += 1

                _log(f"no match in this pass")

            _log("exhausted all passes — not found")
            return ActionResult(True, "Not found", data=None)
        except Exception as e:
            _log(f"exception: {e}")
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

    def list_category_pairs(self, env: str = 'staging') -> ActionResult:
        """Fetch categories from WordPress grouped by WPML translation group.

        Calls the portal's custom endpoint (yedidya/v1/category-pairs) which
        returns each translation group as one row, so the Hebrew and English
        columns in the post-event window can be rendered with perfect
        alignment — row N on both sides is the same logical category.

        Returns ActionResult with data = [
            { 'trid': int,
              'he':   {'id': int, 'name': str, 'slug': str} | None,
              'en':   {'id': int, 'name': str, 'slug': str} | None },
            ...
        ]  sorted by Hebrew name (or English when no Hebrew).
        """
        base = get_cred('wp_url', env).rstrip('/')
        auth = self._auth(env)
        try:
            resp = requests.get(
                f"{base}/wp-json/yedidya/v1/category-pairs",
                auth=auth, timeout=30,
            )
            if resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            if resp.status_code == 404:
                return ActionResult(
                    False,
                    "Endpoint not found (yedidya/v1/category-pairs).\n"
                    "Update the Yedidya Admin Portal plugin on the site.",
                )
            resp.raise_for_status()
            return ActionResult(True, "Fetched.", data=resp.json())
        except Exception as e:
            return ActionResult(False, f"Failed to fetch category pairs: {e}")

    def find_template(self, template: str, env: str = 'staging') -> ActionResult:
        """Look up the template post/page on the site and return its identifying
        info so the user can find and edit it (e.g. to rename its slug).

        Tries posts then pages, with and without lang=en, mirroring run().
        On success, data is a dict with: title, link (public URL), edit_link
        (admin edit URL), post_type ('posts' or 'pages'), id.
        """
        base = get_cred('wp_url', env).rstrip('/')
        auth = self._auth(env)
        for post_type in ('posts', 'pages'):
            for lang_param in (None, 'en'):
                params = {'slug': template, 'context': 'edit', 'status': 'any'}
                if lang_param:
                    params['lang'] = lang_param
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
                        p = posts[0]
                        title = (p.get('title', {}) or {}).get('rendered', '') \
                                or (p.get('title', {}) or {}).get('raw', '')
                        return ActionResult(True, "Template found.", data={
                            'id':        p.get('id', 0),
                            'title':     title,
                            'link':      p.get('link', ''),
                            'edit_link': f"{base}/wp-admin/post.php?post={p.get('id', 0)}&action=edit",
                            'post_type': post_type,
                            'status':    p.get('status', ''),
                        })
                except Exception as e:
                    return ActionResult(False, f"Lookup failed: {e}")
        return ActionResult(False, f"Template '{template}' not found on the site.")

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

    def fetch_post(self, post_id: int, env: str = 'staging') -> ActionResult:
        """Fetch an existing post and return its image URL and category IDs.

        Used by the window to pre-populate the image thumbnail and category
        checkboxes when the user types/pastes the title of an existing post.

        Returns ActionResult with data = {
            'media_url':  str   — source URL of the first embedded image, or ''
            'categories': list  — WordPress category IDs assigned to this post
        }
        """
        base = get_cred('wp_url', env).rstrip('/')
        auth = self._auth(env)
        try:
            resp = requests.get(
                f"{base}/wp-json/wp/v2/posts/{post_id}",
                params={'context': 'edit'},
                auth=auth, timeout=30,
            )
            if resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            resp.raise_for_status()
            p = resp.json()

            raw_content = (p.get('content', {}) or {}).get('raw', '')
            m = re.search(r'<!-- wp:image \{"id":(\d+)', raw_content)
            media_id  = int(m.group(1)) if m else 0
            media_url = ''
            if media_id:
                m_resp = requests.get(
                    f"{base}/wp-json/wp/v2/media/{media_id}",
                    auth=auth, timeout=30,
                )
                if m_resp.status_code == 200:
                    media_url = m_resp.json().get('source_url', '')

            return ActionResult(True, "OK", data={
                'media_url':  media_url,
                'categories': p.get('categories', []),
            })
        except Exception as e:
            return ActionResult(False, f"Fetch post failed: {e}")

    def duplicate_to_lang(self, source_post_id: int, target_lang: str,
                          env: str = 'staging') -> ActionResult:
        """Create a WPML-linked translation copy of an existing post.

        Calls the portal's custom REST endpoint (yedidya/v1/duplicate-post)
        which uses WPML's PHP API (wpml_set_element_language_details) to
        create the duplicate and link the two posts as language siblings.
        This is more reliable than passing icl_translation_of via the
        standard WP REST API, which WPML ignores on some versions.

        Returns ActionResult with data={'link', 'id'} on success.
        """
        base = get_cred('wp_url', env).rstrip('/')
        auth = self._auth(env)

        try:
            resp = self._post(
                f"{base}/wp-json/yedidya/v1/duplicate-post",
                json={
                    'source_post_id': source_post_id,
                    'target_lang':    target_lang,
                },
                auth=auth, timeout=30,
            )
            if resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            if resp.status_code == 404:
                return ActionResult(
                    False,
                    "Custom endpoint not found (yedidya/v1/duplicate-post).\n"
                    "Make sure the Yedidya Admin Portal plugin is up to date on the site.",
                )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return ActionResult(
                    False,
                    "Duplicate endpoint returned a list instead of a post object — "
                    "the translation was not created.",
                )
        except Exception as e:
            return ActionResult(False, f"Failed to duplicate post: {e}")

        post_id  = data.get('id', 0)
        link     = data.get('link', '')
        warnings = data.get('warnings', []) or []

        msg = f"Duplicate created in '{target_lang}'. ID: {post_id}"
        if warnings:
            msg += "\nWarnings:\n  - " + "\n  - ".join(warnings)
        return ActionResult(True, msg, data={
            'link': link,
            'id':   post_id,
        })

    def run(self, template: str, title: str, categories: list,
            date: str = '', description: str = '', image_path: str = '',
            caption: str = '', lang: str = '', env: str = 'staging',
            is_new_image: bool = False, progress_cb=None,
            existing_id: int = None) -> ActionResult:
        """Create or update one post in one language. Fully self-contained:
        every call is treated as an independent entity — no cross-language
        state, no shared image uploads, no shared create/update flags.

        existing_id: when provided, skip the title lookup and update that
        specific post. Used by the bilingual-create flow to update the
        WPML-duplicated English post by its known ID, and by the
        "Update existing post" checkbox to rename a post (change its title
        without creating a new one).

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

        def _progress(msg):
            if progress_cb:
                progress_cb(msg)

        # ── 1. Fetch template (posts then pages; each tried with and without lang=en) ──
        # NOTE: use a distinct loop variable (_lang_try) so the function-level
        # `lang` parameter is not accidentally overwritten.
        _progress("Fetching template…")
        posts = []
        for post_type in ('posts', 'pages'):
            for _lang_try in (None, 'en'):
                params = {'slug': template, 'context': 'edit', 'status': 'any'}
                if _lang_try:
                    params['lang'] = _lang_try
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
        # CRITICAL: pass lang= to the categories endpoint, otherwise
        # WordPress returns categories in the default language only.  An
        # English save would then fail to resolve English category names
        # (they don't exist in the Hebrew category list), the post would be
        # saved with no categories assigned, and the warning would be
        # silently buried in the log.
        _progress("Resolving categories…")
        cat_ids  = []
        warnings = []
        if categories:
            try:
                cat_params = {'per_page': 100}
                if lang:
                    cat_params['lang'] = lang
                cat_resp = requests.get(
                    f"{base}/wp-json/wp/v2/categories",
                    params=cat_params,
                    auth=auth, timeout=30,
                )
                cat_resp.raise_for_status()
                name_to_id = {c['name']: c['id'] for c in cat_resp.json()}
                for name in categories:
                    if name in name_to_id:
                        cat_ids.append(name_to_id[name])
                    else:
                        warnings.append(f"Category not found on site ({lang or 'default'}): '{name}'")
            except Exception as e:
                return ActionResult(False, f"Failed to fetch categories: {e}")

        # ── 4. Find existing post (needed before image step) ──────────────
        # Skip the lookup if the caller already knows the ID (e.g. updating
        # the WPML-duplicated English post by its known post_id, or the
        # "Update existing post" checkbox locked in a target).
        if existing_id is None:
            _progress("Checking for existing post…")
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
                _progress("Uploading image…")
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
                        image_data = f.read()
                    media_resp = requests.post(
                        f"{base}/wp-json/wp/v2/media",
                        headers={
                            'Content-Disposition': f'attachment; filename="{filename}"',
                            'Content-Type': mime,
                        },
                        data=image_data,
                        auth=auth, timeout=60,
                        allow_redirects=False,
                    )
                    # Media upload must not be silently redirected either.
                    if media_resp.status_code in (301, 302, 307, 308):
                        return ActionResult(
                            False,
                            f"Image upload was redirected ({media_resp.status_code}). "
                            f"Check the WordPress URL in credentials.",
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
        _progress("Saving post…")

        post_body = {
            'title':      title,
            'content':    content,
            'status':     'publish',
            'categories': cat_ids,
        }
        # WPML reads language from the URL query parameter, not from the
        # JSON body. Passing lang= in the body is silently ignored.
        lang_params = {'lang': lang} if lang else {}

        try:
            if existing_id:
                post_resp = self._post(
                    f"{base}/wp-json/wp/v2/posts/{existing_id}",
                    params=lang_params,
                    json=post_body, auth=auth, timeout=30,
                )
                verb = "updated"
            else:
                post_resp = self._post(
                    f"{base}/wp-json/wp/v2/posts",
                    params=lang_params,
                    json=post_body, auth=auth, timeout=30,
                )
                verb = "created"

            if post_resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            post_resp.raise_for_status()
            saved_post = post_resp.json()
            # A list response means the POST was redirected to a GET (WordPress
            # URL normalisation — e.g. trailing-slash mismatch).  requests
            # follows 301/302 by switching to GET, which returns existing posts
            # instead of creating a new one.  Never accept this silently.
            if isinstance(saved_post, list):
                if post_resp.history:
                    chain = ' → '.join(
                        f"{r.status_code} {r.url}" for r in post_resp.history
                    )
                    return ActionResult(
                        False,
                        f"Post creation failed — the request was redirected and "
                        f"WordPress returned a list of existing posts instead of "
                        f"creating a new one.\n\n"
                        f"Redirect chain: {chain}\n"
                        f"Final URL: {post_resp.url}\n\n"
                        f"Fix: make sure the WordPress URL saved in credentials "
                        f"matches the site's canonical URL exactly "
                        f"(check trailing slash).",
                    )
                return ActionResult(
                    False,
                    "Post creation returned an unexpected list response — "
                    "the post was not created. Check WordPress admin.",
                )
        except Exception as e:
            return ActionResult(False, f"Failed to save post: {e}")

        msg = f"Post {verb}. ID: {saved_post['id']}"
        if warnings:
            msg += "\nWarnings: " + "; ".join(warnings)
        return ActionResult(True, msg, data={
            'link':    saved_post.get('link', ''),
            'id':      saved_post.get('id', 0),
            'created': not bool(existing_id),  # True when this call inserted a new post
        })
