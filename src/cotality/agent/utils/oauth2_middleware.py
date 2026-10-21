import os

import jwt
from dotenv import load_dotenv
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

load_dotenv()

AUTH_HEADER_PREFIX = "Bearer "


class OAuth2Middleware(BaseHTTPMiddleware):
    """Starlette middleware that authenticates A2A access using an OAuth2 bearer token."""

    AUTH_HEADER_PREFIX = "Bearer "
    _jwks_client: PyJWKClient | None = None

    @classmethod
    def _get_jwks_client(cls) -> PyJWKClient:
        """Lazily initialise and return the JWKS client.

        Raises:
            RuntimeError: If AGENT_AUTH0_JWK_URL is not set.
        """
        if cls._jwks_client is None:
            jwk_url = os.getenv("AGENT_AUTH0_JWK_URL")
            if not jwk_url:
                raise RuntimeError(
                    "AGENT_AUTH0_JWK_URL environment variable is required "
                    "when OAuth2 authentication is enabled"
                )
            cls._jwks_client = PyJWKClient(jwk_url)
        return cls._jwks_client

    async def dispatch(self, request: Request, call_next):
        """Intercepts incoming requests to perform OAuth2 authentication.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable): The next middleware or endpoint handler.

        Returns:
            Response: The HTTP response, either from authentication or the next handler.
        """
        public_paths = ["/health", "/.well-known/agent-card.json"]
        print(request.url.path)
        if request.url.path in public_paths or os.getenv("ENABLE_AGENT_AUTH0").__eq__("False"):
            return await call_next(request)

        try:
            print(f"Headers received: {request.headers}")
            is_valid = await self.verify_token(request)

            if not is_valid:
                return self._unauthorized("Token verification failed", request)

        except (jwt.InvalidTokenError, RuntimeError, ValueError, TypeError) as e:
            print(f"An unexpected error occured during token verification: {e}")
            return self._unauthorized(f"Token verification error: {e}", request)

        response = await call_next(request)
        print(f"Response status: {response.status_code}")
        return response

    def _forbidden(self, reason: str, request: Request):
        """Returns a forbidden response.

        Args:
            reason (str): Reason for the forbidden response.
            request (Request): The incoming HTTP request.

        Returns:
            Response: A 403 Forbidden response.
        """
        accept_header = request.headers.get("accept", "")
        if "text/event-stream" in accept_header:
            return PlainTextResponse(
                f"error forbidden: {reason}", status_code=403, media_type="text/event-stream"
            )
        return JSONResponse({"error": "forbidden", "reason": reason}, status_code=403)

    def _unauthorized(self, reason: str, request: Request):
        """Returns an unauthorized response.

        Args:
            reason (str): Reason for the unauthorized response.
            request (Request): The incoming HTTP request.

        Returns:
            Response: A 401 Unauthorized response.
        """
        accept_header = request.headers.get("accept", "")
        if "text/event-stream" in accept_header:
            return PlainTextResponse(
                f"error unauthorized: {reason}", status_code=401, media_type="text/event-stream"
            )
        return JSONResponse({"error": "unauthorized", "reason": reason}, status_code=401)

    async def verify_token(self, request: Request) -> bool:
        """Verifies that the request contains the OAuth2 bearer token.

        Args:
            request (Request): The incoming HTTP request.

        Returns:
            bool: True if the token is valid, False otherwise.
        """
        print("Verifying token")
        auth_header = request.headers.get("Authorization")
        print(f"Auth Header: {'present' if auth_header else 'missing'}")
        if not auth_header or not auth_header.startswith(AUTH_HEADER_PREFIX):
            print("Invalid authorization header")
            return False

        token = auth_header[len(AUTH_HEADER_PREFIX) :]
        signing_key = self._get_jwks_client().get_signing_key_from_jwt(token)

        _ = jwt.decode(
            token,
            signing_key,
            audience=os.getenv("AGENT_AUTH0_AUDIENCE"),
            issuer=os.getenv("AGENT_AUTH0_ISSUER"),
            algorithms=["RS256"],
        )

        return True
