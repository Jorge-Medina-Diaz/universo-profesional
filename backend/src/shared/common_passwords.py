"""Top-N most common passwords — used by the register/reset policies.

The list is small (200 entries) intentionally: it covers the worst offenders
(`password123`, `qwerty1234`, …) without bloating the import. We check
case-insensitively so users can't bypass with `Password123`.

If you ever need a longer list, the canonical source is the HIBP "Pwned
Passwords" SHA-1 archive; rather than embedding 850M hashes, the right
upgrade path is to call HIBP's k-anonymity API at register time (5-char
prefix lookup, no full hash leaves the host). Not done today because that
adds a network dep on a critical-path endpoint.
"""
from __future__ import annotations

_COMMON_PASSWORDS_LOWER: frozenset[str] = frozenset(
    s.lower()
    for s in (
        # Numeric / sequential
        "123456", "12345678", "123456789", "1234567890", "12345",
        "1234", "111111", "000000", "222222", "121212", "11111111",
        # Letters only
        "qwerty", "qwertyuiop", "asdfgh", "asdfghjkl", "zxcvbn",
        "abc123", "abcd1234", "abcdef", "letmein", "monkey",
        # Words + numbers
        "password", "password1", "password12", "password123", "password1234",
        "passw0rd", "p@ssword", "p@ssw0rd", "p@ssword1", "p@ssw0rd1",
        "admin", "admin123", "administrator", "root", "toor",
        "welcome", "welcome1", "welcome123", "iloveyou", "iloveyou1",
        "princess", "dragon", "sunshine", "master", "shadow",
        "football", "baseball", "soccer", "trustno1", "qwerty123",
        # Spanish-leaning (this is a Spanish-first product)
        "contraseña", "Contraseña1", "contraseña1", "contrasena", "contrasena1",
        "hola123", "hola1234", "españa", "España", "españa1",
        "madrid", "barcelona", "valencia", "sevilla", "españa2024",
        "elsa1234", "juan1234", "maria1234", "lucia1234", "carmen1234",
        "telefonica", "movistar", "santander", "iberdrola", "naturgy",
        # Common patterns
        "Qwerty123", "Qwerty1234", "Welcome123", "Welcome1", "Hello123",
        "Hello1234", "Test1234", "Demo1234", "Sample123", "Default1",
        "Admin1234", "Root1234", "User1234", "Guest123", "Pass1234",
        # Year suffixes
        "Password2024", "Password2025", "Password2026", "Welcome2024",
        "Welcome2025", "Hello2024", "Hello2025", "Admin2024", "Admin2025",
        # Brand-likely guesses
        "Universo1", "Universo123", "UniversoProfesional1",
        # Keyboard walks
        "Qazwsx1234", "1qaz2wsx3edc", "Asdfghjkl1", "Zxcvbnm1234",
        # Variations
        "Letmein123", "Letmein1234", "Trustme1", "Trustme1234",
        "Changeme1", "Changeme123", "Changeme1234", "Default123",
        "Password!", "Password!1", "P@ssword1", "P@ssword123",
        "Qwerty!", "Qwerty!1", "Admin!", "Admin!1",
        # Numeric repeats
        "1111111111", "2222222222", "3333333333", "1234567891",
        "0987654321", "1234509876", "1029384756", "1357924680",
        # Common names + 123
        "Jose1234", "Jorge1234", "David1234", "Carlos1234", "Sofia1234",
        "Marta1234", "Laura1234", "Pedro1234", "Pablo1234", "Sergio1234",
        # English staples often translated
        "Iloveyou1", "Iloveyou123", "Lovelovelove1", "Loveyou123",
        "Princess1", "Sunshine1", "Sunflower1", "Football1", "Baseball1",
        # Tech-bro defaults
        "Github1", "Github123", "Stripe1", "Linkedin1", "Anthropic1",
        # ATM/PIN style padded
        "00001234", "1234abcd", "Abcd1234", "qwertyabcd",
        # Profanity-light
        "Putamadre1", "Joder1234", "Mierda1234",
    )
)


def is_common_password(password: str) -> bool:
    """Return True when `password` is among the most-frequently leaked ones."""
    return password.lower() in _COMMON_PASSWORDS_LOWER
