from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from starlette.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.folders.repositories import FolderRepository
from app.documents import schemas
from app.documents.services import DocumentService
from app.core.logging import get_logger
from app.ingestion.services import IngestionService

logger = get_logger(__name__)

router: APIRouter = APIRouter(prefix="/documents", tags=["documents"])


def _resolve_file_type(filename: str) -> schemas.DocumentTypeEnum:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix == "md":
        suffix = "markdown"
    try:
        return schemas.DocumentTypeEnum(suffix)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{suffix}'. Supported types are pdf, docx, pptx, markdown, txt, html.",
        ) from exc


@router.post("/", response_model=schemas.DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: schemas.DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.DocumentOut:
    profile_id = UUID(current_user.get("profile_id"))
    document = await DocumentService.create_document(db, payload, profile_id)
    return schemas.DocumentOut.model_validate(document)


@router.post("/upload", response_model=schemas.DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    folder_id: Optional[UUID] = Form(None),
    is_favorite: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.DocumentOut:
    profile_id = UUID(current_user.get("profile_id"))

    if file.filename is None or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a filename.",
        )

    file_type = _resolve_file_type(file.filename)

    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        ) from exc

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    resolved_folder_id = folder_id
    if resolved_folder_id is None:
        uploaded_folder = await FolderRepository.get_system_folder_by_type(
            db,
            profile_id,
            "uploaded",
        )
        if uploaded_folder is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default uploaded folder not found for the current user.",
            )
        resolved_folder_id = uploaded_folder.id

    safe_filename = Path(file.filename).name
    upload_subdir = Path(settings.uploads_dir) / str(profile_id)
    upload_subdir.mkdir(parents=True, exist_ok=True)
    disk_path = upload_subdir / safe_filename

    try:
        disk_path.write_bytes(file_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file to disk: {exc}",
        ) from exc

    storage_path = f"uploads/{profile_id}/{safe_filename}"
    doc_create = schemas.DocumentCreate(
        name=Path(safe_filename).stem,
        file_type=file_type,
        file_size=len(file_bytes),
        is_favorite=is_favorite,
        folder_id=resolved_folder_id,
        file_path=storage_path,
    )

    document = await DocumentService.create_document(db, doc_create, profile_id)

    try:
        await IngestionService().process_document(
            session=db,
            document_id=document.id,
            profile_id=profile_id,
            file_bytes=file_bytes,
            file_type=file_type.value,
            folder_id=document.folder_id,
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {exc}",
        ) from exc

    return schemas.DocumentOut.model_validate(document)


MEDIA_TYPE_MAP = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "markdown": "text/plain",
    "txt": "text/plain",
    "html": "text/html",
}


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Response:
    profile_id = UUID(current_user.get("profile_id"))
    document = await DocumentService.get_document(
        db, document_id, profile_id, include_deleted=False
    )

    relative_path = Path(document.file_path)
    if relative_path.parts and relative_path.parts[0] == "uploads":
        relative_path = Path(*relative_path.parts[1:])

    resolved_path = (Path(settings.uploads_dir) / relative_path).resolve()
    uploads_root = Path(settings.uploads_dir).resolve()

    try:
        resolved_path.relative_to(uploads_root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document file path.",
        )

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on disk.",
        )

    media_type = MEDIA_TYPE_MAP.get(
        document.file_type if isinstance(document.file_type, str) else document.file_type.value,
        "application/octet-stream",
    )

    return FileResponse(
        path=str(resolved_path),
        media_type=media_type,
        filename=document.name or resolved_path.name,
    )


@router.get("/", response_model=List[schemas.DocumentOut])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
    folder_id: Optional[UUID] = Query(None),
    is_favorite: Optional[bool] = Query(None),
    is_deleted: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> List[schemas.DocumentOut]:
    profile_id = UUID(current_user.get("profile_id"))
    documents = await DocumentService.list_user_documents(
        db, profile_id, folder_id=folder_id, is_favorite=is_favorite, is_deleted=is_deleted, skip=skip, limit=limit
    )
    return [schemas.DocumentOut.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=schemas.DocumentOut)
async def get_document(
    document_id: UUID,
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.DocumentOut:
    profile_id = UUID(current_user.get("profile_id"))
    document = await DocumentService.get_document(db, document_id, profile_id, include_deleted=include_deleted)
    return schemas.DocumentOut.model_validate(document)


@router.patch("/{document_id}", response_model=schemas.DocumentOut)
async def patch_document(
    document_id: UUID,
    payload: schemas.DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.DocumentOut:
    profile_id = UUID(current_user.get("profile_id"))
    updated = await DocumentService.update_document(db, document_id, payload, profile_id)
    return schemas.DocumentOut.model_validate(updated)


@router.post("/{document_id}/soft-delete", response_model=schemas.DocumentOut)
async def soft_delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.DocumentOut:
    profile_id = UUID(current_user.get("profile_id"))
    updated = await DocumentService.soft_delete_document(db, document_id, profile_id)
    return schemas.DocumentOut.model_validate(updated)


@router.post("/{document_id}/restore", response_model=schemas.DocumentOut)
async def restore_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.DocumentOut:
    profile_id = UUID(current_user.get("profile_id"))
    updated = await DocumentService.restore_document(db, document_id, profile_id)
    return schemas.DocumentOut.model_validate(updated)


@router.delete(
    "/{document_id}",
    response_class=Response,
)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> None:
    profile_id = UUID(current_user.get("profile_id"))
    await DocumentService.permanently_delete_document(db, document_id, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
