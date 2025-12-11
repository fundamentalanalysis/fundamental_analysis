"""
AWS Lambda handler for FastAPI application using Mangum adapter.
This file wraps the FastAPI app for AWS Lambda compatibility.
"""

from mangum import Mangum
from src.main import app

# Mangum adapter for AWS Lambda
# lifespan="off" disables ASGI lifespan events (startup/shutdown)
# which are not supported in Lambda
handler = Mangum(app, lifespan="off")