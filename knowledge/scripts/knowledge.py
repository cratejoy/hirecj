#!/usr/bin/env python3
"""
Knowledge CLI - Simple and powerful command-line interface for Knowledge API
"""
import argparse
import asyncio
import sys
import os
from pathlib import Path
from typing import List, Optional
import glob as glob_module
import json

# Add the parent directory to the path so we can import from lib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.ingester import KnowledgeIngester
from lib.namespace_manager import NamespaceManager
from lib.config import Config
from lib.utils import print_success, print_error, print_info, print_table
from lib.podcast_ingester import PodcastIngester

# Default API base URL
DEFAULT_API_BASE = "http://localhost:8004"


class KnowledgeCLI:
    """Main CLI handler for Knowledge operations"""
    
    def __init__(self):
        self.config = Config()
        self.api_base = self.config.get('api_base', DEFAULT_API_BASE)
        self.default_namespace = self.config.get('default_namespace', 'general')
    
    async def ingest_command(self, args):
        """Handle the ingest command"""
        namespace = args.namespace or self.default_namespace
        
        # Auto-create namespace if requested
        if args.auto_create:
            nm = NamespaceManager(self.api_base)
            created = await nm.ensure_namespace_exists(namespace)
            if created:
                print_success(f"Created namespace: {namespace}")
        
        ingester = KnowledgeIngester(namespace, self.api_base, args.parallel)
        
        # Handle different input types
        results = []
        
        for path_or_url in args.paths:
            # Check if it's a URL
            if path_or_url.startswith(('http://', 'https://')):
                print_info(f"Ingesting URL: {path_or_url}")
                result = await ingester.ingest_url(path_or_url, args.metadata)
                results.append(result)
            
            # Check if it's a file with URLs (--from flag)
            elif args.from_file:
                urls_file = Path(path_or_url)
                if urls_file.exists():
                    print_info(f"Ingesting URLs from: {urls_file}")
                    result = await ingester.ingest_urls_from_file(urls_file)
                    results.extend(result)
                else:
                    print_error(f"URLs file not found: {urls_file}")
            
            # Handle glob patterns and files
            else:
                # Expand glob patterns
                if any(c in path_or_url for c in ['*', '?', '[']):
                    paths = glob_module.glob(path_or_url, recursive=args.recursive)
                    if not paths:
                        print_error(f"No files matching pattern: {path_or_url}")
                        continue
                else:
                    paths = [path_or_url]
                
                for path_str in paths:
                    path = Path(path_str)
                    
                    if path.is_file():
                        print_info(f"Ingesting file: {path}")
                        result = await ingester.ingest_file(path)
                        results.append(result)
                    
                    elif path.is_dir():
                        print_info(f"Ingesting directory: {path}")
                        pattern = args.pattern or '*'
                        dir_results = await ingester.ingest_directory(
                            path, recursive=args.recursive, pattern=pattern
                        )
                        results.extend(dir_results)
                    
                    else:
                        print_error(f"Path not found: {path}")
        
        # Print summary
        await ingester.print_summary()
        
        return 0 if all(r.get('success', False) for r in results if r) else 1
    
    async def list_command(self, args):
        """List all namespaces"""
        nm = NamespaceManager(self.api_base)
        namespaces = await nm.list_namespaces()
        
        if not namespaces:
            print_info("No namespaces found")
            return 0
        
        # Format for table display
        headers = ["ID", "Name", "Documents", "Last Updated", "Status"]
        rows = []
        
        for ns in namespaces:
            # Get statistics if available
            stats = ns.get('stats', {})
            doc_count = stats.get('document_count', 0)
            last_updated = stats.get('last_updated', 'Never')
            
            # Format last updated
            if last_updated and last_updated != 'Never':
                # Parse and format the date nicely
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    last_updated = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            # Determine status
            pending = stats.get('pending_count', 0)
            failed = stats.get('failed_count', 0)
            status = "✅ Ready"
            if pending > 0:
                status = f"⏳ Processing ({pending})"
            elif failed > 0:
                status = f"⚠️  {failed} failed"
            
            rows.append([
                ns['id'],
                ns['name'],
                str(doc_count),
                last_updated,
                status
            ])
        
        print_table(headers, rows, title="Knowledge Namespaces")
        return 0
    
    async def create_command(self, args):
        """Create a new namespace"""
        nm = NamespaceManager(self.api_base)
        
        success = await nm.create_namespace(
            args.namespace_id,
            args.name or args.namespace_id.replace('_', ' ').title(),
            args.description or f"Knowledge base for {args.namespace_id}"
        )
        
        if success:
            print_success(f"Created namespace: {args.namespace_id}")
            
            # Set as default if requested
            if args.set_default:
                self.config.set('default_namespace', args.namespace_id)
                self.config.save()
                print_info(f"Set '{args.namespace_id}' as default namespace")
            
            return 0
        else:
            return 1
    
    async def stats_command(self, args):
        """Show statistics for a namespace"""
        namespace = args.namespace or self.default_namespace
        
        nm = NamespaceManager(self.api_base)
        stats = await nm.get_namespace_stats(namespace)
        
        if not stats:
            print_error(f"Namespace not found: {namespace}")
            return 1
        
        # Display statistics
        print(f"\nStatistics for namespace: {namespace}")
        print("=" * 50)
        print(f"Total documents:     {stats.get('document_count', 0)}")
        print(f"Total chunks:        {stats.get('total_chunks', 0)}")
        print(f"Pending documents:   {stats.get('pending_count', 0)}")
        print(f"Failed documents:    {stats.get('failed_count', 0)}")
        print(f"Stuck documents:     {stats.get('stuck_count', 0)}")
        
        last_updated = stats.get('last_updated', 'Never')
        if last_updated and last_updated != 'Never':
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                last_updated = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        print(f"Last updated:        {last_updated}")
        
        # Show status breakdown if available
        breakdown = stats.get('status_breakdown', {})
        if breakdown:
            print(f"\nStatus breakdown:")
            for status, count in breakdown.items():
                print(f"  {status}:".ljust(20) + str(count))
        
        return 0
    
    async def config_command(self, args):
        """Handle configuration"""
        if args.list:
            # Show current configuration
            print("Current configuration:")
            print("=" * 50)
            for key, value in self.config.config.items():
                print(f"{key}:".ljust(20) + str(value))
            return 0
        
        # Set configuration values
        if args.api_base:
            self.config.set('api_base', args.api_base)
            print_success(f"Set API base URL: {args.api_base}")
        
        if args.default_namespace:
            self.config.set('default_namespace', args.default_namespace)
            print_success(f"Set default namespace: {args.default_namespace}")
        
        if args.parallel:
            self.config.set('parallel_uploads', args.parallel)
            print_success(f"Set parallel uploads: {args.parallel}")
        
        self.config.save()
        return 0
    
    async def podcast_command(self, args):
        """Handle the podcast command"""
        # Ensure namespace exists
        nm = NamespaceManager(self.api_base)
        created = await nm.ensure_namespace_exists(args.namespace)
        if created:
            print_success(f"Created namespace: {args.namespace}")
        
        # Create podcast ingester
        ingester = PodcastIngester(args.namespace, self.api_base)
        
        # Process based on input type
        if args.youtube or args.url.startswith(('https://www.youtube.com/', 'https://youtu.be/')):
            # Process as YouTube video
            success = await ingester.process_youtube_video(
                args.url,
                keep_audio=args.keep_audio
            )
            return 0 if success else 1
        else:
            # Process as RSS feed
            stats = await ingester.ingest_rss_feed(
                args.url,
                limit=args.limit,
                skip_existing=args.skip_existing,
                keep_audio=args.keep_audio
            )
            
            # Return success if at least one episode was processed
            return 0 if stats['processed'] > 0 else 1


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Knowledge CLI - Manage your knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Ingest command
    ingest_parser = subparsers.add_parser(
        'ingest', 
        help='Ingest files or URLs',
        description='Ingest files, directories, or URLs into the knowledge base'
    )
    ingest_parser.add_argument(
        'paths', 
        nargs='+', 
        help='Files, directories, URLs, or glob patterns to ingest'
    )
    ingest_parser.add_argument(
        '-n', '--namespace', 
        help='Target namespace (default: from config or "general")'
    )
    ingest_parser.add_argument(
        '-r', '--recursive', 
        action='store_true',
        help='Process directories recursively'
    )
    ingest_parser.add_argument(
        '-p', '--pattern',
        help='File pattern for directory ingestion (e.g., "*.md")'
    )
    ingest_parser.add_argument(
        '--from', '--from-file',
        dest='from_file',
        action='store_true',
        help='Treat input as a file containing URLs'
    )
    ingest_parser.add_argument(
        '-m', '--metadata',
        type=json.loads,
        help='Additional metadata as JSON string'
    )
    ingest_parser.add_argument(
        '--parallel',
        type=int,
        default=1,
        help='Number of parallel uploads (default: 1)'
    )
    ingest_parser.add_argument(
        '--auto-create',
        action='store_true',
        help='Create namespace if it doesn\'t exist'
    )
    
    # List command
    list_parser = subparsers.add_parser(
        'list',
        help='List all namespaces',
        description='List all available namespaces with statistics'
    )
    
    # Create command
    create_parser = subparsers.add_parser(
        'create',
        help='Create a new namespace',
        description='Create a new namespace for organizing knowledge'
    )
    create_parser.add_argument(
        'namespace_id',
        help='Namespace ID (lowercase, alphanumeric with underscores)'
    )
    create_parser.add_argument(
        '--name',
        help='Human-readable name (default: generated from ID)'
    )
    create_parser.add_argument(
        '--description',
        help='Namespace description'
    )
    create_parser.add_argument(
        '--set-default',
        action='store_true',
        help='Set as default namespace'
    )
    
    # Stats command
    stats_parser = subparsers.add_parser(
        'stats',
        help='Show namespace statistics',
        description='Display detailed statistics for a namespace'
    )
    stats_parser.add_argument(
        'namespace',
        nargs='?',
        help='Namespace to show stats for (default: from config)'
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        'config',
        help='Configure Knowledge CLI',
        description='View or update CLI configuration'
    )
    config_parser.add_argument(
        '--list',
        action='store_true',
        help='List current configuration'
    )
    config_parser.add_argument(
        '--api-base',
        help='Set API base URL'
    )
    config_parser.add_argument(
        '--default-namespace',
        help='Set default namespace'
    )
    config_parser.add_argument(
        '--parallel',
        type=int,
        help='Set default parallel uploads'
    )
    
    # Podcast command
    podcast_parser = subparsers.add_parser(
        'podcast',
        help='Ingest podcasts from RSS feeds',
        description='Download and transcribe podcasts from RSS feeds'
    )
    podcast_parser.add_argument(
        'url',
        help='RSS feed URL or YouTube video URL'
    )
    podcast_parser.add_argument(
        '-n', '--namespace',
        required=True,
        help='Target namespace for ingestion'
    )
    podcast_parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of episodes to process (RSS only)'
    )
    podcast_parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='Skip episodes that have already been processed (default: True)'
    )
    podcast_parser.add_argument(
        '--keep-audio',
        action='store_true',
        help='Keep audio files after processing'
    )
    podcast_parser.add_argument(
        '--youtube',
        action='store_true',
        help='Process as YouTube video instead of RSS feed'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show help if no command
    if not args.command:
        parser.print_help()
        return 1
    
    # Create CLI instance and run command
    cli = KnowledgeCLI()
    
    try:
        if args.command == 'ingest':
            return await cli.ingest_command(args)
        elif args.command == 'list':
            return await cli.list_command(args)
        elif args.command == 'create':
            return await cli.create_command(args)
        elif args.command == 'stats':
            return await cli.stats_command(args)
        elif args.command == 'config':
            return await cli.config_command(args)
        elif args.command == 'podcast':
            return await cli.podcast_command(args)
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print_error("\nOperation cancelled")
        return 1
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))