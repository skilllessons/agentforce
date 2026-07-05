import  hashlib, secrets

from agentforge.core.db.repos import api_keys


def _hash(key:str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

async def issue_key(tenant_id, name=None) -> str:
    token = secrets.token_urlsafe(24)
    key = f"af_{tenant_id}_{token}"
    await api_keys.insert(tenant_id=tenant_id, key_hash=_hash(key), key_prefix=key[:12], name=name)
    return key


async def verify_key(key) -> str | None:
    return await api_keys.lookup_tenant_by_hash(_hash(key))