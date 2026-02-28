"""
JWS Signing Adapter — Aarohan++ Phase 5
Signs NHCX FHIR Bundles using JWS (JSON Web Signature) compact serialization.

NHCX Specification:
  - Algorithm: RS256 (RSA + SHA-256) — required by NHA/NHCX spec
  - For demo/hackathon: uses an auto-generated RSA keypair (2048-bit)
  - In production: replace with NHCX-issued certificate from NHA

Workflow:
  1. Serialize the FHIR bundle to canonical JSON
  2. Create JWS header: {"alg": "RS256", "typ": "JWT", "kid": <key_id>}
  3. Payload = base64url(bundle_json)
  4. Sign header.payload with private key
  5. Return complete JWS compact string + metadata

References:
  https://nrces.in/nhcx/specification
  RFC 7515 — JSON Web Signature
"""

import json
import base64
import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Try to import cryptography lib ───────────────────────────────────────────
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    logger.warning("cryptography package not installed — JWS will use DEMO-MODE (unsigned)")


@dataclass
class JWSResult:
    """Result of signing a bundle."""
    token: str                      # Full JWS compact serialization (or demo stub)
    algorithm: str
    key_id: str
    bundle_digest: str              # SHA-256 hex of the bundle JSON
    signed_at: str
    demo_mode: bool = False         # True if cryptography lib not available


@dataclass
class KeyPair:
    private_pem: bytes
    public_pem: bytes
    key_id: str


# ── Singleton demo keypair (generated once per process) ────────────────────

_demo_keypair: Optional[KeyPair] = None


def _generate_demo_keypair() -> KeyPair:
    global _demo_keypair
    if _demo_keypair is not None:
        return _demo_keypair
    if not _CRYPTO_AVAILABLE:
        return KeyPair(b"", b"", "demo-unsigned")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    kid = "aarohan-demo-" + hashlib.sha256(public_pem).hexdigest()[:12]
    _demo_keypair = KeyPair(private_pem, public_pem, kid)
    logger.info(f"JWS: Generated demo RSA-2048 keypair (kid={kid})")
    return _demo_keypair


def _b64url(data: bytes) -> str:
    """Base64url encoding without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def sign_bundle(bundle: dict, key_pair: Optional[KeyPair] = None) -> JWSResult:
    """
    Sign a FHIR bundle dict and return a JWSResult.

    Args:
        bundle: The FHIR bundle dict to sign
        key_pair: Optional custom keypair. Defaults to auto-generated demo key.

    Returns:
        JWSResult with the signed JWS compact token
    """
    kp = key_pair or _generate_demo_keypair()
    bundle_json = json.dumps(bundle, separators=(",", ":"), ensure_ascii=False)
    bundle_bytes = bundle_json.encode("utf-8")
    digest = hashlib.sha256(bundle_bytes).hexdigest()
    signed_at = datetime.now(timezone.utc).isoformat()

    if not _CRYPTO_AVAILABLE or not kp.private_pem:
        # Demo mode — unsigned token (still shows correct format)
        header = {"alg": "RS256", "typ": "JWT", "kid": kp.key_id, "demo": True}
        header_b64 = _b64url(json.dumps(header).encode())
        payload_b64 = _b64url(bundle_bytes)
        token = f"{header_b64}.{payload_b64}.DEMO_SIGNATURE_NOT_VALID"
        return JWSResult(
            token=token,
            algorithm="RS256",
            key_id=kp.key_id,
            bundle_digest=digest,
            signed_at=signed_at,
            demo_mode=True,
        )

    # Real signing with RS256
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    private_key = load_pem_private_key(kp.private_pem, password=None, backend=default_backend())

    header = {"alg": "RS256", "typ": "JWT", "kid": kp.key_id}
    header_b64 = _b64url(json.dumps(header).encode())
    payload_b64 = _b64url(bundle_bytes)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = _b64url(signature)

    token = f"{header_b64}.{payload_b64}.{sig_b64}"
    return JWSResult(
        token=token,
        algorithm="RS256",
        key_id=kp.key_id,
        bundle_digest=digest,
        signed_at=signed_at,
        demo_mode=False,
    )


def get_public_key_pem() -> str:
    """Return the current demo public key PEM (for verification by validators)."""
    kp = _generate_demo_keypair()
    return kp.public_pem.decode("utf-8") if kp.public_pem else "DEMO_MODE_NO_KEY"
