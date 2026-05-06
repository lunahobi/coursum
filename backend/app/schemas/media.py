from pydantic import BaseModel


class MediaAssetRead(BaseModel):
    path: str
    label: str
    kind: str
    size_bytes: int
    filename: str
    mime_type: str
