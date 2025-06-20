#!/usr/bin/env python3
"""CLI tool to run HireCJ evaluations."""

import argparse
import asyncio
import logging
from pathlib import Path
import sys
import json

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.app.evals import EvalRegistry, EvalRunner, RunOptions

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_summary(eval_run):
    """Print a nice summary of the eval run."""
    print("\n" + "="*60)
    print(f"Eval Run Summary: {eval_run.run_id}")
    print("="*60)
    print(f"Eval ID: {eval_run.eval_id}")
    print(f"Total Samples: {eval_run.total_samples}")
    print(f"Duration: {eval_run.started_at} to {eval_run.completed_at}")
    print("\nResults:")
    print(f"  Passed: {eval_run.summary['passed']} ({eval_run.summary['passed']/eval_run.total_samples*100:.1f}%)")
    print(f"  Failed: {eval_run.summary['failed']} ({eval_run.summary['failed']/eval_run.total_samples*100:.1f}%)")
    print(f"  Errors: {eval_run.summary['errors']}")
    print(f"  Skipped: {eval_run.summary['skipped']}")
    print(f"\nAccuracy: {eval_run.summary['accuracy']*100:.1f}%")
    print(f"Average Score: {eval_run.summary['average_score']:.3f}")
    print("="*60)
    
    # Show first few failures if any
    failures = [r for r in eval_run.results if r.status.value == 'fail']
    if failures:
        print(f"\nFirst {min(3, len(failures))} failures:")
        for i, failure in enumerate(failures[:3]):
            print(f"\n{i+1}. Sample: {failure.sample_id}")
            print(f"   Reason: {failure.reason}")
            if failure.details:
                print(f"   Details: {json.dumps(failure.details, indent=2)}")


async def main():
    parser = argparse.ArgumentParser(description='Run HireCJ evaluations')
    parser.add_argument(
        '--eval',
        help='Eval ID to run (e.g., tool_selection_accuracy)'
    )
    parser.add_argument(
        '--dataset',
        type=Path,
        help='Path to JSONL dataset file'
    )
    parser.add_argument(
        '--registry',
        type=Path,
        default=Path('hirecj_evals/registry'),
        help='Path to eval registry directory'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('hirecj_evals/results/runs'),
        help='Directory to save results'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of samples to evaluate'
    )
    parser.add_argument(
        '--list-evals',
        action='store_true',
        help='List available eval IDs and exit'
    )
    
    args = parser.parse_args()
    
    # Load registry
    logger.info(f"Loading eval registry from {args.registry}")
    registry = EvalRegistry(args.registry)
    registry.load_evals()
    
    # List evals if requested
    if args.list_evals:
        print("\nAvailable Evals:")
        print("="*60)
        for eval_id in sorted(registry.list_evals()):
            try:
                config = registry.get_eval(eval_id)
                print(f"{eval_id:30} - {config.description}")
            except Exception as e:
                print(f"{eval_id:30} - Error: {e}")
        return
    
    # Check required args when not listing
    if not args.eval or not args.dataset:
        parser.error("--eval and --dataset are required when not using --list-evals")
    
    # Check dataset exists
    if not args.dataset.exists():
        print(f"Error: Dataset file not found: {args.dataset}")
        sys.exit(1)
        
    # Create runner
    runner = EvalRunner(registry)
    
    # Run options
    options = RunOptions(
        workers=args.workers,
        sample_limit=args.limit
    )
    
    try:
        # Run evaluation
        logger.info(f"Running eval '{args.eval}' on dataset '{args.dataset}'")
        eval_run = await runner.run(args.eval, args.dataset, options)
        
        # Save results
        results_path = runner.save_results(eval_run, args.output)
        logger.info(f"Results saved to {results_path}")
        
        # Print summary
        print_summary(eval_run)
        
        # Exit with appropriate code
        if eval_run.summary['failed'] > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error running eval: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())