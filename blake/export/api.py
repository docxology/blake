"""
REST API for Blake data access.
"""

from fastapi import FastAPI, HTTPException, Query, Path as PathParam, Request
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import logging
import json
from pathlib import Path


from ..models import BlakeWork, ExportConfig, SourceType
from ..exceptions import BlakeError
from ..provenance import manifest_context_for_work, work_provenance

logger = logging.getLogger(__name__)


class BlakeAPI:
    """REST API for Blake data access."""
    
    def __init__(self, blake_instance):
        """
        Initialize Blake API.
        
        Args:
            blake_instance: BlakeCorpus instance
        """
        self.blake = blake_instance
        self.data_dir = blake_instance.data_dir
        self.output_dir = getattr(blake_instance, "output_dir", None)
        self.app = FastAPI(
            title="Blake API",
            description="REST API for William Blake's works",
            version="0.1.0"
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(_request: Request, exc: HTTPException):
            return self._error_response(
                status_code=exc.status_code,
                code=self._error_code(exc.status_code),
                message=str(exc.detail),
            )
        
        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {"message": "Blake API", "version": "0.1.0"}
        
        @self.app.get("/works")
        async def get_works(
            limit: int = Query(10, ge=1, le=100),
            offset: int = Query(0, ge=0),
            work_type: Optional[str] = Query(None),
            source: Optional[str] = Query(None)
        ):
            """Get list of works."""
            try:
                works = await self.blake.get_all_works()
                
                # Apply filters
                if work_type:
                    works = [w for w in works if w.metadata.work_type == work_type]
                if source:
                    works = [w for w in works if w.metadata.source == source]
                
                # Apply pagination
                total = len(works)
                works = works[offset:offset + limit]
                
                return {
                    "works": [self._work_to_dict(w) for w in works],
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/works/{work_id}")
        async def get_work(work_id: str = PathParam(...)):
            """Get specific work by ID."""
            try:
                work = await self.blake.get_work(work_id)
                if not work:
                    raise HTTPException(status_code=404, detail="Work not found")
                
                return self._work_to_dict(work)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/works/{work_id}/analysis")
        async def get_work_analysis(work_id: str = PathParam(...)):
            """Get analysis results for a work."""
            try:
                work = await self.blake.get_work(work_id)
                if not work:
                    raise HTTPException(status_code=404, detail="Work not found")
                
                return {
                    "work_id": work_id,
                    "text_analysis": work.text_analysis,
                    "visual_analysis": work.visual_analysis,
                    "cross_analysis": work.cross_analysis
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/works/{work_id}/analyze")
        async def analyze_work(
            work_id: str = PathParam(...),
            analysis_types: Optional[List[str]] = Query(None)
        ):
            """Analyze a specific work."""
            try:
                work = await self.blake.get_work(work_id)
                if not work:
                    raise HTTPException(status_code=404, detail="Work not found")
                
                results = await self.blake.analyze_work(work_id, analysis_types)
                return {"work_id": work_id, "analysis": results}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/search")
        async def search_works(
            q: str = Query(..., description="Search query"),
            work_type: Optional[str] = Query(None),
            source: Optional[str] = Query(None),
            has_images: Optional[bool] = Query(None),
            has_text: Optional[bool] = Query(None),
            limit: int = Query(10, ge=1, le=100)
        ):
            """Search works."""
            try:
                filters = {}
                if work_type:
                    filters['work_type'] = work_type
                if source:
                    filters['source'] = source
                if has_images is not None:
                    filters['has_images'] = has_images
                if has_text is not None:
                    filters['has_text'] = has_text
                
                results = await self.blake.search_works(q, filters)
                results = results[:limit]
                
                return {
                    "query": q,
                    "results": [self._work_to_dict(w) for w in results],
                    "count": len(results)
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/statistics")
        async def get_statistics():
            """Get collection statistics."""
            try:
                stats = await self.blake.get_statistics()
                return stats
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/export/{work_id}")
        async def export_work(
            work_id: str = PathParam(...),
            format: str = Query("json", pattern="^(json|csv|pdf|html|markdown|md|parquet)$")
        ):
            """Export a specific work."""
            try:
                work = await self.blake.get_work(work_id)
                if not work:
                    raise HTTPException(status_code=404, detail="Work not found")
                
                output_dir = self.data_dir / "exports" / "api"
                output_dir.mkdir(parents=True, exist_ok=True)
                extension = "md" if format == "markdown" else format
                output_path = output_dir / f"blake_work_{work_id}.{extension}"
                output_path = await self.blake.exporter.export_work(work, output_path, format=format)
                
                # Return file
                return FileResponse(
                    path=output_path,
                    filename=f"blake_work_{work_id}.{format}",
                    media_type="application/octet-stream"
                )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy"}
    
    def _work_to_dict(self, work: BlakeWork) -> Dict[str, Any]:
        """Convert work to dictionary for API response."""
        return {
            "id": work.id,
            "title": work.metadata.title,
            "work_type": work.metadata.work_type,
            "creation_date": work.metadata.creation_date.isoformat() if work.metadata.creation_date else None,
            "source": work.metadata.source,
            "description": work.metadata.description,
            "has_text": work.text_content is not None,
            "has_images": len(work.images) > 0,
            "is_processed": work.fully_processed,
            "tags": work.metadata.tags,
            "themes": work.metadata.themes,
            "subjects": work.metadata.subjects,
            "provenance": work_provenance(work),
            "corpus_manifest": manifest_context_for_work(work, self._manifest_payload()),
        }

    def _manifest_payload(self) -> Dict[str, Any]:
        if not self.output_dir:
            return {}
        path = Path(self.output_dir) / "corpus_manifest.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _error_code(self, status_code: int) -> str:
        if status_code == 404:
            return "not_found"
        if status_code == 400:
            return "bad_request"
        if status_code == 422:
            return "validation_error"
        if status_code >= 500:
            return "internal_error"
        return "request_error"

    def _error_response(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {},
                }
            },
        )
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the API server."""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)
