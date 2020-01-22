import requests
from .models import Board
import multiprocessing
_LOCK = multiprocessing.Lock()

class WekanApi:
    def api_call(self, url, data=None, authed=True, params=None, delete=None):
        if data is None and params is None:
            api_response = self.session.get(
                "{}{}".format(self.api_url, url),
                headers={"Authorization": "Bearer {}".format(self.token)},
                proxies=self.proxies
            )
        else:
            # delete
            if delete:
                _LOCK.acquire( timeout=5000 )
                api_response = self.session.delete(
                    "{}{}".format(self.api_url, url),
                    data=data,
                    headers={"Authorization": "Bearer {}".format(self.token)} if authed else {},
                    proxies=self.proxies
                )
                _LOCK.release()
            # modify
            elif params:
                if data:
                    # print 1
                    _LOCK.acquire( timeout=5000 )
                    api_response = self.session.put(
                        "{}{}".format(self.api_url, url),
                        data=data,
                        headers={"Authorization": "Bearer {}".format(self.token)},
                        proxies=self.proxies
                    )
                    _LOCK.release()
                else:
                    headers = {
                      'Content-Type': 'multipart/form-data',
                      'Accept': 'application/json',
                      'Authorization': "Bearer {}".format(self.token),
                    }
                    # print 2, headers, "{}{}".format(self.api_url, url)
                    _LOCK.acquire( timeout=5000 )
                    api_response = self.session.put(
                        "{}{}".format(self.api_url, url),
                        params=params,
                        headers=headers if authed else {},
                        # proxies=self.proxies
                    )
                    _LOCK.release()
            # add
            else:
                # print 3
                _LOCK.acquire( timeout=5000 )
                api_response = self.session.post(
                    "{}{}".format(self.api_url, url),
                    data=data,
                    headers={"Authorization": "Bearer {}".format(self.token)} if authed else {},
                    proxies=self.proxies
                )
                _LOCK.release()
        return api_response.json()

    def __init__(self, api_url, credentials, proxies=None):
        if proxies is None:
            proxies = {}
        self.session = requests.Session()
        self.proxies = proxies
        self.api_url = api_url
        api_login = self.api_call("/users/login", data=credentials, authed=False)
        self.token = api_login["token"]
        self.user_id = api_login["id"]

    def get_user_boards(self, filter=''):
        boards_data = self.api_call("/api/users/{}/boards".format(self.user_id))
        return [Board(self, board_data) for board_data in boards_data if filter in board_data["title"]]
