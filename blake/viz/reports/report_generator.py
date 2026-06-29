"""
Report Generator

Automated report generation for research, educational, and public use cases.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import Report, ReportTemplate, ReportSection, ReportType

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates automated reports."""
    
    def __init__(self):
        """Initialize report generator."""
        self.templates = self._create_templates()
        logger.info("Initialized ReportGenerator")

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _work_title(work: Any) -> str:
        if isinstance(work, dict):
            metadata = work.get("metadata")
            if isinstance(metadata, dict):
                title = metadata.get("title")
                if title:
                    return str(title)
            title = work.get("title") or work.get("id")
            return str(title or "Untitled work")

        metadata = getattr(work, "metadata", None)
        if metadata is not None:
            title = getattr(metadata, "title", None)
            if title:
                return str(title)
        title = getattr(work, "title", None)
        if title:
            return str(title)
        return str(getattr(work, "id", "Untitled work"))

    @staticmethod
    def _work_source(work: Any) -> str:
        if isinstance(work, dict):
            metadata = work.get("metadata")
            if isinstance(metadata, dict):
                source = metadata.get("source")
                if source:
                    return str(source)
            source = work.get("source")
            if source:
                return str(source)
            return "unknown"

        metadata = getattr(work, "metadata", None)
        if metadata is not None:
            source = getattr(metadata, "source", None)
            if source:
                return str(source)
        source = getattr(work, "source", None)
        if source:
            return str(source)
        return "unknown"

    @staticmethod
    def _work_image_count(work: Any) -> int:
        if isinstance(work, dict):
            return len(work.get("images") or [])
        images = getattr(work, "images", None)
        return len(images or [])

    @staticmethod
    def _work_has_text(work: Any) -> bool:
        if isinstance(work, dict):
            return bool(work.get("text_content"))
        return bool(getattr(work, "text_content", None))

    @staticmethod
    def _summarize_counts(counts: Dict[str, Any], *, empty_label: str) -> str:
        rows: List[tuple[str, int]] = []
        for key, value in counts.items():
            count = ReportGenerator._coerce_int(value)
            if count > 0:
                rows.append((str(key), count))
        if not rows:
            return empty_label
        rows.sort(key=lambda item: (-item[1], item[0]))
        return ", ".join(f"{name} ({count})" for name, count in rows[:3])

    @staticmethod
    def _format_date_range(date_range: Dict[str, Any]) -> str:
        earliest = date_range.get("earliest")
        latest = date_range.get("latest")
        if earliest and latest:
            if earliest == latest:
                return str(earliest)
            return f"{earliest} to {latest}"
        if earliest:
            return f"from {earliest}"
        if latest:
            return f"through {latest}"
        return "not yet established"

    def _build_public_gallery(self, works: List[Any]) -> List[Dict[str, Any]]:
        gallery: List[Dict[str, Any]] = []
        for work in sorted(works, key=self._work_title)[:3]:
            work_id = "unknown"
            if isinstance(work, dict):
                work_id = str(work.get("id") or "unknown")
            else:
                work_id = str(getattr(work, "id", "unknown"))
            gallery.append(
                {
                    "id": work_id,
                    "title": self._work_title(work),
                    "source": self._work_source(work),
                    "image_count": self._work_image_count(work),
                    "has_text": self._work_has_text(work),
                }
            )
        return gallery

    def _build_public_report_content(
        self,
        summary: Optional[Dict[str, Any]] = None,
        works: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        summary = summary or {}
        works = works or []

        total_works = self._coerce_int(summary.get("total_works"), len(works))
        total_images = self._coerce_int(
            summary.get("total_images"),
            sum(self._work_image_count(work) for work in works),
        )
        processed_works = self._coerce_int(summary.get("processed_works"))
        source_summary = self._summarize_counts(
            summary.get("sources") or {}, empty_label="no source breakdown available"
        )
        work_type_summary = self._summarize_counts(
            summary.get("work_types") or {}, empty_label="no work-type breakdown available"
        )
        date_range_text = self._format_date_range(summary.get("date_range") or {})
        coverage_status = str(summary.get("coverage_status") or "not reported")
        gallery = self._build_public_gallery(works)

        highlights = [
            f"Local corpus snapshot: {total_works} works and {total_images} images.",
            f"Coverage status: {coverage_status}.",
        ]
        if processed_works:
            highlights.append(f"{processed_works} works are marked processed.")
        if source_summary != "no source breakdown available":
            highlights.append(f"Source mix: {source_summary}.")
        if work_type_summary != "no work-type breakdown available":
            highlights.append(f"Work types: {work_type_summary}.")
        if date_range_text != "not yet established":
            highlights.append(f"Date range: {date_range_text}.")

        return {
            "summary": {
                "total_works": total_works,
                "total_images": total_images,
                "processed_works": processed_works,
                "source_count": len(summary.get("sources") or {}),
                "coverage_status": coverage_status,
                "date_range": date_range_text,
            },
            "highlights": highlights,
            "visual_gallery": gallery,
            "stories": [
                "The public report is limited to code, documentation, checksums, and aggregate corpus context.",
                "Rights-gated assets stay excluded from public release until the source terms allow redistribution.",
                "The same local corpus can be explored through the CLI, dashboard, and release-preflight outputs.",
            ],
        }
    
    def _create_templates(self) -> Dict[str, ReportTemplate]:
        """Create report templates."""
        return {
            "research_comprehensive": ReportTemplate(
                id="research_comprehensive",
                name="Comprehensive Research Report",
                description="Corpus summary for research review, analysis status, and release context",
                report_type=ReportType.RESEARCH,
                sections=[
                    ReportSection(
                        id="executive_summary",
                        title="Executive Summary",
                        content_type="text",
                        content={
                            "text": "Populated at generation time with corpus coverage and analysis status."
                        }
                    ),
                    ReportSection(
                        id="methodology",
                        title="Methodology",
                        content_type="text",
                        content={
                            "text": "Populated at generation time with acquisition, analysis, and release methods."
                        }
                    ),
                    ReportSection(
                        id="findings",
                        title="Key Findings",
                        content_type="analysis",
                        content={
                            "analysis": "Populated at generation time with corpus findings and coverage notes."
                        }
                    ),
                    ReportSection(
                        id="visualizations",
                        title="Visualizations",
                        content_type="visualization",
                        content={"visualizations": []}
                    ),
                    ReportSection(
                        id="conclusions",
                        title="Conclusions",
                        content_type="text",
                        content={
                            "text": "Populated at generation time with release-ready conclusions."
                        }
                    ),
                    ReportSection(
                        id="references",
                        title="References",
                        content_type="text",
                        content={
                            "text": "Populated at generation time with corpus manifest and references."
                        }
                    )
                ]
            ),
            "educational_beginner": ReportTemplate(
                id="educational_beginner",
                name="Beginner Educational Report",
                description="Introductory guide to Blake for learners and general audiences",
                report_type=ReportType.EDUCATIONAL,
                sections=[
                    ReportSection(
                        id="introduction",
                        title="Introduction to Blake",
                        content_type="text",
                        content={
                            "text": "Populated at generation time with corpus and learning context."
                        }
                    ),
                    ReportSection(
                        id="key_works",
                        title="Key Works",
                        content_type="works",
                        content={"works": []}
                    ),
                    ReportSection(
                        id="themes",
                        title="Main Themes",
                        content_type="themes",
                        content={"themes": []}
                    ),
                    ReportSection(
                        id="activities",
                        title="Learning Activities",
                        content_type="activities",
                        content={"activities": []}
                    )
                ]
            ),
            "public_engagement": ReportTemplate(
                id="public_engagement",
                name="Public Corpus Snapshot",
                description="Public-facing snapshot of the locally available Blake corpus",
                report_type=ReportType.PUBLIC,
                sections=[
                    ReportSection(
                        id="highlights",
                        title="Highlights",
                        content_type="highlights",
                        content={
                            "highlights": [
                                "Populated at generation time with corpus coverage notes."
                            ]
                        }
                    ),
                    ReportSection(
                        id="visual_gallery",
                        title="Visual Gallery",
                        content_type="gallery",
                        content={"gallery": []}
                    ),
                    ReportSection(
                        id="stories",
                        title="Stories",
                        content_type="stories",
                        content={
                            "stories": [
                                "Populated at generation time with release and exploration context."
                            ]
                        }
                    )
                ]
            )
        }
    
    async def generate_research_report(self, focus: str = "comprehensive") -> Report:
        """Generate research report."""
        logger.info(f"Generating research report with focus: {focus}")
        
        template = self.templates.get("research_comprehensive")
        if not template:
            raise ValueError("Research template not found")
        
        # Generate report content
        content = {
            "executive_summary": "This report summarizes the local Blake corpus, its coverage, and the analysis outputs available for review.",
            "methodology": "Analysis combines normalized acquisition, metadata storage, text analysis, image analysis, visualization, export, and release-preflight reporting.",
            "findings": "Current outputs emphasize provenance, coverage status, and the separation between public bundle material and rights-gated local assets.",
            "visualizations": ["word_cloud", "timeline", "network_analysis"],
            "conclusions": "The local corpus is ready for research use, while redistribution still follows the documented rights and release checklist.",
            "references": "Corpus manifest, source audit, rights gate report, and manuscript references."
        }
        
        return Report(
            id=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title="Comprehensive Research Report",
            template=template,
            content=content,
            generated_at=datetime.now(),
            generated_by="Blake Report Generator"
        )
    
    async def generate_educational_report(self, level: str = "intermediate") -> Report:
        """Generate educational report."""
        logger.info(f"Generating educational report for level: {level}")
        
        template = self.templates.get("educational_beginner")
        if not template:
            raise ValueError("Educational template not found")
        
        # Generate report content
        content = {
            "introduction": "William Blake is introduced here through the local corpus and the workflow that organizes texts, images, and metadata.",
            "key_works": ["Songs of Innocence", "Songs of Experience", "The Tyger"],
            "themes": ["innocence vs experience", "imagination", "social criticism"],
            "activities": ["timeline exploration", "theme analysis", "visual comparison"]
        }
        
        return Report(
            id=f"educational_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Educational Report - {level.title()} Level",
            template=template,
            content=content,
            generated_at=datetime.now(),
            generated_by="Blake Report Generator"
        )
    
    async def generate_public_report(
        self,
        summary: Optional[Dict[str, Any]] = None,
        works: Optional[List[Any]] = None,
    ) -> Report:
        """Generate public engagement report."""
        logger.info("Generating public engagement report")
        
        template = self.templates.get("public_engagement")
        if not template:
            raise ValueError("Public engagement template not found")
        
        # Generate report content
        content = self._build_public_report_content(summary=summary, works=works)
        
        return Report(
            id=f"public_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title="Public Corpus Snapshot",
            template=template,
            content=content,
            generated_at=datetime.now(),
            generated_by="Blake Report Generator"
        )
    
    async def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available report templates."""
        return [
            {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "section_count": len(template.sections)
            }
            for template in self.templates.values()
        ]
    
    async def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """Get specific report template."""
        return self.templates.get(template_id)
