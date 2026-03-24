# Yedidya Admin Portal — User Guide

The Yedidya Admin Portal is a Windows desktop tool for site administrators. It lets you run common WordPress admin tasks — generating the members list, removing users — from a simple local interface, without logging into WordPress directly.

Credentials are stored securely on your machine (Windows Credential Manager). Nothing is saved in plain text.

---

## First Run

When you open the portal for the first time, a credentials window will appear. Fill in your details for Staging and/or Production:

- **Site URL** and **SFTP host/user** are pre-filled — don't change them unless you know what you are doing and why.
- **Application Password** is a WordPress-generated password, not your login password. To create one: log into WordPress → Users → Your Profile → scroll to *Application Passwords* → enter a name (e.g. "Portal") → click *Add New*. Copy the password and paste it here.
- **SFTP Password** — ask the site administrator.

You only do this once. Credentials are saved and reused on every subsequent launch.

---

## Staging vs. Production

The portal has two environments. The toggle is at the top of the main window.

- **Staging** — a test copy of the site. Use this by default. Mistakes here don't affect the live site.
- **Production** — the live site. Switch to this only when you're ready to publish.

The portal always opens in Staging mode.

---

## Members List

Fetches the data needed for the members list (e.g. names, phones, email etc.) of all existing accounts from WordPress, generates a formatted PDF, and uploads it to the website.
See more details below. 


**How to run:**

1. Click **Go** next to *Members List*.
2. Check the file paths — they default to the folder where the portal is installed. You can leave them as-is unless you want the files saved somewhere else. Any change is remembered for next time.
3. Click **Run**.

The portal runs three steps in sequence:

| Step | What happens |
|------|-------------|
| Fetch | Downloads the current member list from WordPress into a CSV file |
| Process | Cleans and sorts the data. Accounts that have the approval to publish in the members list set to "No" are filtered out |
| Generate PDF | Produces the formatted members list PDF (In Hebrew; there is no option currently to have it in English)|

In **Staging**, the PDF is uploaded automatically after generation.

In **Production**, the PDF is opened for you to review first. After reviewing, you'll be asked to confirm before the upload proceeds. If you close the PDF without confirming, the upload is skipped and the file is saved locally.

**When done**, click *Done* to return to the main window.

---

## Delete Users

Removes WordPress users based on a CSV list of email addresses.

**How to run:**

1. Prepare a CSV file with one email address per row. A column header (`email`, `Email`, or `EMAIL`) is recognised automatically — if there's no header, the first column is used.
2. Click **Go** next to *Delete Users*.
3. Enter the path to your CSV file and click **Preview**.
4. The portal looks up each email in WordPress and shows you:
   - **Found** — users that will be deleted (name + email)
   - **Not found** — emails with no matching WordPress account
5. Review the list. If it looks right, click **Run**.

No users are deleted before you confirm.

**Deletion modes:**

| Mode | What is removed |
|------|----------------|
| Standard (default) | WordPress account + all content associated with that user |
| GDPR Erase (checkbox) | Same as above, plus personal data anonymised in WooCommerce orders (name, address, email, phone) |

> **Note on GDPR Erase:** WooCommerce orders are not deleted — financial records must be retained for tax compliance. However, all personal details within those orders are replaced with anonymous placeholders, so the individual can no longer be identified.

When the GDPR checkbox is ticked, a confirmation prompt will appear before the portal proceeds.

---

## Updating Credentials

Click **Update Credentials** in the top-right of the main window at any time.

If a connection fails with an authentication error, the credentials window opens automatically.
