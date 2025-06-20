"""Registry loader for HireCJ eval configurations."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvalConfig:
    """Configuration for a single eval."""
    id: str
    description: str
    eval_class: str
    args: Dict[str, Any]
    parent: Optional[str] = None
    dataset: Optional[str] = None
    
    
class EvalRegistry:
    """Loads and manages eval configurations from YAML files."""
    
    def __init__(self, registry_path: Path):
        """Initialize registry with path to YAML files.
        
        Args:
            registry_path: Path to directory containing YAML eval definitions
        """
        self.registry_path = Path(registry_path)
        self.evals: Dict[str, Dict[str, Any]] = {}
        self._raw_configs: Dict[str, Dict[str, Any]] = {}
        
    def load_evals(self, pattern: str = "**/*.yaml") -> None:
        """Discover and parse eval definitions.
        
        Args:
            pattern: Glob pattern for finding YAML files
        """
        yaml_files = list(self.registry_path.glob(pattern))
        logger.info(f"Found {len(yaml_files)} YAML files in {self.registry_path}")
        
        # First pass: load all raw configs
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    configs = yaml.safe_load(f)
                    
                if configs:
                    logger.info(f"Loading configs from {yaml_file}")
                    for eval_id, config in configs.items():
                        if eval_id in self._raw_configs:
                            logger.warning(f"Duplicate eval ID {eval_id}, overwriting")
                        self._raw_configs[eval_id] = config
                        
            except Exception as e:
                logger.error(f"Error loading {yaml_file}: {e}")
        
        # Second pass: resolve inheritance
        for eval_id in self._raw_configs:
            if eval_id not in self.evals:
                self._resolve_eval(eval_id)
                
        logger.info(f"Loaded {len(self.evals)} eval configurations")
        
    def _resolve_eval(self, eval_id: str) -> Dict[str, Any]:
        """Resolve a single eval with inheritance.
        
        Args:
            eval_id: ID of the eval to resolve
            
        Returns:
            Resolved eval configuration
        """
        if eval_id in self.evals:
            return self.evals[eval_id]
            
        if eval_id not in self._raw_configs:
            raise ValueError(f"Unknown eval ID: {eval_id}")
            
        config = self._raw_configs[eval_id].copy()
        
        # Resolve parent if specified
        if 'parent' in config and config['parent']:
            parent_id = config['parent']
            parent_config = self._resolve_eval(parent_id)
            
            # Merge parent config with child config
            merged_config = self._merge_configs(parent_config, config)
            config = merged_config
            
        # Set the ID if not present
        config['id'] = eval_id
        
        # Store resolved config
        self.evals[eval_id] = config
        return config
        
    def _merge_configs(self, parent: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
        """Merge parent and child configurations.
        
        Child values override parent values. For 'args' dicts, we do a deep merge.
        
        Args:
            parent: Parent configuration
            child: Child configuration
            
        Returns:
            Merged configuration
        """
        merged = parent.copy()
        
        for key, value in child.items():
            if key == 'args' and key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Deep merge args
                merged[key] = {**merged[key], **value}
            else:
                # Override parent value
                merged[key] = value
                
        return merged
        
    def get_eval(self, eval_id: str) -> EvalConfig:
        """Get a resolved eval configuration.
        
        Args:
            eval_id: ID of the eval to get
            
        Returns:
            EvalConfig object
            
        Raises:
            ValueError: If eval_id is not found
        """
        if eval_id not in self.evals:
            if eval_id in self._raw_configs:
                self._resolve_eval(eval_id)
            else:
                raise ValueError(f"Unknown eval ID: {eval_id}")
                
        config = self.evals[eval_id]
        
        return EvalConfig(
            id=eval_id,
            description=config.get('description', ''),
            eval_class=config.get('class', ''),
            args=config.get('args', {}),
            parent=config.get('parent'),
            dataset=config.get('dataset')
        )
        
    def list_evals(self) -> List[str]:
        """List all available eval IDs.
        
        Returns:
            List of eval IDs
        """
        return list(self.evals.keys())
        
    def get_evals_by_class(self, class_name: str) -> List[str]:
        """Get all evals using a specific class.
        
        Args:
            class_name: Full class name (e.g., 'evals.base.ExactMatch')
            
        Returns:
            List of eval IDs using that class
        """
        matching_evals = []
        for eval_id, config in self.evals.items():
            if config.get('class') == class_name:
                matching_evals.append(eval_id)
        return matching_evals