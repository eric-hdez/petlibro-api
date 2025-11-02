import aiohttp
import hashlib

from dataclasses import dataclass
from urllib.parse import urljoin

@dataclass
class PetLibroUser:
    email: str
    password: str
    
    def password_hash(self) -> str:
        return hashlib.md5(self.password.encode()).hexdigest()

    def  __str__(self) -> str:
        return f"PetLibroUser(email={self.email}, password={self.hash_password()[:8]}...)"


class PetLibroSession:
    _APPID: int = 1 # from HomeAssistance Example
    _APPSN: str = "c35772530d1041699c87fe62348507a8" # from HomeAssistance Example
    _BASEURL: str = 'https://api.us.petlibro.com'

    class ResponseCode:
        NOT_YET_LOGIN = 1009

    def __init__(self, user: PetLibroUser, region: str = 'US', timezone: str = 'America/New_York') -> None:
        self.user = user
        self.region = region
        self.timezone = timezone

        self._session = aiohttp.ClientSession()
        self._token = None
        self.headers = {
            "source": "ANDROID",
            "language": "EN",
            "timezone": timezone,
            "version": "1.3.45",
        }
    
    async def __aenter__(self) -> "PetLibroSession":
        if not self._token:
            await self._authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._session.close()

    async def _authenticate(self) -> None:
        payload = {
            "appId": self._APPID,
            "appSn": self._APPSN,
            "email": self.user.email,
            "password": self.user.password_hash(),
            "phoneBrand": '',
            "phoneSystemVersion": '',
            "country": self.region,
            "timezone": self.timezone,
            "thirdId": None,
            "type": None
        }
        headers = {
            "Content-Type": 'application/json',
            "User-Agent": 'PetLibro/1.3.45',
            "Accept": 'application/json',
            "Accept-Language": 'en-US',
            **self.headers
        }
        url = urljoin(self._BASEURL, '/member/auth/login')

        async with self._session.post(url, json=payload, headers=headers) as response:
            status = response.status
            payload = await response.json()
            if status != 200:
                raise PetLibroSessionException(f"Authentication failed with status {status}: {payload}")
            elif "token" not in payload.get("data", {}):
                raise PetLibroSessionException(f"Authentication failed: {payload}")
            
            self._token = payload["data"]["token"]
    
    async def request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = urljoin(self.__BASEURL, endpoint)
        try:
            return await self._make_request(method, url, **kwargs)
        except PetLibroAuthException:
            await self._authenticate()
            return await self._make_request(method, url, **kwargs)
    
    async def _make_request(self, method: str, url: str, **kwargs) -> dict:
        headers = kwargs.pop('headers', {})
        headers.update({
            'Authorization': f'Bearer {self._token}',
            'token': self._token,
            'Content-Type': 'application/json',
            **self.headers
        })
        
        async with self._session.request(method, url, headers=headers, **kwargs) as response:
            status = response.status
            payload = await response.json()
            if status != 200:
                raise PetLibroSessionException(f"Request to {url} failed with status {status}: {payload}")
            elif payload["code"] == PetLibroSession.ResponseCode.NOT_YET_LOGIN:
                raise PetLibroAuthException("Authentication required or token expired.")
            return payload

''' Exception Definitions '''
class PetLibroSessionException(Exception):
    pass

class PetLibroAuthException(PetLibroSessionException):
    pass