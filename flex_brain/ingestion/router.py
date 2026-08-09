from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, status

from flex_brain.ingestion.dependencies import IngestionServiceDep
from flex_brain.ingestion.models import IngestionRequest, IngestionResponse
from flex_brain.ingestion.pdf import InvalidPdfError, PdfTooLongError
from flex_brain.ingestion.service import (
    DEFAULT_EMBEDDING_MODEL,
    EmptyContentError,
    UnsupportedMimetypeError,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("")
async def ingest(
    request: Annotated[IngestionRequest, Form()], ingestion_service: IngestionServiceDep
) -> IngestionResponse:
    file = request.file
    model = request.model

    if model is None:
        model = DEFAULT_EMBEDDING_MODEL

    content = await file.read()

    try:
        result = await ingestion_service.ingest(
            content,
            filename=file.filename,
            declared_type=file.content_type,
            model=model,
            space_id=request.space_id,
        )
    except UnsupportedMimetypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except EmptyContentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except InvalidPdfError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except PdfTooLongError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
        ) from exc

    return IngestionResponse(
        document_id=result.document_id,
        model=model,
        filename=file.filename,
        mimetype=result.mimetype,
        chunks=result.chunks,
        space_id=result.space_id,
    )
