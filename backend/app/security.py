import os
import requests


def verify_recaptcha(token: str) -> bool:
    """Verify a reCAPTCHA token with Google's API.

    If the ``DISABLE_CAPTCHA`` environment variable is set to a truthy
    value, the check is bypassed and ``True`` is returned. This makes it
    easy to temporarily disable captcha validation for local development or
    troubleshooting without modifying the calling code.
    """

    if os.getenv("DISABLE_CAPTCHA", "").lower() in {"1", "true", "yes"}:
        return True

    secret = os.getenv("RECAPTCHA_SECRET", "6Lcu13grAAAAAHhpUM7ba7SLORGjd_XNYnta1WGJ")
    if not secret:
        return False
    try:
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": secret, "response": token},
            timeout=5,
        )
        data = resp.json()
        return data.get("success", False)
    except Exception:
        return False
