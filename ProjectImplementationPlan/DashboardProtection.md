# Authentication & Security Implementation Plan

## Goal

Implement a complete authentication and authorization system for the admin dashboard.

The protected page is:

```text
/history
```

The application uses:

* React frontend
* FastAPI backend
* Supabase (Authentication + Database)

The backend is the **only** component that communicates with Supabase. The frontend must never communicate directly with Supabase.

The `admin_users` table already exists and contains the authorized administrator(s). Initially it contains:

* `sherwindesouza9@gmail.com`

Only users whose email exists in `admin_users` may access the application.

There must be **no signup flow**.

---

# Architecture

```text
React
    │
    ▼
FastAPI
    │
    ├── Supabase Auth
    └── Supabase Database
```

All authentication, authorization and database operations must be performed by FastAPI.

Do not use the Supabase JavaScript client in the frontend.

---

# 1. Login

Create:

```text
POST /auth/login
```

Request body:

```json
{
  "email": "...",
  "password": "..."
}
```

Backend flow:

1. Authenticate the credentials using Supabase Auth.
2. If authentication fails, return `401 Unauthorized`.
3. Retrieve the authenticated user's email.
4. Verify that the email exists in the `admin_users` table.
5. If the email is not present:

   * End the authenticated session.
   * Return `403 Forbidden`.
6. If successful:

   * Create the authenticated session.
   * Store the session using a secure HTTP-only cookie.
7. Return a success response.

The frontend must never store authentication tokens in localStorage or sessionStorage.

---

# 2. Forgot Password

Create:

```text
POST /auth/forgot-password
```

Request:

```json
{
  "email": "..."
}
```

Backend:

* Trigger Supabase's password reset email.
* Configure the reset link to redirect back to the frontend.
* Always return a generic success response.

---

# 3. Update Password

Create a frontend page:

```text
/reset-password
```

After the user clicks the password reset link from their email:

* Display a form for entering a new password.
* Submit the new password to:

```text
POST /auth/update-password
```

Backend:

* Update the authenticated user's password through Supabase Auth.
* Return success.

After completion:

* Redirect the user to the login page.

This flow is also used when the initial administrator sets their password.

---

# 4. Session Management

Authentication must use secure cookies.

The authentication cookie must be:

* HTTP-only
* Secure
* SameSite=Lax (or stricter where appropriate)

The browser should automatically send the cookie with every request.

The frontend must never manually manage authentication tokens.

---

# 5. Authentication Check

Create:

```text
GET /auth/me
```

Purpose:

Determine whether the current browser session is authenticated.

Backend:

* Validate the authentication cookie.
* If valid:

  * Return the authenticated user's information.
* Otherwise:

  * Return `401 Unauthorized`.

The frontend should call this endpoint when the application loads.

---

# 6. Protected Route

Protect:

```text
/history
```

Frontend flow:

When the user navigates to `/history`:

1. Call `GET /auth/me`.
2. If authenticated:

   * Render the page.
3. Otherwise:

   * Redirect to `/login`.

The frontend should never determine authentication on its own.

---

# 7. Backend Authentication

Every protected FastAPI endpoint must require authentication.

For every protected request:

1. Read the authentication cookie.
2. Validate the authenticated session.
3. Reject:

   * Missing session
   * Invalid session
   * Expired session

Return:

```text
401 Unauthorized
```

for any authentication failure.

---

# 8. Backend Authorization

After authentication succeeds:

Retrieve the authenticated user's email.

Verify that the email exists inside:

```text
admin_users
```

If it does not exist:

Return:

```text
403 Forbidden
```

Every protected endpoint must perform this authorization check before executing business logic.

---

# 9. Database Access

All database access must occur through FastAPI.

The frontend must never:

* Access Supabase directly.
* Query database tables.
* Authenticate directly with Supabase.
* Reset passwords directly.

FastAPI is solely responsible for communicating with Supabase.

RLS is already enabled and must continue to be enforced.

---

# 10. Logout

Create:

```text
POST /auth/logout
```

Backend:

* End the authenticated session.
* Clear the authentication cookie.

Frontend:

* Redirect the user to `/login`.

After logout, protected pages must no longer be accessible.

---

# 11. Complete Flow

1. User opens `/login`.
2. React sends credentials to `POST /auth/login`.
3. FastAPI authenticates with Supabase Auth.
4. FastAPI verifies the user's email exists in `admin_users`.
5. FastAPI creates the authenticated session.
6. FastAPI sets a secure HTTP-only cookie.
7. Browser stores the cookie.
8. User navigates to `/history`.
9. React calls `GET /auth/me`.
10. FastAPI validates the session.
11. FastAPI confirms the user exists in `admin_users`.
12. React loads the `/history` page.
13. Every protected API request automatically includes the authentication cookie.
14. FastAPI validates the session and authorization before executing any protected operation.
15. Logout clears the session and redirects to `/login`.

---

# Security Requirements

* No signup functionality.
* Password creation must occur through the password reset flow.
* FastAPI is the only component that communicates with Supabase.
* The frontend must never use the Supabase JavaScript client.
* Authentication state must be stored using secure HTTP-only cookies.
* No authentication tokens may be stored in localStorage or sessionStorage.
* Every protected endpoint must authenticate the request.
* Every protected endpoint must verify that the authenticated email exists in `admin_users`.
* `/history` must never be accessible without authentication.
* Invalid or expired sessions must return `401 Unauthorized`.
* Authenticated users not present in `admin_users` must receive `403 Forbidden`.
