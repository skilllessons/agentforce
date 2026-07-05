from fastapi import Header, HTTPException

from agentforge.core.auth.keys import verify_key


async def require_tenant(authorization: str = Header(...)) -> str:
    # header looks like:  Authorization: Bearer af_acme_xxxx
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing or malformed Authorization header")
    tenant_id = await verify_key(token)
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="invalid API key")
    return tenant_id