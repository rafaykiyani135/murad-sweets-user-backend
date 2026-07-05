"""
Authentication endpoints for the admin dashboard.

Uses the local admin_users table with bcrypt password verification.
Sessions are managed via secure HTTP-only cookies containing JWTs.
Password reset emails are sent through the Resend API.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.db.session import get_db
from app.models.admin_user import AdminUser
from app.core import security
from app.core.config import settings
from app.core.security import AUTH_COOKIE_NAME

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class UpdatePasswordRequest(BaseModel):
    token: str
    new_password: str

class AuthMeResponse(BaseModel):
    email: str
    username: str


# ─── Cookie Helpers ──────────────────────────────────────────────────────────

def _set_auth_cookie(response: Response, token: str) -> None:
    """Set a secure HTTP-only session cookie."""
    is_production = settings.APP_ENV == "production"
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_production,         # HTTPS only in production
        samesite="none" if is_production else "lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

def _clear_auth_cookie(response: Response) -> None:
    """Remove the session cookie."""
    is_production = settings.APP_ENV == "production"
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        path="/",
    )


# ─── Shared Dependency ──────────────────────────────────────────────────────

async def get_current_admin_from_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """
    FastAPI dependency that reads the JWT from the HTTP-only cookie,
    validates it, and confirms the user exists in admin_users.
    """
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    result = await db.execute(select(AdminUser).where(AdminUser.email == email))
    admin = result.scalar_one_or_none()

    if admin is None or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return admin


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/login")
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Authenticate admin credentials and set an HTTP-only session cookie.
    Login is by email + password against the admin_users table.
    """
    result = await db.execute(select(AdminUser).where(AdminUser.email == payload.email))
    admin = result.scalar_one_or_none()

    if not admin or not security.verify_password(payload.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Create JWT with email as subject (matches admin_users lookup)
    access_token = security.create_access_token(subject=admin.email)
    _set_auth_cookie(response, access_token)

    return {"success": True, "email": admin.email}


@router.get("/me", response_model=AuthMeResponse)
async def auth_me(admin: AdminUser = Depends(get_current_admin_from_cookie)):
    """
    Check if the current session is authenticated.
    Returns 401 if not authenticated.
    """
    return AuthMeResponse(email=admin.email, username=admin.username)


@router.post("/logout")
async def logout(response: Response):
    """Clear the session cookie and log out."""
    _clear_auth_cookie(response)
    return {"success": True}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Send a password reset email if the address belongs to an admin.
    Always returns a generic success response to prevent email enumeration.
    """
    result = await db.execute(select(AdminUser).where(AdminUser.email == payload.email))
    admin = result.scalar_one_or_none()

    if admin and admin.is_active:
        reset_token = security.create_password_reset_token(admin.email)
        reset_link = f"{settings.FRONTEND_ORIGIN}/reset-password?token={reset_token}"

        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": settings.EMAIL_FROM,
                "to": [admin.email],
                "subject": "Murad Sweets — Password Reset",
                "html": f"""
                <div style="font-family: 'Lato', sans-serif; max-width: 500px; margin: 0 auto; padding: 40px 20px;">
                    <h2 style="color: #4A0F17; font-family: serif;">Murad Sweets</h2>
                    <p style="color: #8A5A2B;">You requested a password reset for your admin account.</p>
                    <p style="color: #8A5A2B;">Click the button below to set a new password. This link expires in 30 minutes.</p>
                    <a href="{reset_link}" style="display: inline-block; margin: 24px 0; padding: 14px 32px; background: #7B1E2B; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600;">
                        Reset Password
                    </a>
                    <p style="color: #8A5A2B; font-size: 13px;">If you did not request this, you can safely ignore this email.</p>
                </div>
                """,
            })
        except Exception:
            # Log but don't expose email delivery failures
            pass

    # Always return success to prevent email enumeration
    return {"success": True, "message": "If that email is registered, a reset link has been sent."}


@router.post("/update-password")
async def update_password(payload: UpdatePasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Set a new password using a valid reset token.
    """
    email = security.verify_password_reset_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link. Please request a new one.",
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )

    result = await db.execute(select(AdminUser).where(AdminUser.email == email))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    admin.hashed_password = security.get_password_hash(payload.new_password)
    await db.commit()

    return {"success": True, "message": "Password updated successfully. You can now log in."}
