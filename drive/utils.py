import hashlib

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def gravatar_url(email: str) -> str:
    email_hash = sha256_hash(email.strip().lower())
    return f"https://www.gravatar.com/avatar/{email_hash}?s=200&d=identicon"
