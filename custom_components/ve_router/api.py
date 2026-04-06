class VERouterApi:
    def __init__(self, session, host):
        self._session = session
        self._host = host

    async def async_test_connection(self):
        url = f"http://{self._host}/data"
        async with self._session.get(url, timeout=5) as resp:
            return await resp.json()
