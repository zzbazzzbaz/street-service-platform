from django.shortcuts import get_object_or_404
from ninja import Router

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.activities.schemas import ActivitiesData, ActivityCheckinIn, ActivityCheckinOut, ActivityOut, ActivitySignupCancelOut, ActivitySignupOut, ActivitySignupsData
from apps.activities.services import activity_data, cancel_signup, checkin_activity, checkin_data, signup_activity, signup_data
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import paginate_queryset
from shared.services import authenticate_member


router = Router(tags=["活动"])


@router.get("", response={200: SuccessResponse[ActivitiesData], 401: ErrorResponse, 403: ErrorResponse})
def activity_list(request, page: int = 1, page_size: int = 20):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    items, page_data = paginate_queryset(Activity.objects.filter(status=Activity.Status.PUBLISHED), page=page, page_size=page_size)
    activity_ids = [item.id for item in items]
    signups = {
        signup.activity_id: signup
        for signup in ActivitySignup.objects.filter(member=member, activity_id__in=activity_ids)
    }
    checkins = {
        checkin.activity_id: checkin
        for checkin in ActivityCheckin.objects.filter(member=member, activity_id__in=activity_ids)
    }
    for item in items:
        item._member_signup = signups.get(item.id)
        item._member_checkin = checkins.get(item.id)
    return success_response({"items": [activity_data(item, member=member) for item in items], **page_data})


@router.get("/my-signups", response={200: SuccessResponse[ActivitySignupsData], 401: ErrorResponse, 403: ErrorResponse})
def my_activity_signups(request, page: int = 1, page_size: int = 20):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    queryset = member.activity_signups.select_related("activity", "member")
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    checkins = {
        checkin.activity_id: checkin
        for checkin in ActivityCheckin.objects.filter(member=member, activity_id__in=[item.activity_id for item in items])
    }
    for item in items:
        item._member_checkin = checkins.get(item.activity_id)
    return success_response({"items": [signup_data(item) for item in items], **page_data})


@router.get("/{activity_id}", response={200: SuccessResponse[ActivityOut], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def activity_detail(request, activity_id: int):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    activity = get_object_or_404(Activity, pk=activity_id, status=Activity.Status.PUBLISHED)
    return success_response(activity_data(activity, member=member))


@router.post("/{activity_id}/signup", response={200: SuccessResponse[ActivitySignupOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def activity_signup(request, activity_id: int):
    try:
        member = authenticate_member(request)
        activity = get_object_or_404(Activity, pk=activity_id)
        signup = signup_activity(member, activity)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(signup_data(signup))


@router.delete("/{activity_id}/signup", response={200: SuccessResponse[ActivitySignupCancelOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def activity_cancel_signup(request, activity_id: int):
    try:
        member = authenticate_member(request)
        activity = get_object_or_404(Activity, pk=activity_id)
        data = cancel_signup(member, activity)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(data)


@router.post("/{activity_id}/checkin", response={200: SuccessResponse[ActivityCheckinOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def activity_checkin(request, activity_id: int, payload: ActivityCheckinIn):
    try:
        member = authenticate_member(request)
        activity = get_object_or_404(Activity, pk=activity_id)
        checkin = checkin_activity(member, activity, checkin_code=payload.checkin_code)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(checkin_data(checkin))
