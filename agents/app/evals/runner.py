"""Eval runner for executing evaluations."""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import importlib
from concurrent.futures import ThreadPoolExecutor

from .base import CJEval, EvalSample, EvalResult, EvalStatus
from .registry import EvalRegistry, EvalConfig

logger = logging.getLogger(__name__)


@dataclass
class RunOptions:
    """Options for running an evaluation."""
    workers: int = 4
    timeout: int = 30
    sample_limit: Optional[int] = None
    prompt_override: Optional[Dict[str, str]] = None
    

@dataclass
class EvalRunResult:
    """Result of an entire eval run."""
    eval_id: str
    run_id: str
    started_at: str
    completed_at: str
    total_samples: int
    results: List[EvalResult]
    summary: Dict[str, Any]
    

class EvalRunner:
    """Runs evaluations on datasets."""
    
    def __init__(self, registry: EvalRegistry):
        """Initialize runner with an eval registry.
        
        Args:
            registry: EvalRegistry instance with loaded configs
        """
        self.registry = registry
        self._eval_cache: Dict[str, CJEval] = {}
        
    def load_samples(self, dataset_path: Path) -> List[EvalSample]:
        """Load samples from a JSONL dataset file.
        
        Args:
            dataset_path: Path to JSONL file
            
        Returns:
            List of EvalSample objects
        """
        samples = []
        
        with open(dataset_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    sample = EvalSample(
                        eval_id=data.get('eval_id', ''),
                        sample_id=data.get('sample_id', f'line_{line_num}'),
                        input=data.get('input', {}),
                        ideal=data.get('ideal'),
                        actual=data.get('actual'),
                        metadata=data.get('metadata', {})
                    )
                    samples.append(sample)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing line {line_num}: {e}")
                except Exception as e:
                    logger.error(f"Error creating sample from line {line_num}: {e}")
                    
        logger.info(f"Loaded {len(samples)} samples from {dataset_path}")
        return samples
        
    def _get_eval_instance(self, eval_config: EvalConfig) -> CJEval:
        """Get or create an eval instance from config.
        
        Args:
            eval_config: EvalConfig object
            
        Returns:
            CJEval instance
        """
        # Check cache first
        cache_key = f"{eval_config.eval_class}:{json.dumps(eval_config.args, sort_keys=True)}"
        if cache_key in self._eval_cache:
            return self._eval_cache[cache_key]
            
        # Parse class path
        module_path, class_name = eval_config.eval_class.rsplit('.', 1)
        
        # Import module and get class
        try:
            # Handle relative imports within our package
            if module_path.startswith('evals.'):
                module_path = f"agents.app.{module_path}"
                
            module = importlib.import_module(module_path)
            eval_class = getattr(module, class_name)
            
            # Create instance with args
            instance = eval_class(**eval_config.args)
            
            # Cache for reuse
            self._eval_cache[cache_key] = instance
            
            return instance
            
        except Exception as e:
            logger.error(f"Error creating eval instance for {eval_config.eval_class}: {e}")
            raise
            
    async def run(self, eval_id: str, dataset_path: Path, options: Optional[RunOptions] = None) -> EvalRunResult:
        """Run an evaluation on a dataset.
        
        Args:
            eval_id: ID of the eval to run
            dataset_path: Path to JSONL dataset
            options: Run options
            
        Returns:
            EvalRunResult with all results and summary
        """
        if options is None:
            options = RunOptions()
            
        # Generate run ID
        run_id = f"{eval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now().isoformat()
        
        logger.info(f"Starting eval run {run_id}")
        
        # Get eval config and instance
        eval_config = self.registry.get_eval(eval_id)
        eval_instance = self._get_eval_instance(eval_config)
        
        # Load samples
        samples = self.load_samples(dataset_path)
        
        # Apply sample limit if specified
        if options.sample_limit:
            samples = samples[:options.sample_limit]
            
        logger.info(f"Running {eval_config.eval_class} on {len(samples)} samples with {options.workers} workers")
        
        # Run evaluations in parallel
        results = await self._run_parallel(eval_instance, samples, options)
        
        # Calculate summary statistics
        summary = self._calculate_summary(results)
        
        completed_at = datetime.now().isoformat()
        
        return EvalRunResult(
            eval_id=eval_id,
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            total_samples=len(samples),
            results=results,
            summary=summary
        )
        
    async def _run_parallel(self, eval_instance: CJEval, samples: List[EvalSample], 
                           options: RunOptions) -> List[EvalResult]:
        """Run evaluations in parallel.
        
        Args:
            eval_instance: The eval instance to use
            samples: List of samples to evaluate
            options: Run options
            
        Returns:
            List of EvalResult objects
        """
        # Create tasks for each sample
        tasks = []
        
        # Use ThreadPoolExecutor for CPU-bound eval tasks
        with ThreadPoolExecutor(max_workers=options.workers) as executor:
            loop = asyncio.get_event_loop()
            
            for sample in samples:
                # Run eval_sample in thread pool
                task = loop.run_in_executor(
                    executor,
                    eval_instance.eval_sample,
                    sample
                )
                tasks.append(task)
                
            # Wait for all tasks with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=options.timeout * len(samples)
                )
            except asyncio.TimeoutError:
                logger.error(f"Eval timed out after {options.timeout * len(samples)} seconds")
                # Cancel remaining tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
                raise
                
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error result
                processed_results.append(EvalResult(
                    sample_id=samples[i].sample_id,
                    status=EvalStatus.ERROR,
                    score=0.0,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
                
        return processed_results
        
    def _calculate_summary(self, results: List[EvalResult]) -> Dict[str, Any]:
        """Calculate summary statistics from results.
        
        Args:
            results: List of EvalResult objects
            
        Returns:
            Summary dictionary
        """
        total = len(results)
        if total == 0:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "accuracy": 0.0,
                "average_score": 0.0
            }
            
        # Count by status
        status_counts = {status: 0 for status in EvalStatus}
        total_score = 0.0
        
        for result in results:
            status_counts[result.status] += 1
            total_score += result.score
            
        # Calculate accuracy (passed / (passed + failed))
        passed = status_counts[EvalStatus.PASS]
        failed = status_counts[EvalStatus.FAIL]
        accuracy = passed / (passed + failed) if (passed + failed) > 0 else 0.0
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": status_counts[EvalStatus.ERROR],
            "skipped": status_counts[EvalStatus.SKIP],
            "accuracy": accuracy,
            "average_score": total_score / total
        }
        
    def save_results(self, eval_run: EvalRunResult, output_dir: Path) -> Path:
        """Save eval run results to file.
        
        Args:
            eval_run: EvalRunResult to save
            output_dir: Directory to save results
            
        Returns:
            Path to saved results file
        """
        # Create output directory
        run_dir = output_dir / eval_run.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save full results
        results_file = run_dir / "results.json"
        with open(results_file, 'w') as f:
            # Convert to dict for JSON serialization
            data = {
                "eval_id": eval_run.eval_id,
                "run_id": eval_run.run_id,
                "started_at": eval_run.started_at,
                "completed_at": eval_run.completed_at,
                "total_samples": eval_run.total_samples,
                "summary": eval_run.summary,
                "results": [asdict(r) for r in eval_run.results]
            }
            json.dump(data, f, indent=2, default=str)
            
        # Save summary separately for quick access
        summary_file = run_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(eval_run.summary, f, indent=2)
            
        logger.info(f"Saved results to {results_file}")
        return results_file