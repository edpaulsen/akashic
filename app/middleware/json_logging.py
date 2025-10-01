import json
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class JSONLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("akashic.json")
        if not self.logger.handlers:
            h = logging.StreamHandler()
            self.logger.addHandler(h)
        self.logger.setLevel(logging.INFO)

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        rid = str(uuid.uuid4())
        q = str(request.url.query)
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            dur = int((time.time() - start) * 1000)
            record = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "request_id": rid,
                "method": request.method,
                "path": request.url.path,
                "query": q,
                "status": status,
                "duration_ms": dur,
            }
            self.logger.info(json.dumps(record))
        return response
