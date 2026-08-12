from __future__ import annotations

from apps.members.models import Member


def mask_name(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) == 1:
        return "*"
    return f"{value[0]}*"


def mask_phone(value: str) -> str:
    value = (value or "").strip()
    if len(value) < 7:
        return ""
    return f"{value[:3]}****{value[-4:]}"


def member_brief(member: Member | None) -> dict:
    if member is None:
        return {"member_id": None, "member_name": "", "member_phone": ""}
    return {
        "member_id": member.id,
        "member_name": member.real_name or member.nickname,
        "member_phone": mask_phone(member.phone),
    }


def admin_member_brief(member: Member | None) -> dict:
    if member is None:
        return {"member_id": None, "member_name": "", "member_phone": ""}
    return {
        "member_id": member.id,
        "member_name": member.real_name or member.nickname,
        "member_phone": member.phone or "",
    }
