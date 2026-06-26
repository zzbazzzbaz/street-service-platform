from ninja import Form, Router

from apps.core.schemas import UploadedImagesData
from apps.core.services import save_uploaded_images
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError, get_token_identity
from shared.exceptions import BusinessError
from shared.services import authenticate_member, authenticate_merchant


router = Router(tags=["上传"])


def authenticate_upload_subject(request):
    identity = get_token_identity(request)
    if identity.subject_type == "member":
        return authenticate_member(request)
    if identity.subject_type == "merchant":
        return authenticate_merchant(request)
    raise TokenError("token 主体类型错误")


@router.post("/images", response={200: SuccessResponse[UploadedImagesData], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def upload_images(
    request,
    business_type: str = Form("general"),
    related_id: str = Form(""),
):
    try:
        authenticate_upload_subject(request)
        files = request.FILES.getlist("files")
        data = save_uploaded_images(request, files, business_type=business_type, related_id=related_id)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(data)
