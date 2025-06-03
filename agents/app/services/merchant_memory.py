"""
Merchant memory service for managing persistent facts about merchants.

This service handles loading, saving, and managing merchant-specific knowledge
that accumulates across conversations.
"""
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)


class MerchantMemory:
    """Container for merchant facts/memory."""
    
    def __init__(self, merchant_id: str, facts: List[Dict[str, Any]] = None):
        """Initialize merchant memory.
        
        Args:
            merchant_id: Unique identifier for the merchant
            facts: Optional list of existing facts
        """
        self.merchant_id = merchant_id
        self.facts = facts or []
    
    def add_fact(self, fact: str, source: str):
        """Add a new fact (append-only).
        
        Args:
            fact: The fact text to add
            source: Source identifier (e.g., conversation_id)
        """
        self.facts.append({
            'fact': fact,
            'learned_at': datetime.now().isoformat(),
            'source': source
        })
        logger.info(f"[MEMORY] Added new fact for {self.merchant_id}: '{fact[:100]}...' from source: {source}")
    
    def get_all_facts(self) -> List[str]:
        """Get all facts as strings.
        
        Returns:
            List of fact strings
        """
        return [f['fact'] for f in self.facts]
    
    def get_recent_facts(self, limit: int = 20) -> List[str]:
        """Get most recent facts.
        
        Args:
            limit: Maximum number of facts to return
            
        Returns:
            List of most recent fact strings
        """
        # Facts are stored in order, so return the last N
        return [f['fact'] for f in self.facts[-limit:]]


class MerchantMemoryService:
    """Service for managing merchant memory persistence."""
    
    def __init__(self):
        """Initialize the service with memory directory."""
        self.memory_dir = Path("data/merchant_memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Initialized MerchantMemoryService with directory: {self.memory_dir}")
    
    def load_memory(self, merchant_id: str) -> MerchantMemory:
        """Load merchant memory from storage.
        
        Args:
            merchant_id: Unique identifier for the merchant
            
        Returns:
            MerchantMemory instance with loaded facts or empty if not found
        """
        memory_file = self.memory_dir / f"{merchant_id}_memory.yaml"
        
        if memory_file.exists():
            try:
                with open(memory_file, 'r') as f:
                    data = yaml.safe_load(f) or {}
                
                facts = data.get('facts', [])
                logger.info(f"Loaded {len(facts)} facts for merchant {merchant_id}")
                return MerchantMemory(merchant_id, facts)
                
            except Exception as e:
                logger.error(f"Error loading memory for {merchant_id} from {memory_file}: {e}")
                raise  # Re-raise the exception - don't swallow it
        else:
            logger.info(f"No existing memory found for merchant {merchant_id}, starting fresh")
            return MerchantMemory(merchant_id, [])
    
    def save_memory(self, memory: MerchantMemory):
        """Save merchant memory to storage.
        
        Args:
            memory: MerchantMemory instance to save
        """
        memory_file = self.memory_dir / f"{memory.merchant_id}_memory.yaml"
        
        try:
            data = {
                'merchant_id': memory.merchant_id,
                'last_updated': datetime.now().isoformat(),
                'facts': memory.facts
            }
            
            with open(memory_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"[MEMORY] Successfully saved {len(memory.facts)} facts for merchant {memory.merchant_id} to {memory_file}")
            
        except Exception as e:
            logger.error(f"[MEMORY] Error saving memory for {memory.merchant_id} to {memory_file}: {e}")
            raise  # Re-raise the exception - don't swallow it