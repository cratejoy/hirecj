"""
Cache warming service for pre-generating first messages
"""

import asyncio
import logging
import os
from typing import Dict, Optional, Any
from datetime import datetime

from app.universe import UniverseLoader
from app.workflows import WorkflowLoader
from app.services.session_manager import SessionManager
from app.services.message_processor import MessageProcessor
from app.services.conversation_storage import ConversationStorage

logger = logging.getLogger(__name__)


class CacheWarmingService:
    """Service to warm cache with first messages on startup"""

    def __init__(self, concurrency: int = None):
        """
        Initialize cache warming service

        Args:
            concurrency: Maximum number of concurrent warming tasks
        """
        if concurrency is None:
            from app.config import settings

            concurrency = settings.cache_warm_concurrency
        self.concurrency = concurrency
        self.universe_loader = UniverseLoader()
        self.workflow_loader = WorkflowLoader()
        self.session_manager = SessionManager()
        self.message_processor = MessageProcessor()
        self.conversation_storage = ConversationStorage()
        self.warming_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None,
        }

    async def warm_all_first_messages(self) -> Dict[str, Any]:
        """
        Warm cache for all workflow/universe combinations

        Returns:
            Statistics about the warming process
        """
        logger.info("🔥 Starting cache warming for first messages...")
        self.warming_stats["start_time"] = datetime.utcnow()

        # Get all available universes
        universes = self.universe_loader.list_universes()
        logger.info(f"Found {len(universes)} universes to process")

        # Get all available workflows
        workflows = self.workflow_loader.list_workflows()
        logger.info(f"Found {len(workflows)} workflows to process")

        # Create combinations to process
        combinations = []
        for universe_id in universes:
            # Check if universe has data
            try:
                universe = self.universe_loader.load(universe_id)
                if not universe:
                    logger.warning(f"Skipping universe {universe_id} - no data")
                    self.warming_stats["skipped"] += 1
                    continue

                # Add combinations for each workflow
                for workflow_id in workflows:
                    combinations.append((universe_id, workflow_id))

            except Exception as e:
                logger.error(f"Error loading universe {universe_id}: {e}")
                self.warming_stats["skipped"] += 1
                continue

        # Process combinations in parallel with concurrency limit
        if combinations:
            self.warming_stats["total"] = len(combinations)
            logger.info(
                f"Processing {len(combinations)} cache warming tasks with concurrency={self.concurrency}..."
            )

            # Use semaphore to limit concurrency
            semaphore = asyncio.Semaphore(self.concurrency)

            async def warm_with_limit(universe_id: str, workflow_id: str):
                async with semaphore:
                    return await self._warm_single_combination(universe_id, workflow_id)

            # Create tasks for parallel execution
            tasks = [
                asyncio.create_task(warm_with_limit(universe_id, workflow_id))
                for universe_id, workflow_id in combinations
            ]

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count results
            for result in results:
                if isinstance(result, Exception):
                    self.warming_stats["failed"] += 1
                elif isinstance(result, dict):
                    if result.get("success"):
                        self.warming_stats["success"] += 1
                    elif result.get("skipped"):
                        self.warming_stats["skipped"] += 1
                    elif result.get("failed"):
                        self.warming_stats["failed"] += 1
                    else:
                        self.warming_stats["failed"] += 1
                else:
                    self.warming_stats["failed"] += 1

        self.warming_stats["end_time"] = datetime.utcnow()
        duration = (
            self.warming_stats["end_time"] - self.warming_stats["start_time"]
        ).total_seconds()

        logger.info(f"✅ Cache warming completed in {duration:.1f}s")
        logger.info(f"   Total: {self.warming_stats['total']}")
        logger.info(f"   Success: {self.warming_stats['success']}")
        logger.info(f"   Failed: {self.warming_stats['failed']}")
        logger.info(f"   Skipped: {self.warming_stats['skipped']}")

        return self.warming_stats

    async def _warm_single_combination(self, universe_id: str, workflow_id: str):
        """Warm cache for a specific universe/workflow combination"""
        try:
            logger.debug(f"Warming cache for {universe_id}/{workflow_id}")

            # Generate the first message
            result = await self._generate_and_cache_first_message(
                universe_id, workflow_id
            )

            if result:
                if result.get("skipped"):
                    return {"skipped": True}
                logger.info(f"✅ Cached first message for {universe_id}/{workflow_id}")
                return {"success": True}
            else:
                logger.warning(f"❌ Failed to cache {universe_id}/{workflow_id}")
                return {"failed": True}

        except Exception as e:
            logger.error(f"Error warming cache for {universe_id}/{workflow_id}: {e}")
            return False  # Return False instead of raising to not break other tasks

    async def _generate_and_cache_first_message(
        self, universe_id: str, workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate and cache the first message for a universe/workflow combo

        This ensures consistency with actual conversation generation
        and proper caching.
        """
        try:
            # Only warm cache for workflows that start with CJ
            if workflow_id not in ["daily_briefing", "weekly_review"]:
                logger.info(f"Skipping {workflow_id} - not a CJ-initiated workflow")
                return {"skipped": True}

            # Load universe to get metadata
            universe = self.universe_loader.load(universe_id)
            if not universe:
                return None

            # Extract merchant and scenario from universe metadata
            metadata = universe.get("metadata", {})
            merchant_name = metadata.get("merchant", "")
            scenario_name = metadata.get("scenario", "")

            # Create a conversation session
            session = self.session_manager.create_session(
                merchant_name=merchant_name,
                scenario_name=scenario_name,
                workflow_name=workflow_id,
                universe_path=f"data/universes/{universe_id}.yaml",
            )

            # Generate the initial message
            # This will create the CJ agent with caching and generate the first message
            try:
                # For cache warming, we process an empty message to trigger initial response
                initial_message = await self.message_processor.process_message(
                    session=session,
                    message="Provide daily briefing",
                    sender="merchant",
                )
            except Exception as e:
                logger.error(f"Failed to generate initial message: {e}")
                initial_message = None

            if initial_message:
                logger.info(
                    f"✅ Successfully generated and cached first message for {universe_id}/{workflow_id}"
                )

                # Clean up the session (we don't need to save the conversation)
                self.session_manager.end_session(session.id)

                return {
                    "universe_id": universe_id,
                    "workflow_id": workflow_id,
                    "message": initial_message,
                    "cached_at": datetime.utcnow().isoformat(),
                }

            return None

        except Exception as e:
            logger.error(f"Error generating first message: {e}")
            logger.exception(e)  # Log full traceback
            return None

    async def warm_specific_combination(
        self, universe_id: str, workflow_id: str
    ) -> bool:
        """
        Warm cache for a specific universe/workflow combination

        Useful for warming cache after creating new content
        """
        try:
            result = await self._generate_and_cache_first_message(
                universe_id, workflow_id
            )
            return result is not None
        except Exception as e:
            logger.error(f"Error warming specific combination: {e}")
            return False


# Convenience function for startup
async def warm_cache_on_startup():
    """Convenience function to warm cache on application startup"""
    # Check if cache warming is enabled
    if os.getenv("WARM_CACHE_ON_STARTUP", "true").lower() != "true":
        logger.info("Cache warming disabled by environment variable")
        return

    # Create service with default concurrency from settings
    service = CacheWarmingService()

    # Run warming in background to not block startup
    asyncio.create_task(service.warm_all_first_messages())
