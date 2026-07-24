import requests
from typing import Any, Dict

class InsRestApiClient:
    _API_PREFIX: str = "/api/v1"
    _DEFAULT_HEADERS: Dict[str, str] = {"Accept": "application/json"}
    _REQUEST_TIMEOUT_SECONDS: float = 5.0

    def __init__(self, ip_address: str, port: int = 80):
        self._base_url = f"http://{ip_address}:{port}"

    def fetch_data(self) -> Dict[str, Any]:
        ins_data = {}
        try:
            ins_data['status'] = self._get_json("status")
            ins_data['ins_measurement'] = self._get_json("data")
            ins_data['online'] = True
        except requests.RequestException as exc:
            ins_data['online'] = False
            ins_data['error_message'] = str(exc)
        else:
            try:
                ins_data['gnss1_measurement'] = self._get_json("gnss1")
            except requests.RequestException as exc:
                ins_data['gnss1_measurement'] = None
            
            try:
                ins_data['gnss2_measurement'] = self._get_json("gnss2")
            except requests.RequestException as exc:
                ins_data['gnss2_measurement'] = None
            
            try:
                ins_data['datalogger'] = self._get_json("dataLogger")
            except requests.RequestException as exc:
                ins_data['datalogger'] = None
            
        return ins_data

    def reboot(self) -> None:
        self._post("system/reboot")

    def start_data_logger(self) -> None:
        self._post("dataLogger/start")

    def stop_data_logger(self) -> None:
        self._post("dataLogger/stop")

    def _build_url(self, path: str) -> str:
        return f"{self._base_url}{self._API_PREFIX}/{path}"

    def _get_json(self, path: str) -> Dict[str, Any]:
        url = self._build_url(path)
        response = requests.get(url, headers=self._DEFAULT_HEADERS, timeout=self._REQUEST_TIMEOUT_SECONDS)
        self._raise_for_status(response)
        return response.json()

    def _post(self, path: str) -> None:
        url = self._build_url(path)
        response = requests.post(url, headers=self._DEFAULT_HEADERS, json={}, timeout=self._REQUEST_TIMEOUT_SECONDS)
        self._raise_for_status(response)

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.ok:
            return

        try:
            problem = response.json()
        except ValueError:
            problem = None

        if isinstance(problem, dict) and ('title' in problem or 'detail' in problem):
            message = f"{response.status_code} {problem.get('title', '')}: {problem.get('detail', '')}".strip()
            raise requests.HTTPError(message, response=response)

        response.raise_for_status()
