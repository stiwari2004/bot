"""
Response compression middleware
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from typing import Callable
import gzip
import json
from io import BytesIO
from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum response size to compress (bytes)
MIN_COMPRESS_SIZE = 500

# Content types that should be compressed
COMPRESSIBLE_TYPES = {
    "application/json",
    "application/javascript",
    "text/html",
    "text/css",
    "text/plain",
    "text/xml",
    "application/xml",
}


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to compress HTTP responses using gzip
    
    Compresses responses that:
    - Are larger than MIN_COMPRESS_SIZE bytes
    - Have compressible content types
    - Client accepts gzip encoding
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        supports_gzip = "gzip" in accept_encoding.lower()
        
        if not supports_gzip:
            # Client doesn't support gzip, skip compression
            return await call_next(request)
        
        # Get response
        response = await call_next(request)
        
        # Skip compression for certain status codes
        if response.status_code in (204, 304):
            return response
        
        # Skip compression for streaming responses
        if isinstance(response, StreamingResponse):
            return response
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        base_content_type = content_type.split(";")[0].strip().lower()
        
        if base_content_type not in COMPRESSIBLE_TYPES:
            return response
        
        # Get response body
        body = b""
        if hasattr(response, "body"):
            body = response.body
        elif hasattr(response, "render"):
            # For template responses, we'd need to render first
            # For now, skip compression for these
            return response
        
        # Check minimum size
        if len(body) < MIN_COMPRESS_SIZE:
            return response
        
        # Compress body
        try:
            compressed_body = BytesIO()
            with gzip.GzipFile(fileobj=compressed_body, mode="wb") as gz:
                gz.write(body)
            compressed_body.seek(0)
            compressed_data = compressed_body.read()
            
            # Only use compressed version if it's actually smaller
            if len(compressed_data) < len(body):
                # Create new response with compressed body
                compressed_response = Response(
                    content=compressed_data,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                compressed_response.headers["content-encoding"] = "gzip"
                compressed_response.headers["content-length"] = str(len(compressed_data))
                
                logger.debug(
                    f"Compressed response: {len(body)} -> {len(compressed_data)} bytes "
                    f"({100 * (1 - len(compressed_data) / len(body)):.1f}% reduction)"
                )
                return compressed_response
        except Exception as e:
            logger.warning(f"Failed to compress response: {e}")
            # Return original response if compression fails
            return response
        
        return response
