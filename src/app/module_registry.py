# =============================================================
# src/app/module_registry.py
# Central module registration and orchestration
# =============================================================

"""
Module Registry - Central hub for registering and running analytical modules.

This file registers all available modules with the AgentRegistry.
To add a new module:
1. Create the module folder in src/app/{module_name}/
2. Implement the required files (models, metrics, rules, llm, orchestrator)
3. Add the module configuration to agents_config.yaml
4. Register the module runner here

Example:
    from src.app.my_new_module import run_my_module
    AgentRegistry.register("my_module", runner=run_my_module)
"""

from src.app.base.base_agent import AgentRegistry, register_runner

# Import module runners
from src.app.borrowing_module.debt_orchestrator import run_borrowings_module
from src.app.equity_funding_module.equity_orchestrator import run_equity_funding_module


# =============================================================
# REGISTER ALL MODULES
# =============================================================

def initialize_registry():
    """
    Initialize the agent registry with all available modules.
    Call this at application startup.
    """
    # Register Borrowings Module
    AgentRegistry.register(
        module_key="borrowings",
        runner=run_borrowings_module
    )
    
    # Register Equity & Funding Mix Module
    AgentRegistry.register(
        module_key="equity_funding_mix",
        runner=run_equity_funding_module
    )
    
    # =========================================================
    # ADD NEW MODULES HERE
    # =========================================================
    # Example:
    # from src.app.liquidity_module import run_liquidity_module
    # AgentRegistry.register(
    #     module_key="liquidity",
    #     runner=run_liquidity_module
    # )
    
    print(f"[Registry] Initialized with modules: {AgentRegistry.list_modules()}")


def run_module(module_key: str, input_data):
    """
    Run a specific module by its key.
    
    Args:
        module_key: The module identifier (must match YAML config)
        input_data: Module-specific input data
    
    Returns:
        Module output
    
    Raises:
        ValueError: If module is not registered
    """
    if not AgentRegistry.is_registered(module_key):
        raise ValueError(
            f"Module '{module_key}' is not registered. "
            f"Available modules: {AgentRegistry.list_modules()}"
        )
    
    return AgentRegistry.run_module(module_key, input_data)


def get_available_modules():
    """
    Get list of all available modules.
    
    Returns:
        List of module keys that are both registered and enabled in config
    """
    return AgentRegistry.get_enabled_modules()


def get_all_registered_modules():
    """
    Get all registered modules regardless of config status.
    
    Returns:
        List of all registered module keys
    """
    return AgentRegistry.list_modules()


# =============================================================
# MODULE INFO UTILITIES
# =============================================================

def get_module_info(module_key: str) -> dict:
    """
    Get information about a specific module from config.
    
    Args:
        module_key: The module identifier
    
    Returns:
        Dictionary with module metadata
    """
    from src.app.config.config_loader import get_config_loader
    
    config = get_config_loader().get_module_config(module_key)
    if not config:
        return {"error": f"Module '{module_key}' not found in config"}
    
    return {
        "key": module_key,
        "name": config.name,
        "description": config.description,
        "enabled": config.enabled,
        "agent_name": config.agent.name if config.agent else None,
        "metrics_count": len(config.per_year_metrics),
        "rules_count": len(config.rules),
        "registered": AgentRegistry.is_registered(module_key),
    }


def list_all_modules_info() -> list:
    """
    Get information about all configured modules.
    
    Returns:
        List of module info dictionaries
    """
    from src.app.config.config_loader import get_config_loader
    
    modules = get_config_loader().get_all_modules()
    return [get_module_info(key) for key in modules.keys()]
