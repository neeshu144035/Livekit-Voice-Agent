"""
Example usage of structured logging in Voice AI Platform.

This demonstrates how to replace print() statements and standard logging
with structured JSON logging throughout the application.
"""

from backend.logging_config import get_logger, LogContext

logger = get_logger("example_module")

def process_call(agent_id: int, call_id: str):
    """Example function demonstrating structured logging."""
    
    # Simple info log
    logger.info("Starting call processing", extra={"agent_id": agent_id, "call_id": call_id})
    
    # Using context manager for cross-cutting concerns
    with LogContext(agent_id=agent_id, call_id=call_id):
        logger.info("Context added automatically to all logs")
        
        # Simulate processing steps
        logger.debug("Validating caller", extra={"step": "validation"})
        logger.debug("Connecting to LLM", extra={"step": "llm_connect"})
        
        try:
            # Simulate operation that might fail
            result = perform_risky_operation()
            logger.info("Operation successful", extra={"result": result})
        except Exception as e:
            # Error with exception info
            logger.error("Operation failed", exc_info=True, extra={"retry_count": 3})
            raise
    
    logger.info("Call processing completed")

def perform_risky_operation():
    """Simulated operation that might fail."""
    return "success"

def handle_agent_update(agent_id: int, field: str, value: str):
    """Example: logging agent updates with structured data."""
    logger.info(
        "Agent field updated",
        extra={
            "agent_id": agent_id,
            "field": field,
            "value": value,
            "operation": "update_agent"
        }
    )

def fetch_external_api(url: str, timeout_ms: int):
    """Example: logging external API calls."""
    logger.info("Fetching external API", extra={"url": url, "timeout_ms": timeout_ms})
    
    try:
        # Simulate API call
        response_time = 150  # ms
        status_code = 200
        
        logger.info(
            "API response received",
            extra={
                "url": url,
                "status_code": status_code,
                "response_time_ms": response_time,
            }
        )
        return {"status": "ok"}
    except Exception as e:
        logger.exception("API call failed", extra={"url": url})
        raise

if __name__ == "__main__":
    # Example usage
    process_call(agent_id=123, call_id="call_456")
    handle_agent_update(agent_id=123, field="name", value="NewAgent")
    fetch_external_api("https://api.example.com/data", timeout_ms=5000)
