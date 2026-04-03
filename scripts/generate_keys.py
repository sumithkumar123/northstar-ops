"""
Generate RSA-2048 keypair for RS256 JWT signing.
Writes private.pem and public.pem to /keys/ (or the path in KEY_DIR env var).
Run once before starting services; keys directory is mounted as a read-only volume.
"""
import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KEY_DIR = Path(os.environ.get("KEY_DIR", "/keys"))
KEY_DIR.mkdir(parents=True, exist_ok=True)

private_path = KEY_DIR / "private.pem"
public_path = KEY_DIR / "public.pem"

if private_path.exists() and public_path.exists():
    print("Keys already exist, skipping generation.")
else:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"Generated RSA-2048 keypair at {KEY_DIR}")
