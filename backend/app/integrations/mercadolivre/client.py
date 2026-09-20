"""Mercado Livre endpoints verified against official documentation (see docs)."""
from datetime import datetime, timedelta, timezone
import asyncio
from urllib.parse import urlencode
import httpx
import simplejson
from fastapi import HTTPException
from app.core.config import settings

AUTH_URL_MLB = "https://auth.mercadolivre.com.br/authorization"
API_BASE_URL = "https://api.mercadolibre.com"


class MercadoLivreClient:
    def __init__(self, app_id=None, client_secret=None, redirect_uri=None):
        self._http_client = None
        self.app_id = app_id or settings.MERCADOLIVRE_APP_ID
        self.client_secret = client_secret or settings.MERCADOLIVRE_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.MERCADOLIVRE_REDIRECT_URI

    async def close(self):
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def is_configured(self):
        return bool(self.app_id and self.client_secret and self.redirect_uri)

    def get_authorization_url(self, state: str):
        if not self.is_configured():
            raise HTTPException(503, "Mercado Livre não está configurado no servidor.")
        return AUTH_URL_MLB + "?" + urlencode({"response_type": "code", "client_id": self.app_id, "redirect_uri": self.redirect_uri, "state": state})

    async def _request(self, method, path, access_token=None, payload=None, form=None, files=None):
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
        options = {}
        if payload is not None:
            headers["Content-Type"] = "application/json"
            options["content"] = simplejson.dumps(payload, use_decimal=True, allow_nan=False).encode()
        if form is not None:
            options["data"] = form
        if files is not None:
            options["files"] = files
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))
        for attempt in range(3 if method == "GET" else 1):
            try:
                response = await self._http_client.request(method, API_BASE_URL + path, headers=headers, **options)
            except (httpx.TimeoutException, httpx.NetworkError):
                if method != "GET" or attempt == 2:
                    raise HTTPException(503, "Não foi possível acessar o Mercado Livre. Tente novamente; em uma autorização, reinicie pelo botão Autorizar conta.") from None
                await asyncio.sleep(0.5 * (2 ** attempt))
                continue
            if method == "GET" and response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                await asyncio.sleep(0.5 * (2 ** attempt))
                continue
            break
        if response.status_code >= 400:
            # Do not forward remote response text: it can contain request credentials.
            code = 401 if response.status_code in (401, 403) else 422 if response.status_code == 400 else 502
            raise HTTPException(code, f"Mercado Livre recusou a operação (HTTP {response.status_code}). Revise os dados ou reconecte a conta.")
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return simplejson.loads(response.content, use_decimal=True)
        except ValueError:
            raise HTTPException(502, "Resposta inválida do Mercado Livre.")

    async def _token(self, fields):
        if not self.is_configured():
            raise HTTPException(503, "Mercado Livre não está configurado no servidor.")
        data = await self._request("POST", "/oauth/token", form={"client_id": self.app_id, "client_secret": self.client_secret, **fields})
        if not all(data.get(key) for key in ("access_token", "refresh_token", "expires_in", "user_id")):
            raise HTTPException(502, "Resposta de autenticação incompleta.")
        if not isinstance(data["expires_in"], int) or data["expires_in"] <= 0:
            raise HTTPException(502, "Validade de autenticação inválida.")
        data["token_expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
        return data

    async def exchange_code_for_token(self, code):
        return await self._token({"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri})

    async def refresh_access_token(self, refresh_token):
        return await self._token({"grant_type": "refresh_token", "refresh_token": refresh_token})

    async def get_user_info(self, access_token):
        return await self._request("GET", "/users/me", access_token)

    async def predict_category(self, title, access_token):
        return await self._request("GET", "/sites/MLB/domain_discovery/search?" + urlencode({"limit": 4, "q": title}), access_token)

    async def get_category_attributes(self, category_id, access_token):
        return await self._request("GET", f"/categories/{category_id}/attributes", access_token)

    async def upload_picture(self, data, filename, access_token):
        result = await self._request("POST", "/pictures/items/upload", access_token, files={"file": (filename, data)})
        if not result.get("id"):
            raise HTTPException(502, "Imagem não confirmada pelo Mercado Livre.")
        return result["id"]

    async def validate_item(self, item_data, access_token):
        await self._request("POST", "/items/validate", access_token, payload=item_data)
        return {"valid": True}

    async def publish_item(self, item_data, access_token):
        return await self._request("POST", "/items", access_token, payload=item_data)

    async def set_description(self, item_id, description, access_token):
        return await self._request("POST", f"/items/{item_id}/description", access_token, payload={"plain_text": description})

    async def get_item(self, item_id, access_token):
        return await self._request("GET", f"/items/{item_id}", access_token)

    async def update_item(self, item_id, item_data, access_token):
        return await self._request("PUT", f"/items/{item_id}", access_token, payload=item_data)
