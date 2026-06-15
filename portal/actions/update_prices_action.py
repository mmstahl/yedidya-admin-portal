"""
Update Product Prices action.

Reads an Excel file with columns: ID, Regular price, Minimum price.
Validates all rows first, then fetches product details from WooCommerce,
shows a preview, and updates prices via the WooCommerce REST API.

Price types:
  - Regular price: standard WooCommerce product (regular_price field)
  - Minimum price: WooCommerce Name Your Price plugin (_min_price meta key)
"""
import openpyxl
import requests

from portal.actions.base_action import BaseAction, ActionResult
from portal.credentials.credential_manager import get as get_cred

WC_PRODUCTS_ENDPOINT = '/wp-json/wc/v3/products'


class UpdatePricesAction(BaseAction):
    name = "Update Product Prices"
    description = "Update WooCommerce product prices from an Excel file"

    def parse_excel(self, path):
        """
        Parse and validate the Excel file.
        Returns (rows, error_string_or_None).
        rows = list of {id, regular_price, min_price} — exactly one price is non-None.
        Completely empty rows are silently skipped.
        Aborts on any structural error before returning rows.
        """
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
        except FileNotFoundError:
            return [], f"File not found: {path}"
        except Exception as e:
            return [], f"Could not open file: {e}"

        rows_iter = ws.iter_rows(values_only=True)
        try:
            header = next(rows_iter)
        except StopIteration:
            return [], "Excel file is empty."

        header_lower = [str(h).strip().lower() if h is not None else '' for h in header]

        def find_col(name):
            try:
                return header_lower.index(name)
            except ValueError:
                return None

        col_id  = find_col('id')
        col_reg = find_col('regular price')
        col_min = find_col('minimum price')

        if col_id is None:
            return [], "Column 'ID' not found in the Excel file."
        if col_reg is None:
            return [], "Column 'Regular price' not found in the Excel file."
        if col_min is None:
            return [], "Column 'Minimum price' not found in the Excel file."

        rows = []
        for row_num, row in enumerate(rows_iter, start=2):
            # Skip completely empty rows
            if all(cell is None or str(cell).strip() == '' for cell in row):
                continue

            def cell(col):
                val = row[col] if col < len(row) else None
                return str(val).strip() if val is not None else ''

            id_str  = cell(col_id)
            reg_str = cell(col_reg)
            min_str = cell(col_min)

            if not id_str and not reg_str and not min_str:
                continue

            if not id_str:
                return [], f"Row {row_num}: missing product ID."
            try:
                product_id = int(float(id_str))
            except ValueError:
                return [], f"Row {row_num}: '{id_str}' is not a valid product ID."

            has_reg = bool(reg_str)
            has_min = bool(min_str)

            if has_reg and has_min:
                return [], (
                    f"Row {row_num} (ID {product_id}): both Regular price and Minimum price "
                    f"are set. Each product must have exactly one."
                )
            if not has_reg and not has_min:
                return [], (
                    f"Row {row_num} (ID {product_id}): neither Regular price nor "
                    f"Minimum price is set."
                )

            price_str   = reg_str if has_reg else min_str
            price_label = "Regular price" if has_reg else "Minimum price"
            try:
                price = float(price_str)
            except ValueError:
                return [], (
                    f"Row {row_num} (ID {product_id}): {price_label} '{price_str}' "
                    f"is not a valid number."
                )
            if price < 0:
                return [], (
                    f"Row {row_num} (ID {product_id}): {price_label} cannot be negative."
                )

            rows.append({
                'id':            product_id,
                'regular_price': price if has_reg else None,
                'min_price':     price if has_min else None,
            })

        if not rows:
            return [], "No product rows found in the Excel file."

        return rows, None

    def preview(self, rows, env='staging'):
        """
        Fetch each product from WooCommerce to get its name, current price, and type.
        Aborts if a product is not found or if the price type in the Excel doesn't
        match the product's type in WooCommerce.

        Returns (preview_rows, error_string_or_None).
        preview_rows = list of {id, name, price_type, current_price, new_price, raw_row}
          price_type: 'regular' | 'min'
          current_price / new_price: display strings
        """
        wp_url  = get_cred('wp_url',      env)
        wp_user = get_cred('wp_user',     env)
        wp_pass = get_cred('wp_password', env)

        preview_rows = []

        for row in rows:
            product_id = row['id']
            try:
                product, error = self._fetch_product(wp_url, wp_user, wp_pass, product_id)
            except ConnectionError as e:
                return [], str(e)

            if error:
                return [], error

            meta   = {m['key']: m['value'] for m in product.get('meta_data', [])}
            is_nyp = meta.get('_nyp') == 'yes'
            wants_min = row['min_price'] is not None

            if wants_min and not is_nyp:
                return [], (
                    f"Product {product_id} (\"{product['name']}\"): Excel sets a Minimum "
                    f"price, but this product is not set up as \"Name Your Price\". "
                    f"Update the product type in WooCommerce first."
                )
            if not wants_min and is_nyp:
                return [], (
                    f"Product {product_id} (\"{product['name']}\"): Excel sets a Regular "
                    f"price, but this product is set up as \"Name Your Price\". "
                    f"Update the product type in WooCommerce first."
                )

            if is_nyp:
                raw = meta.get('_min_price', '')
                try:
                    current_price = f"₪{float(raw):.2f} min"
                except (ValueError, TypeError):
                    current_price = "(not set)"
                new_price  = f"₪{row['min_price']:.2f} min"
                price_type = 'min'
            else:
                raw = product.get('regular_price', '')
                try:
                    current_price = f"₪{float(raw):.2f}"
                except (ValueError, TypeError):
                    current_price = "(not set)"
                new_price  = f"₪{row['regular_price']:.2f}"
                price_type = 'regular'

            preview_rows.append({
                'id':            product_id,
                'name':          product['name'],
                'price_type':    price_type,
                'current_price': current_price,
                'new_price':     new_price,
                'raw_row':       row,
            })

        return preview_rows, None

    def run(self, preview_rows, env='staging', progress_callback=None) -> ActionResult:
        """
        Update each product price via WooCommerce REST API.
        preview_rows: list from preview()
        progress_callback(current, total, message)
        """
        wp_url  = get_cred('wp_url',      env)
        wp_user = get_cred('wp_user',     env)
        wp_pass = get_cred('wp_password', env)

        log    = []
        total  = len(preview_rows)
        errors = 0

        for i, prow in enumerate(preview_rows, 1):
            product_id = prow['id']
            name       = prow['name']
            row        = prow['raw_row']

            msg = f"Updating {name} (#{product_id})…"
            log.append(msg)
            if progress_callback:
                progress_callback(i, total, msg)

            result_msg, is_error = self._update_product(
                wp_url, wp_user, wp_pass, product_id, row
            )
            log.append(f"  {'✗ ERROR' if is_error else '✓'} {result_msg}")
            if is_error:
                errors += 1

        if errors == 0:
            return ActionResult(True, f"Updated {total} product(s).", log)
        elif errors < total:
            return ActionResult(
                False,
                f"Completed with {errors} error(s). {total - errors}/{total} updated.",
                log,
            )
        else:
            return ActionResult(False, "All updates failed.", log)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_product(self, wp_url, wp_user, wp_pass, product_id):
        """
        Returns (product_dict, error_string_or_None).
        Raises ConnectionError on auth failures.
        """
        try:
            url  = f"{wp_url.rstrip('/')}{WC_PRODUCTS_ENDPOINT}/{product_id}"
            resp = requests.get(url, auth=(wp_user, wp_pass), timeout=15)
            if resp.status_code == 401:
                raise ConnectionError("401 Unauthorized — check credentials")
            if resp.status_code == 403:
                raise ConnectionError("403 Forbidden — account lacks admin access")
            if resp.status_code == 404:
                return None, f"Product ID {product_id} not found in WordPress."
            resp.raise_for_status()
            return resp.json(), None
        except ConnectionError:
            raise
        except Exception as e:
            return None, str(e)

    def _update_product(self, wp_url, wp_user, wp_pass, product_id, row):
        """
        PUT the new price to WooCommerce. Returns (message, is_error).
        """
        try:
            url = f"{wp_url.rstrip('/')}{WC_PRODUCTS_ENDPOINT}/{product_id}"
            if row['regular_price'] is not None:
                body = {'regular_price': str(row['regular_price'])}
            else:
                body = {'meta_data': [{'key': '_min_price', 'value': str(row['min_price'])}]}

            resp = requests.put(url, json=body, auth=(wp_user, wp_pass), timeout=15)
            if resp.status_code == 401:
                raise ConnectionError("401 Unauthorized — check credentials")
            if not resp.ok:
                return f"HTTP {resp.status_code}: {resp.text[:120]}", True
            return "Updated", False
        except ConnectionError as e:
            return str(e), True
        except Exception as e:
            return str(e), True
