# Yedidya WordPress Site — Reference

## Hosting

- **Provider:** WordPress.com (managed)
- **Staging URL:** https://staging-9e0a-kehilatyedidya.wpcomstaging.com/
- **Production URL:** https://yedidya.org.il
- **SFTP host:** sftp.wp.com

## Languages

- **Default:** Hebrew
- **Secondary:** English (via WPML)
- Note: the WP REST API returns plugin names and some other fields in Hebrew due to the default locale.

## Products

- All products are membership options (15 products total).
- Mix of standard WooCommerce products (regular price) and WooCommerce Name Your Price products (minimum price).

## User / Membership Model

- Unknown — to be documented when investigated.

## REST APIs in use

| API | Base path | Auth |
|-----|-----------|------|
| WordPress REST API | `/wp-json/wp/v2/` | Basic Auth (Application Password) |
| WooCommerce REST API v3 | `/wp-json/wc/v3/` | Basic Auth (Application Password) |
| Custom Yedidya endpoints | `/wp-json/yedidya/v1/` | Basic Auth (Application Password) |

### Custom endpoints (registered by the portal PHP plugin)
- `POST /wp-json/yedidya/v1/gdpr-erase` — full GDPR user erasure including WooCommerce orders
- `POST /wp-json/yedidya/v1/duplicate-post` — WPML-linked post duplication
- `GET  /wp-json/yedidya/v1/category-pairs` — all categories grouped by WPML trid
- `GET  /wp-json/yedidya/v1/db-extract` — (DB Extract action endpoint)

## Known Quirks

- **`?search=` on WP REST API is broken on WordPress.com staging** — returns `200 []` for every query. The portal works around this by fetching posts page-by-page and matching titles locally.
- **`context=edit` on staging returns empty results silently** — WordPress.com staging returns `200 []` when `context=edit` is requested by an account that lacks `edit_others_posts`, with no 403 error.
- **WordPress.com staging returns 400 on RFC 5987 Hebrew filenames in HTTP headers** — filenames must be ASCII.
- **WPML `?lang=` filter can silently return 0 results** for posts not registered in WPML's language table — the portal retries without `?lang=` as fallback.

## Active Plugins

| Plugin | Version | Notes |
|--------|---------|-------|
| Advanced Order Export For WooCommerce | 4.1.0 | |
| Akismet Anti-spam | 5.7 | |
| Checkout Field Editor for WooCommerce | 2.1.9 | |
| Code Snippets | 3.9.6 | |
| Contact Form CFDB7 | 1.3.6 | |
| Contact Form 7 | 6.1.6 | |
| Dynamic Year Block | 1.0.0 | |
| EmbedPress | 4.5.5 | |
| Force Email 2FA for All Users (Excluding Admins) | 1.3 | |
| Gutenberg | 23.3.2 | Block editor |
| Import and export users and customers | 2.3.7 | |
| Jetpack | 16.0-a.1 | |
| Jetpack Boost | 4.6.1 | |
| Layout Grid | 1.8.5 | |
| New User Approve | 3.2.5 | Likely part of membership flow |
| Page Optimize | 0.6.3 | |
| Popup Maker | 1.22.0 | |
| Profile Builder | 3.16.2 | User registration/profile — likely part of membership flow |
| Profile Builder Basic | 3.12.5 | |
| Two Factor | 0.16.0 | |
| UpdraftPlus - Backup/Restore | 1.26.5 | |
| WooCommerce | 10.8.1 | Core e-commerce |
| WooCommerce Name Your Price | 3.7.4 | Used for donation/flexible membership products |
| WooCommerce PayPal Payments | 4.0.4 | Payment gateway |
| WooCommerce.com Update Manager | 1.0.3 | |
| WooPayments | 10.8.0 | Payment gateway |
| Woocommerce iCredit | 4.0.0 | Payment gateway (Israeli) |
| WP Mail SMTP | 4.8.0 | |
| WPCode Lite | 2.3.6 | |
| WPForms Lite | 1.10.1.1 | |
| WPML Multilingual CMS | 4.9.5 | Hebrew/English bilingual |
| WPML Multilingual & Multicurrency for WooCommerce | 5.5.6 | |
| WordPress Importer | 0.9.5 | |
| YYDevelopment - Accessibility | 2.3.1 | |
| Yedidya Admin Portal | 1.0.0 | Our custom portal plugin (inactive — superseded by current plugin version) |
| Yedidya GDPR Erase | 1.1.0 | Custom GDPR erasure plugin |
| Yedidya Member Export | 1.0 | Custom member export |

## Inactive Plugins

| Plugin | Version | Notes |
|--------|---------|-------|
| Classic Editor | 1.7.0 | Replaced by Gutenberg |
| LiteSpeed Cache | 7.8.1 | |
| Order Export & Order Import for WooCommerce | 2.7.4 | |
| Redirect Pro for WooCommerce | 1.0.1 | |
| WPML All Import | 2.3.2 | |
| WPML Export and Import | 1.2.1 | |
| WPML String Translation | 3.5.3 | |
