from dataclasses import dataclass
import ipaddress

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import Tenant


settings = get_settings()


@dataclass
class TenantContext:
    tenant: Tenant | None
    source: str


def _extract_hostname(host: str) -> str:
    return host.split(":")[0].strip().lower()


def _is_ip_address(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def resolve_tenant_code(request: Request) -> TenantContext:
    host = request.headers.get("host", "")
    hostname = _extract_hostname(host)
    if hostname and "." in hostname and not _is_ip_address(hostname):
        subdomain = hostname.split(".")[0]
        if subdomain not in {"localhost", "127", "api"}:
            return TenantContext(tenant=None, source=subdomain)
    if settings.allow_tenant_header_fallback:
        header_value = request.headers.get(settings.tenant_header_name)
        if header_value:
            return TenantContext(tenant=None, source=header_value.lower())
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant context is required")


def get_current_tenant(request: Request, db: Session) -> Tenant:
    tenant_code = resolve_tenant_code(request).source
    tenant = db.scalar(select(Tenant).where(Tenant.code == tenant_code))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant
