"""
Export format implementations.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ..models import BlakeWork, ExportConfig
from ..exceptions import ExportError
from ..provenance import work_provenance

logger = logging.getLogger(__name__)


class BaseExporter:
    """Base class for export format implementations."""
    
    def __init__(self):
        """Initialize exporter."""
        pass
    
    async def export_works(self, works: List[BlakeWork], output_dir: Path,
                          config: ExportConfig) -> Path:
        """Export works to file."""
        raise NotImplementedError
    
    async def export_work(self, work: BlakeWork, output_path: Path) -> Path:
        """Export single work to file."""
        raise NotImplementedError
    
    async def export_analysis_results(self, works: List[BlakeWork],
                                    output_path: Path) -> Path:
        """Export analysis results to file."""
        raise NotImplementedError


class JSONExporter(BaseExporter):
    """JSON format exporter."""
    
    async def export_works(self, works: List[BlakeWork], output_dir: Path,
                          config: ExportConfig) -> Path:
        """Export works to JSON file."""
        output_file = output_dir / f"blake_works.{self._get_extension()}"
        
        export_data = []
        for work in works:
            work_data = self._work_to_dict(work, config)
            export_data.append(work_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Exported {len(works)} works to {output_file}")
        return output_file
    
    async def export_work(self, work: BlakeWork, output_path: Path) -> Path:
        """Export single work to JSON file."""
        work_data = self._work_to_dict(work, ExportConfig(
            output_dir=output_path.parent,
            include_images=True,
            include_metadata=True,
            include_analysis=True
        ))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(work_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Exported work {work.id} to {output_path}")
        return output_path
    
    async def export_analysis_results(self, works: List[BlakeWork],
                                    output_path: Path) -> Path:
        """Export analysis results to JSON file."""
        analysis_data = []
        
        for work in works:
            work_analysis = {
                'work_id': work.id,
                'title': work.metadata.title,
                'text_analysis': work.text_analysis,
                'visual_analysis': work.visual_analysis,
                'cross_analysis': work.cross_analysis,
            }
            analysis_data.append(work_analysis)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Exported analysis results to {output_path}")
        return output_path
    
    def _work_to_dict(self, work: BlakeWork, config: ExportConfig) -> Dict[str, Any]:
        """Convert work to dictionary for export."""
        work_data = {
            'id': work.id,
            'metadata': work.metadata.model_dump(mode="json") if config.include_metadata else None,
            'provenance': work_provenance(work),
        }
        
        if config.include_metadata:
            work_data['text_content'] = work.text_content
            work_data['images'] = [img.model_dump(mode="json") for img in work.images]
        
        if config.include_analysis:
            work_data['text_analysis'] = work.text_analysis
            work_data['visual_analysis'] = work.visual_analysis
            work_data['cross_analysis'] = work.cross_analysis
        
        return work_data
    
    def _get_extension(self) -> str:
        """Get file extension for this format."""
        return "json"


class CSVExporter(BaseExporter):
    """CSV format exporter."""
    
    async def export_works(self, works: List[BlakeWork], output_dir: Path, 
                          config: ExportConfig) -> Path:
        """Export works to CSV file."""
        output_file = output_dir / f"blake_works.{self._get_extension()}"
        
        # Prepare data for CSV
        csv_data = []
        for work in works:
            row = {
                'id': work.id,
                'title': work.metadata.title,
                'work_type': work.metadata.work_type,
                'creation_date': work.metadata.creation_date.isoformat() if work.metadata.creation_date else '',
                'source': work.metadata.source,
                'description': work.metadata.description or '',
                'medium': work.metadata.medium or '',
                'dimensions': work.metadata.dimensions or '',
                'location': work.metadata.location or '',
                'tags': '; '.join(work.metadata.tags),
                'themes': '; '.join(work.metadata.themes),
                'subjects': '; '.join(work.metadata.subjects),
                'has_text': bool(work.text_content),
                'text_length': len(work.text_content) if work.text_content else 0,
                'num_images': len(work.images),
                'is_processed': work.fully_processed,
                **work_provenance(work),
            }
            csv_data.append(row)
        
        fieldnames = [
            'id', 'title', 'work_type', 'creation_date', 'source', 'description',
            'medium', 'dimensions', 'location', 'tags', 'themes', 'subjects',
            'has_text', 'text_length', 'num_images', 'is_processed',
            'source_url', 'source_id', 'source_authority_tier', 'checksum',
            'run_id', 'rights_disposition', 'license_type', 'attribution',
            'usage_terms'
        ]
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        logger.info(f"Exported {len(works)} works to {output_file}")
        return output_file
    
    async def export_work(self, work: BlakeWork, output_path: Path) -> Path:
        """Export single work to CSV file."""
        # For single work, create a simple CSV
        row = {
            'id': work.id,
            'title': work.metadata.title,
            'work_type': work.metadata.work_type,
            'creation_date': work.metadata.creation_date.isoformat() if work.metadata.creation_date else '',
            'source': work.metadata.source,
            'description': work.metadata.description or '',
            'text_content': work.text_content or '',
            'tags': '; '.join(work.metadata.tags),
            'themes': '; '.join(work.metadata.themes),
            **work_provenance(work),
        }
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writeheader()
            writer.writerow(row)
        
        logger.info(f"Exported work {work.id} to {output_path}")
        return output_path
    
    async def export_analysis_results(self, works: List[BlakeWork], 
                                    output_path: Path) -> Path:
        """Export analysis results to CSV file."""
        # This is a simplified version - in practice, you'd flatten the analysis data
        csv_data = []
        
        for work in works:
            row = {
                'work_id': work.id,
                'title': work.metadata.title,
                'has_text_analysis': bool(work.text_analysis),
                'has_visual_analysis': bool(work.visual_analysis),
                'has_cross_analysis': bool(work.cross_analysis),
            }
            
            # Add basic text analysis results
            if work.text_analysis:
                basic_stats = work.text_analysis.get('basic_stats', {})
                row.update({
                    'word_count': basic_stats.get('word_count', 0),
                    'sentence_count': basic_stats.get('sentence_count', 0),
                    'vocabulary_richness': basic_stats.get('vocabulary_richness', 0),
                })
                
                sentiment = work.text_analysis.get('sentiment', {})
                row.update({
                    'sentiment': sentiment.get('sentiment', ''),
                    'sentiment_score': sentiment.get('compound_score', 0),
                })
            
            csv_data.append(row)
        
        fieldnames = [
            'work_id', 'title', 'has_text_analysis', 'has_visual_analysis',
            'has_cross_analysis', 'word_count', 'sentence_count',
            'vocabulary_richness', 'sentiment', 'sentiment_score'
        ]
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(csv_data)
        
        logger.info(f"Exported analysis results to {output_path}")
        return output_path
    
    def _get_extension(self) -> str:
        """Get file extension for this format."""
        return "csv"


class PDFExporter(BaseExporter):
    """PDF format exporter."""
    
    async def export_works(self, works: List[BlakeWork], output_dir: Path, 
                          config: ExportConfig) -> Path:
        """Export works to PDF file."""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
        except ImportError:
            raise ExportError("reportlab not available for PDF export")
        
        output_file = output_dir / f"blake_works.{self._get_extension()}"
        
        # Create PDF document
        doc = SimpleDocTemplate(str(output_file), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
        )
        story.append(Paragraph("William Blake Works Collection", title_style))
        story.append(Spacer(1, 12))
        
        # Add each work
        for i, work in enumerate(works):
            if i > 0:
                story.append(PageBreak())
            
            # Work title
            story.append(Paragraph(work.metadata.title, styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Work metadata
            metadata_text = f"""
            <b>Type:</b> {work.metadata.work_type}<br/>
            <b>Date:</b> {work.metadata.creation_date.strftime('%Y-%m-%d') if work.metadata.creation_date else 'Unknown'}<br/>
            <b>Source:</b> {work.metadata.source}<br/>
            """
            if work.metadata.description:
                metadata_text += f"<b>Description:</b> {work.metadata.description}<br/>"
            
            story.append(Paragraph(metadata_text, styles['Normal']))
            story.append(Spacer(1, 12))
            
            # Text content
            if work.text_content and config.include_metadata:
                story.append(Paragraph("Text Content:", styles['Heading3']))
                story.append(Spacer(1, 6))
                
                # Truncate very long text
                text_content = work.text_content
                if len(text_content) > 5000:
                    text_content = text_content[:5000] + "... [truncated]"
                
                story.append(Paragraph(text_content, styles['Normal']))
                story.append(Spacer(1, 12))
            
            # Analysis results
            if config.include_analysis:
                if work.text_analysis:
                    story.append(Paragraph("Text Analysis:", styles['Heading3']))
                    story.append(Spacer(1, 6))
                    
                    basic_stats = work.text_analysis.get('basic_stats', {})
                    analysis_text = f"""
                    <b>Word Count:</b> {basic_stats.get('word_count', 0)}<br/>
                    <b>Sentence Count:</b> {basic_stats.get('sentence_count', 0)}<br/>
                    <b>Vocabulary Richness:</b> {basic_stats.get('vocabulary_richness', 0):.2f}<br/>
                    """
                    
                    sentiment = work.text_analysis.get('sentiment', {})
                    if sentiment:
                        analysis_text += f"<b>Sentiment:</b> {sentiment.get('sentiment', 'Unknown')}<br/>"
                    
                    story.append(Paragraph(analysis_text, styles['Normal']))
                    story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"Exported {len(works)} works to {output_file}")
        return output_file
    
    async def export_work(self, work: BlakeWork, output_path: Path) -> Path:
        """Export single work to PDF file."""
        # For single work, create a detailed PDF
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError:
            raise ExportError("reportlab not available for PDF export")
        
        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
        )
        story.append(Paragraph(work.metadata.title, title_style))
        story.append(Spacer(1, 12))
        
        # Metadata
        metadata_text = f"""
        <b>Type:</b> {work.metadata.work_type}<br/>
        <b>Date:</b> {work.metadata.creation_date.strftime('%Y-%m-%d') if work.metadata.creation_date else 'Unknown'}<br/>
        <b>Source:</b> {work.metadata.source}<br/>
        """
        if work.metadata.description:
            metadata_text += f"<b>Description:</b> {work.metadata.description}<br/>"
        
        story.append(Paragraph(metadata_text, styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Text content
        if work.text_content:
            story.append(Paragraph("Text Content:", styles['Heading2']))
            story.append(Spacer(1, 6))
            story.append(Paragraph(work.text_content, styles['Normal']))
        
        doc.build(story)
        
        logger.info(f"Exported work {work.id} to {output_path}")
        return output_path
    
    async def export_analysis_results(self, works: List[BlakeWork], 
                                    output_path: Path) -> Path:
        """Export analysis results to PDF file."""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
        except ImportError:
            raise ExportError("reportlab not available for PDF export")
        
        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
        )
        story.append(Paragraph("Blake Works Analysis Results", title_style))
        story.append(Spacer(1, 12))
        
        # Summary table
        table_data = [['Work ID', 'Title', 'Word Count', 'Sentiment', 'Images']]
        
        for work in works:
            word_count = 0
            sentiment = 'Unknown'
            
            if work.text_analysis:
                basic_stats = work.text_analysis.get('basic_stats', {})
                word_count = basic_stats.get('word_count', 0)
                
                sentiment_data = work.text_analysis.get('sentiment', {})
                sentiment = sentiment_data.get('sentiment', 'Unknown')
            
            table_data.append([
                work.id,
                work.metadata.title[:30] + '...' if len(work.metadata.title) > 30 else work.metadata.title,
                str(word_count),
                sentiment,
                str(len(work.images))
            ])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Detailed analysis for each work
        for work in works:
            story.append(Paragraph(f"<b>{work.metadata.title}</b>", styles['Heading2']))
            story.append(Spacer(1, 6))
            
            if work.text_analysis:
                basic_stats = work.text_analysis.get('basic_stats', {})
                analysis_text = f"""
                <b>Text Statistics:</b><br/>
                Word Count: {basic_stats.get('word_count', 0)}<br/>
                Sentence Count: {basic_stats.get('sentence_count', 0)}<br/>
                Vocabulary Richness: {basic_stats.get('vocabulary_richness', 0):.2f}<br/>
                """
                story.append(Paragraph(analysis_text, styles['Normal']))
                story.append(Spacer(1, 6))
        
        doc.build(story)
        
        logger.info(f"Exported analysis results to {output_path}")
        return output_path
    
    def _get_extension(self) -> str:
        """Get file extension for this format."""
        return "pdf"


class HTMLExporter(BaseExporter):
    """HTML format exporter with styled reports."""
    
    async def export_works(self, works: List[BlakeWork], output_dir: Path, 
                          config: ExportConfig) -> Path:
        """Export works to HTML file."""
        output_file = output_dir / f"blake_works.{self._get_extension()}"
        
        html_content = self._generate_html_header("William Blake Works Collection")
        
        # Summary section
        html_content += """
        <div class="summary-section">
            <h2>Collection Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <span class="stat-number">{}</span>
                    <span class="stat-label">Total Works</span>
                </div>
                <div class="stat-card">
                    <span class="stat-number">{}</span>
                    <span class="stat-label">With Text</span>
                </div>
                <div class="stat-card">
                    <span class="stat-number">{}</span>
                    <span class="stat-label">Images</span>
                </div>
            </div>
        </div>
        """.format(
            len(works),
            sum(1 for w in works if w.text_content),
            sum(len(w.images) for w in works)
        )
        
        # Works list
        html_content += '<div class="works-section"><h2>Works</h2>'
        for work in works:
            html_content += self._work_to_html_card(work, config)
        html_content += '</div>'
        
        html_content += self._generate_html_footer()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Exported {len(works)} works to {output_file}")
        return output_file
    
    async def export_work(self, work: BlakeWork, output_path: Path) -> Path:
        """Export single work to HTML file."""
        html_content = self._generate_html_header(work.metadata.title)
        
        config = ExportConfig(
            output_dir=output_path.parent,
            include_images=True,
            include_metadata=True,
            include_analysis=True
        )
        html_content += self._work_to_html_card(work, config, detailed=True)
        html_content += self._generate_html_footer()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Exported work {work.id} to {output_path}")
        return output_path
    
    async def export_analysis_results(self, works: List[BlakeWork], 
                                    output_path: Path) -> Path:
        """Export analysis results to HTML file."""
        html_content = self._generate_html_header("Blake Works Analysis Report")
        
        html_content += '<div class="analysis-section">'
        
        for work in works:
            html_content += f'''
            <div class="work-analysis">
                <h3>{work.metadata.title}</h3>
                <div class="analysis-grid">
            '''
            
            if work.text_analysis:
                basic_stats = work.text_analysis.get('basic_stats', {})
                sentiment = work.text_analysis.get('sentiment', {})
                
                html_content += f'''
                    <div class="analysis-card">
                        <h4>Text Statistics</h4>
                        <p><b>Word Count:</b> {basic_stats.get('word_count', 0)}</p>
                        <p><b>Sentences:</b> {basic_stats.get('sentence_count', 0)}</p>
                        <p><b>Richness:</b> {basic_stats.get('vocabulary_richness', 0):.3f}</p>
                    </div>
                    <div class="analysis-card">
                        <h4>Sentiment</h4>
                        <p class="sentiment-{sentiment.get('sentiment', 'neutral')}">{sentiment.get('sentiment', 'Unknown').title()}</p>
                        <p>Score: {sentiment.get('compound_score', 0):.2f}</p>
                    </div>
                '''
            
            html_content += '</div></div>'
        
        html_content += '</div>'
        html_content += self._generate_html_footer()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Exported analysis results to {output_path}")
        return output_path
    
    def _generate_html_header(self, title: str) -> str:
        """Generate HTML header with CSS styling."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Georgia', serif; line-height: 1.6; background: #f5f5dc; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #8b0000; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }}
        h2 {{ color: #34495e; margin: 1.5rem 0 1rem; }}
        h3 {{ color: #2c3e50; margin: 1rem 0 0.5rem; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; 
                     padding: 1.5rem; border-radius: 8px; text-align: center; }}
        .stat-number {{ display: block; font-size: 2.5rem; font-weight: bold; }}
        .stat-label {{ font-size: 0.9rem; opacity: 0.9; }}
        .work-card {{ background: white; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; 
                     box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .work-card h3 {{ color: #8b0000; border-bottom: 1px solid #ddd; padding-bottom: 0.5rem; }}
        .work-meta {{ color: #666; font-size: 0.9rem; margin: 0.5rem 0; }}
        .work-text {{ background: #fafafa; padding: 1rem; border-radius: 4px; margin-top: 1rem; 
                     max-height: 300px; overflow-y: auto; white-space: pre-wrap; }}
        .analysis-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
        .analysis-card {{ background: #fff; padding: 1rem; border-radius: 8px; border-left: 4px solid #8b0000; }}
        .sentiment-positive {{ color: #27ae60; font-size: 1.2rem; font-weight: bold; }}
        .sentiment-negative {{ color: #e74c3c; font-size: 1.2rem; font-weight: bold; }}
        .sentiment-neutral {{ color: #7f8c8d; font-size: 1.2rem; font-weight: bold; }}
        footer {{ margin-top: 3rem; text-align: center; color: #666; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
'''
    
    def _generate_html_footer(self) -> str:
        """Generate HTML footer."""
        return f'''
        <footer>
            <p>Generated by Blake Analysis Platform on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </footer>
    </div>
</body>
</html>
'''
    
    def _work_to_html_card(self, work: BlakeWork, config: ExportConfig, detailed: bool = False) -> str:
        """Convert work to HTML card."""
        html = f'''
        <div class="work-card">
            <h3>{work.metadata.title}</h3>
            <p class="work-meta">
                <b>Type:</b> {work.metadata.work_type} | 
                <b>Date:</b> {work.metadata.creation_date.strftime('%Y') if work.metadata.creation_date else 'Unknown'} | 
                <b>Source:</b> {work.metadata.source}
            </p>
        '''
        
        if work.metadata.description:
            html += f'<p>{work.metadata.description}</p>'
        
        if work.metadata.themes:
            html += f'<p class="work-meta"><b>Themes:</b> {", ".join(work.metadata.themes)}</p>'
        
        if detailed and work.text_content:
            text_preview = work.text_content[:2000] + '...' if len(work.text_content) > 2000 else work.text_content
            html += f'<div class="work-text">{text_preview}</div>'
        
        if config.include_analysis and work.text_analysis:
            basic_stats = work.text_analysis.get('basic_stats', {})
            html += f'''
            <p class="work-meta">
                <b>Words:</b> {basic_stats.get('word_count', 0)} | 
                <b>Sentences:</b> {basic_stats.get('sentence_count', 0)}
            </p>
            '''
        
        html += '</div>'
        return html
    
    def _get_extension(self) -> str:
        """Get file extension for this format."""
        return "html"


class MarkdownExporter(BaseExporter):
    """Markdown format exporter for documentation-friendly output."""
    
    async def export_works(self, works: List[BlakeWork], output_dir: Path, 
                          config: ExportConfig) -> Path:
        """Export works to Markdown file."""
        output_file = output_dir / f"blake_works.{self._get_extension()}"
        
        md_content = f"# William Blake Works Collection\n\n"
        md_content += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
        
        # Summary
        md_content += "## Summary\n\n"
        md_content += f"| Metric | Value |\n|--------|-------|\n"
        md_content += f"| Total Works | {len(works)} |\n"
        md_content += f"| With Text | {sum(1 for w in works if w.text_content)} |\n"
        md_content += f"| Total Images | {sum(len(w.images) for w in works)} |\n\n"
        
        # Works table
        md_content += "## Works Index\n\n"
        md_content += "| Title | Type | Date | Source |\n|-------|------|------|--------|\n"
        for work in works:
            date = work.metadata.creation_date.strftime('%Y') if work.metadata.creation_date else '-'
            title = work.metadata.title[:40] + '...' if len(work.metadata.title) > 40 else work.metadata.title
            md_content += f"| {title} | {work.metadata.work_type} | {date} | {work.metadata.source} |\n"
        
        md_content += "\n---\n\n## Work Details\n\n"
        
        for work in works:
            md_content += self._work_to_markdown(work, config)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Exported {len(works)} works to {output_file}")
        return output_file
    
    async def export_work(self, work: BlakeWork, output_path: Path) -> Path:
        """Export single work to Markdown file."""
        config = ExportConfig(
            output_dir=output_path.parent,
            include_images=True,
            include_metadata=True,
            include_analysis=True
        )
        
        md_content = self._work_to_markdown(work, config, detailed=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Exported work {work.id} to {output_path}")
        return output_path
    
    async def export_analysis_results(self, works: List[BlakeWork], 
                                    output_path: Path) -> Path:
        """Export analysis results to Markdown file."""
        md_content = "# Blake Works Analysis Report\n\n"
        md_content += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
        
        # Summary table
        md_content += "## Analysis Summary\n\n"
        md_content += "| Work | Words | Sentences | Sentiment | Score |\n"
        md_content += "|------|-------|-----------|-----------|-------|\n"
        
        for work in works:
            if work.text_analysis:
                stats = work.text_analysis.get('basic_stats', {})
                sentiment = work.text_analysis.get('sentiment', {})
                title = work.metadata.title[:30] + '...' if len(work.metadata.title) > 30 else work.metadata.title
                md_content += f"| {title} | {stats.get('word_count', 0)} | {stats.get('sentence_count', 0)} | {sentiment.get('sentiment', '-')} | {sentiment.get('compound_score', 0):.2f} |\n"
        
        md_content += "\n---\n\n## Detailed Analysis\n\n"
        
        for work in works:
            md_content += f"### {work.metadata.title}\n\n"
            
            if work.text_analysis:
                stats = work.text_analysis.get('basic_stats', {})
                md_content += "#### Text Statistics\n\n"
                md_content += f"- **Word Count:** {stats.get('word_count', 0)}\n"
                md_content += f"- **Sentence Count:** {stats.get('sentence_count', 0)}\n"
                md_content += f"- **Vocabulary Richness:** {stats.get('vocabulary_richness', 0):.4f}\n\n"
                
                sentiment = work.text_analysis.get('sentiment', {})
                if sentiment:
                    md_content += "#### Sentiment\n\n"
                    md_content += f"- **Overall:** {sentiment.get('sentiment', 'Unknown')}\n"
                    md_content += f"- **Score:** {sentiment.get('compound_score', 0):.2f}\n\n"
            
            md_content += "---\n\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Exported analysis results to {output_path}")
        return output_path
    
    def _work_to_markdown(self, work: BlakeWork, config: ExportConfig, detailed: bool = False) -> str:
        """Convert work to Markdown section."""
        md = f"### {work.metadata.title}\n\n"
        
        md += f"**Type:** {work.metadata.work_type}  \n"
        md += f"**Date:** {work.metadata.creation_date.strftime('%Y') if work.metadata.creation_date else 'Unknown'}  \n"
        md += f"**Source:** {work.metadata.source}  \n\n"
        provenance = work_provenance(work)
        md += f"**Authority Tier:** {provenance['source_authority_tier']}  \n"
        md += f"**Rights Disposition:** {provenance['rights_disposition']}  \n"
        if provenance.get("source_url"):
            md += f"**Source URL:** {provenance['source_url']}  \n"
        if provenance.get("checksum"):
            md += f"**Checksum:** {provenance['checksum']}  \n"
        md += "\n"
        
        if work.metadata.description:
            md += f"*{work.metadata.description}*\n\n"
        
        if work.metadata.themes:
            md += f"**Themes:** {', '.join(work.metadata.themes)}\n\n"
        
        if detailed and work.text_content:
            md += "#### Text Content\n\n"
            text_preview = work.text_content[:1000] + '...' if len(work.text_content) > 1000 else work.text_content
            md += f"```\n{text_preview}\n```\n\n"
        
        if config.include_analysis and work.text_analysis:
            stats = work.text_analysis.get('basic_stats', {})
            md += f"**Statistics:** {stats.get('word_count', 0)} words, {stats.get('sentence_count', 0)} sentences\n\n"
        
        md += "---\n\n"
        return md
    
    def _get_extension(self) -> str:
        """Get file extension for this format."""
        return "md"


class ParquetExporter(BaseExporter):
    async def export_works(
        self,
        works: List[BlakeWork],
        output_dir: Path,
        config: ExportConfig,
    ) -> Path:
        output_file = output_dir / f"blake_works.{self._get_extension()}"
        self._write_rows([self._work_to_row(work) for work in works], output_file)
        logger.info(f"Exported {len(works)} works to {output_file}")
        return output_file

    async def export_work(self, work: BlakeWork, output_path: Path) -> Path:
        self._write_rows([self._work_to_row(work)], output_path)
        logger.info(f"Exported work {work.id} to {output_path}")
        return output_path

    async def export_analysis_results(
        self,
        works: List[BlakeWork],
        output_path: Path,
    ) -> Path:
        rows = []
        for work in works:
            rows.append({
                'work_id': work.id,
                'title': work.metadata.title,
                'text_analysis': json.dumps(work.text_analysis, default=str),
                'visual_analysis': json.dumps(work.visual_analysis, default=str),
                'cross_analysis': json.dumps(work.cross_analysis, default=str),
            })
        self._write_rows(rows, output_path)
        logger.info(f"Exported analysis results to {output_path}")
        return output_path

    def _write_rows(self, rows: List[Dict[str, Any]], output_path: Path) -> None:
        try:
            import pandas as pd
        except ImportError as exc:
            raise ExportError("pandas and pyarrow are required for Parquet export") from exc
        pd.DataFrame(rows).to_parquet(output_path, index=False)

    def _work_to_row(self, work: BlakeWork) -> Dict[str, Any]:
        provenance = work_provenance(work)
        return {
            'id': work.id,
            'title': work.metadata.title,
            'work_type': str(work.metadata.work_type),
            'source': str(work.metadata.source),
            'creation_date': work.metadata.creation_date.isoformat() if work.metadata.creation_date else None,
            'publication_date': work.metadata.publication_date.isoformat() if work.metadata.publication_date else None,
            'has_text': bool(work.text_content),
            'text_length': len(work.text_content) if work.text_content else 0,
            'image_count': len(work.images),
            'processed': work.fully_processed,
            'themes': json.dumps(work.metadata.themes),
            'subjects': json.dumps(work.metadata.subjects),
            'metadata': json.dumps(work.metadata.model_dump(mode="json"), default=str),
            'source_url': provenance.get("source_url"),
            'source_id': provenance.get("source_id"),
            'source_authority_tier': provenance.get("source_authority_tier"),
            'checksum': provenance.get("checksum"),
            'run_id': provenance.get("run_id"),
            'rights_disposition': provenance.get("rights_disposition"),
            'license_type': provenance.get("license_type"),
            'attribution': provenance.get("attribution"),
            'usage_terms': provenance.get("usage_terms"),
        }

    def _get_extension(self) -> str:
        return "parquet"


EXPORTERS = {
    'json': JSONExporter,
    'csv': CSVExporter,
    'pdf': PDFExporter,
    'html': HTMLExporter,
    'markdown': MarkdownExporter,
    'md': MarkdownExporter,
    'parquet': ParquetExporter,
}


def get_exporter(format_name: str) -> BaseExporter:
    """Get exporter instance for format name."""
    format_lower = format_name.lower()
    if format_lower not in EXPORTERS:
        raise ExportError(f"Unknown export format: {format_name}. Available: {list(EXPORTERS.keys())}")
    return EXPORTERS[format_lower]()
