"""
Interactive Terminal Orchestrator

A comprehensive interactive CLI for managing the Blake system with
real-time reporting, analysis options, and workflow management.
"""

import asyncio
import logging
import json
import sys
from pathlib import Path
from typing import Any, List, Optional, TextIO

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import box

from .corpus import BlakeCorpus
from .models import ExportConfig
from .provenance import enum_value

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()


class InteractiveOrchestrator:
    """Interactive terminal orchestrator for Blake system."""
    
    def __init__(
        self, data_dir: str = "./blake_data", *,
        output_dir: Optional[Path] = None, console: Optional[Console] = None,
        input_stream: Optional[TextIO] = None,
    ):
        """Initialize the orchestrator."""
        self.data_dir = Path(data_dir)
        self.blake = None
        self.console = console if console is not None else Console()
        self.output_dir = output_dir
        self.input_stream = input_stream
        
    async def initialize(self):
        """Initialize the Blake system."""
        try:
            with self.console.status("[bold green]Initializing Blake system..."):
                self.blake = BlakeCorpus(self.data_dir, output_dir=self.output_dir)
                await self.blake.initialize()
            self.console.print("✅ [green]Blake system initialized successfully![/green]")
        except Exception as e:
            self.console.print(f"❌ [red]Failed to initialize Blake system: {e}[/red]")
            sys.exit(1)
    
    def display_welcome(self):
        """Display welcome screen."""
        welcome_text = """
[bold blue]╔══════════════════════════════════════════════════════════════╗[/bold blue]
[bold blue]║                                                              ║[/bold blue]
[bold blue]║  🎨 Blake Interactive Orchestrator v1.0                     ║[/bold blue]
[bold blue]║                                                              ║[/bold blue]
[bold blue]║  Target-aware analysis and exploration platform for         ║[/bold blue]
[bold blue]║  locally available William Blake corpus evidence            ║[/bold blue]
[bold blue]║                                                              ║[/bold blue]
[bold blue]╚══════════════════════════════════════════════════════════════╝[/bold blue]
        """
        self.console.print(welcome_text)
    
    def display_main_menu(self):
        """Display main menu options."""
        menu_text = """
[bold cyan]Main Menu:[/bold cyan]

[bold yellow]📊 Data Management:[/bold yellow]
  1. 📥 Fetch provider records
  2. 📋 View available works
  3. 🔍 Search works
  4. 📈 View statistics

[bold yellow]🔬 Analysis:[/bold yellow]
  5. 📝 Text analysis
  6. 🖼️  Visual analysis
  7. 🔗 Cross-analysis
  8. 📊 Comparative analysis

[bold yellow]📊 Visualization:[/bold yellow]
  9. 🎨 Create visualizations
  10. 📊 View dashboards
  11. 📄 Generate reports

[bold yellow]⚙️  System:[/bold yellow]
  12. 🧹 Clear cache
  13. 📤 Export data
  14. 🔧 Settings
  15. ❌ Exit

[bold cyan]Enter your choice (1-15):[/bold cyan]
        """
        self.console.print(menu_text)
    
    async def download_all_works(self):
        self.console.print("\n[bold blue]📥 Fetching provider records...[/bold blue]")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task("Downloading works...", total=100)
                
                # Download works
                works = await self.blake.download_all()
                
                progress.update(task, completed=100)
            
            self.console.print(f"✅ [green]Successfully downloaded {len(works)} works![/green]")
            
            # Show summary
            await self.show_works_summary(works)
            
        except Exception as e:
            self.console.print(f"❌ [red]Download failed: {e}[/red]")
    
    async def show_works_summary(self, works: List[Any]):
        """Show summary of downloaded works."""
        if not works:
            self.console.print("📭 [yellow]No works available[/yellow]")
            return
        
        # Create summary table
        table = Table(title="📚 Works Summary", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("Source", style="blue")
        table.add_column("Status", style="yellow")
        
        for work in works[:10]:  # Show first 10 works
            status = "✅ Analyzed" if work.fully_processed else "⏳ Pending"
            table.add_row(
                work.id,
                work.metadata.title[:50] + "..." if len(work.metadata.title) > 50 else work.metadata.title,
                enum_value(work.metadata.work_type) or "Unknown",
                enum_value(work.metadata.source) or "Unknown",
                status
            )
        
        if len(works) > 10:
            table.add_row("...", f"... and {len(works) - 10} more", "", "", "")
        
        self.console.print(table)
    
    async def view_available_works(self):
        """View all available works."""
        self.console.print("\n[bold blue]📋 Available Works[/bold blue]")
        
        try:
            works = await self.blake.get_all_works()
            await self.show_works_summary(works)
            
            # Show detailed statistics
            await self.show_works_statistics(works)
            
        except Exception as e:
            self.console.print(f"❌ [red]Failed to retrieve works: {e}[/red]")
    
    async def show_works_statistics(self, works: List[Any]):
        """Show detailed statistics about works."""
        if not works:
            return
        
        # Calculate statistics
        total_works = len(works)
        analyzed_works = len([w for w in works if w.fully_processed])
        text_works = len([w for w in works if w.text_content])
        image_works = len([w for w in works if w.images])
        
        # Work types
        work_types = {}
        for work in works:
            work_type = enum_value(work.metadata.work_type) or "Unknown"
            work_types[work_type] = work_types.get(work_type, 0) + 1
        
        # Sources
        sources = {}
        for work in works:
            source = enum_value(work.metadata.source) or "Unknown"
            sources[source] = sources.get(source, 0) + 1
        
        # Create statistics panel
        stats_text = f"""
[bold cyan]📊 Statistics:[/bold cyan]
• Total Works: {total_works}
• Analyzed: {analyzed_works} ({analyzed_works/total_works*100:.1f}%)
• With Text: {text_works}
• With Images: {image_works}

[bold cyan]📚 Work Types:[/bold cyan]
{chr(10).join([f"• {work_type}: {count}" for work_type, count in work_types.items()])}

[bold cyan]🌐 Sources:[/bold cyan]
{chr(10).join([f"• {source}: {count}" for source, count in sources.items()])}
        """
        
        self.console.print(Panel(stats_text, title="📊 Works Statistics", border_style="blue"))
    
    async def search_works(self):
        """Search works by content."""
        query = Prompt.ask("\n[bold cyan]🔍 Enter search query[/bold cyan]", console=self.console, stream=self.input_stream)
        
        if not query:
            self.console.print("❌ [red]Search query cannot be empty[/red]")
            return
        
        try:
            with self.console.status(f"[bold green]Searching for '{query}'..."):
                results = await self.blake.search_works(query)
            
            if not results:
                self.console.print(f"📭 [yellow]No works found matching '{query}'[/yellow]")
                return
            
            self.console.print(f"✅ [green]Found {len(results)} works matching '{query}'[/green]")
            
            # Display results
            table = Table(title=f"🔍 Search Results for '{query}'", box=box.ROUNDED)
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="magenta")
            table.add_column("Relevance", style="green")
            table.add_column("Preview", style="yellow")
            
            for result in results[:10]:  # Show first 10 results
                preview = result.text_content[:100] + "..." if result.text_content and len(result.text_content) > 100 else result.text_content or "No text content"
                table.add_row(
                    result.id,
                    result.metadata.title,
                    "High",  # Placeholder for relevance score
                    preview
                )
            
            self.console.print(table)
            
        except Exception as e:
            self.console.print(f"❌ [red]Search failed: {e}[/red]")
    
    async def run_text_analysis(self):
        """Run text analysis on works."""
        self.console.print("\n[bold blue]📝 Text Analysis[/bold blue]")
        
        try:
            works = await self.blake.get_all_works()
            if not works:
                self.console.print("📭 [yellow]No works available for analysis[/yellow]")
                return
            
            # Show analysis options
            analysis_options = {
                "1": "Basic analysis (sentiment, topics, entities)",
                "2": "Advanced analysis (stylistic features, complexity)",
                "3": "Comparative analysis (compare multiple works)",
                "4": "Full analysis (all features)"
            }
            
            self.console.print("\n[bold cyan]Analysis Options:[/bold cyan]")
            for key, desc in analysis_options.items():
                self.console.print(f"  {key}. {desc}")
            
            choice = Prompt.ask("Select analysis type", choices=list(analysis_options.keys()), console=self.console, stream=self.input_stream)
            
            with self.console.status("[bold green]Running text analysis..."):
                if choice == "1":
                    results = await self.blake.analyze_all(["text"])
                elif choice == "2":
                    results = await self.blake.analyze_all(["text"])
                elif choice == "3":
                    results = await self.blake.analyze_all(["text", "cross"])
                else:
                    results = await self.blake.analyze_all(["text", "visual", "cross"])
            
            self.console.print(f"✅ [green]Analysis completed! Processed {len(results)} works[/green]")
            
            # Show analysis summary
            await self.show_analysis_summary(results)
            
        except Exception as e:
            self.console.print(f"❌ [red]Analysis failed: {e}[/red]")
    
    async def show_analysis_summary(self, results: List[Any]):
        """Show summary of analysis results."""
        if not results:
            return
        
        # Calculate analysis statistics
        analyzed_count = len([r for r in results if r.text_analysis])
        sentiment_scores = []
        topics = []
        
        for result in results:
            if result.text_analysis:
                if 'sentiment' in result.text_analysis:
                    sentiment = result.text_analysis['sentiment']
                    sentiment_scores.append(sentiment.get('compound_score', sentiment.get('compound', 0)))
                if 'topics' in result.text_analysis:
                    records = result.text_analysis['topics']
                    if isinstance(records, dict):
                        records = records.get('topics', [])
                    if not isinstance(records, list):
                        raise ValueError("Saved topic records must be a list")
                    topics.extend(json.dumps(record, sort_keys=True, default=str) for record in records)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        unique_topics = len(set(topics))
        
        summary_text = f"""
[bold cyan]📊 Analysis Summary:[/bold cyan]
• Works Analyzed: {analyzed_count}
• Average Sentiment: {avg_sentiment:.2f}
• Distinct Saved Topic Records: {unique_topics}
• Total Saved Topic Records: {len(topics)}
        """
        
        self.console.print(Panel(summary_text, title="📊 Analysis Results", border_style="green"))
    
    async def create_visualizations(self):
        """Create visualizations."""
        self.console.print("\n[bold blue]🎨 Visualization Creation[/bold blue]")
        
        try:
            # Get available visualizations
            viz_types = await self.blake.get_available_visualizations()
            
            if not viz_types:
                self.console.print("📭 [yellow]No visualizations available[/yellow]")
                return
            
            # Show visualization options
            self.console.print("\n[bold cyan]Available Visualizations:[/bold cyan]")
            for i, viz in enumerate(viz_types, 1):
                self.console.print(f"  {i}. {viz['type']} - {viz['description']}")
            
            choice = IntPrompt.ask("Select visualization (number)", default=1, console=self.console, stream=self.input_stream)
            
            if 1 <= choice <= len(viz_types):
                selected_viz = viz_types[choice - 1]
                
                with self.console.status(f"[bold green]Creating {selected_viz['type']} visualization..."):
                    result = await self.blake.create_visualization(
                        selected_viz['type'],
                        "text",  # Default to text data
                        {"title": f"Blake {selected_viz['type'].title()} Visualization"}
                    )
                
                self.console.print(f"✅ [green]Visualization '{selected_viz['type']}' created successfully![/green]")
                
                # Show visualization details
                self.console.print("\n[bold cyan]Visualization Details:[/bold cyan]")
                self.console.print(f"• Type: {result.get('type', 'Unknown')}")
                self.console.print(f"• Category: {result.get('metadata', {}).get('renderer', 'Unknown')}")
                self.console.print(f"• Work Count: {result.get('metadata', {}).get('work_count', 'Unknown')}")
            else:
                self.console.print("❌ [red]Invalid selection[/red]")
                
        except Exception as e:
            self.console.print(f"❌ [red]Visualization creation failed: {e}[/red]")
    
    async def view_dashboards(self):
        """View available dashboards."""
        self.console.print("\n[bold blue]📊 Available Dashboards[/bold blue]")
        
        try:
            summary = await self.blake.get_dashboard_summary()
            
            # Create dashboard table
            table = Table(title="📊 Dashboards", box=box.ROUNDED)
            table.add_column("Type", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Description", style="green")
            table.add_column("Components", style="yellow")
            
            for dashboard in summary.get('available_dashboards', []):
                table.add_row(
                    dashboard['type'],
                    dashboard['name'],
                    dashboard['description'],
                    str(dashboard['component_count'])
                )
            
            self.console.print(table)
            
            # Ask if user wants to create a dashboard
            if Confirm.ask("\n[bold cyan]Would you like to create a dashboard?[/bold cyan]", console=self.console, stream=self.input_stream):
                await self.create_dashboard()
                
        except Exception as e:
            self.console.print(f"❌ [red]Failed to retrieve dashboards: {e}[/red]")
    
    async def create_dashboard(self):
        """Create a dashboard."""
        dashboard_types = {
            "1": ("research", "Research Dashboard"),
            "2": ("educational", "Educational Dashboard"),
            "3": ("public", "Public Dashboard")
        }
        
        self.console.print("\n[bold cyan]Dashboard Types:[/bold cyan]")
        for key, (_, name) in dashboard_types.items():
            self.console.print(f"  {key}. {name}")
        
        choice = Prompt.ask("Select dashboard type", choices=list(dashboard_types.keys()), console=self.console, stream=self.input_stream)
        
        if choice in dashboard_types:
            dashboard_type, dashboard_name = dashboard_types[choice]
            
            with self.console.status(f"[bold green]Creating {dashboard_name}..."):
                if dashboard_type == "research":
                    result = await self.blake.create_research_dashboard()
                elif dashboard_type == "educational":
                    result = await self.blake.create_educational_dashboard()
                else:
                    result = await self.blake.create_public_dashboard()
            
            self.console.print(f"✅ [green]{dashboard_name} created successfully![/green]")
            self.console.print(f"• Components: {result.get('component_count', 'Unknown')}")
    
    async def generate_reports(self):
        """Generate reports."""
        self.console.print("\n[bold blue]📄 Report Generation[/bold blue]")
        
        report_types = {
            "1": ("research", "Research Report"),
            "2": ("educational", "Educational Report"),
            "3": ("public", "Public Report")
        }
        
        self.console.print("\n[bold cyan]Report Types:[/bold cyan]")
        for key, (_, name) in report_types.items():
            self.console.print(f"  {key}. {name}")
        
        choice = Prompt.ask("Select report type", choices=list(report_types.keys()), console=self.console, stream=self.input_stream)
        
        if choice in report_types:
            report_type, report_name = report_types[choice]
            
            with self.console.status(f"[bold green]Generating {report_name}..."):
                if report_type == "research":
                    result = await self.blake.generate_research_report()
                elif report_type == "educational":
                    result = await self.blake.generate_educational_report()
                else:
                    result = await self.blake.generate_public_report()
            
            self.console.print(f"✅ [green]{report_name} generated successfully![/green]")
            self.console.print(f"• Report ID: {result['report'].id}")
    
    async def clear_cache(self):
        """Clear system cache."""
        if Confirm.ask("\n[bold red]Are you sure you want to clear the cache?[/bold red]", console=self.console, stream=self.input_stream):
            try:
                with self.console.status("[bold green]Clearing cache..."):
                    await self.blake.clear_cache()
                self.console.print("✅ [green]Cache cleared successfully![/green]")
            except Exception as e:
                self.console.print(f"❌ [red]Failed to clear cache: {e}[/red]")
    
    async def export_data(self):
        """Export data."""
        self.console.print("\n[bold blue]📤 Data Export[/bold blue]")
        
        export_formats = {
            "1": "JSON",
            "2": "CSV", 
            "3": "PDF"
        }
        
        self.console.print("\n[bold cyan]Export Formats:[/bold cyan]")
        for key, format_name in export_formats.items():
            self.console.print(f"  {key}. {format_name}")
        
        choice = Prompt.ask("Select export format", choices=list(export_formats.keys()), console=self.console, stream=self.input_stream)
        
        if choice in export_formats:
            format_name = export_formats[choice]
            
            try:
                with self.console.status(f"[bold green]Exporting data as {format_name}..."):
                    result = await self.blake.export_works(
                        ExportConfig(
                            format=format_name.lower(),
                            output_dir=self.blake.output_dir / "exports",
                        )
                    )
                
                self.console.print(f"✅ [green]Data exported as {format_name} successfully![/green]")
                self.console.print(f"• Path: {result}")
                return result
            except Exception as e:
                self.console.print(f"❌ [red]Export failed: {e}[/red]")
    
    async def show_settings(self):
        """Show current settings."""
        self.console.print("\n[bold blue]⚙️ Settings[/bold blue]")
        
        settings_text = f"""
[bold cyan]Current Settings:[/bold cyan]
• Data Directory: {self.data_dir}
• System Status: {'✅ Initialized' if self.blake else '❌ Not initialized'}
• Cache Enabled: True
• Log Level: INFO
        """
        
        self.console.print(Panel(settings_text, title="⚙️ System Settings", border_style="blue"))
    
    async def run(self):
        """Run the interactive orchestrator."""
        self.display_welcome()
        await self.initialize()
        
        while True:
            try:
                self.display_main_menu()
                choice = Prompt.ask("", choices=[str(i) for i in range(1, 16)], console=self.console, stream=self.input_stream)
                
                if choice == "1":
                    await self.download_all_works()
                elif choice == "2":
                    await self.view_available_works()
                elif choice == "3":
                    await self.search_works()
                elif choice == "4":
                    works = await self.blake.get_all_works()
                    await self.show_works_statistics(works)
                elif choice == "5":
                    await self.run_text_analysis()
                elif choice == "6":
                    self.console.print("🖼️ [yellow]Visual analysis not yet implemented[/yellow]")
                elif choice == "7":
                    self.console.print("🔗 [yellow]Cross-analysis not yet implemented[/yellow]")
                elif choice == "8":
                    self.console.print("📊 [yellow]Comparative analysis not yet implemented[/yellow]")
                elif choice == "9":
                    await self.create_visualizations()
                elif choice == "10":
                    await self.view_dashboards()
                elif choice == "11":
                    await self.generate_reports()
                elif choice == "12":
                    await self.clear_cache()
                elif choice == "13":
                    await self.export_data()
                elif choice == "14":
                    await self.show_settings()
                elif choice == "15":
                    if Confirm.ask("\n[bold red]Are you sure you want to exit?[/bold red]", console=self.console, stream=self.input_stream):
                        self.console.print("👋 [green]Goodbye![/green]")
                        break
                
                # Pause before showing menu again
                if choice != "15":
                    Prompt.ask("\n[dim]Press Enter to continue...[/dim]", console=self.console, stream=self.input_stream)
                    
            except KeyboardInterrupt:
                if Confirm.ask("\n[bold red]Are you sure you want to exit?[/bold red]", console=self.console, stream=self.input_stream):
                    self.console.print("👋 [green]Goodbye![/green]")
                    break
            except Exception as e:
                self.console.print(f"❌ [red]An error occurred: {e}[/red]")
                logger.exception("Error in interactive orchestrator")


async def main():
    """Main entry point."""
    orchestrator = InteractiveOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())
