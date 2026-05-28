import httpx
import re
from modules import utils
from modules.utils import load_config


class WordPressClient:
    def __init__(self, wp_url, username, app_password):
        self.api_base = f"{wp_url}/wp-json/wp/v2"
        self.auth = (username, app_password)
        self.timeout = 30

    def _post(self, endpoint, data):
        r = httpx.post(
            f"{self.api_base}/{endpoint}",
            json=data,
            auth=self.auth,
            timeout=self.timeout,
        )
        if r.status_code in (200, 201):
            return r.json()
        raise Exception(f"WP API error [{endpoint}]: {r.status_code} - {r.text}")

    def _get(self, endpoint, params=None):
        r = httpx.get(
            f"{self.api_base}/{endpoint}",
            params=params,
            auth=self.auth,
            timeout=self.timeout,
        )
        if r.status_code == 200:
            return r.json()
        raise Exception(f"WP API GET error [{endpoint}]: {r.status_code}")

    def parse_article_response(self, raw_response):
        meta_match = re.search(r'<!-- meta:\s*(.+?)-->', raw_response)
        meta_description = meta_match.group(1).strip() if meta_match else ""

        article_match = re.search(r'<article>(.*?)</article>', raw_response, re.DOTALL)
        if not article_match:
            article_match = re.search(r'<body>(.*?)</body>', raw_response, re.DOTALL)

        content = article_match.group(1).strip() if article_match else raw_response.strip()
        return meta_description, content

    def create_post(self, title, content, meta_description="", categories=None, tags=None, status="draft"):
        data = {
            "title": title,
            "content": content,
            "status": status,
        }
        if meta_description:
            data["meta"] = {"_aioseo_description": meta_description}
        if categories:
            cat_ids = []
            for cat_name in categories:
                try:
                    existing = self._get("categories", {"search": cat_name})
                    if existing:
                        cat_ids.append(existing[0]["id"])
                except Exception:
                    pass
            if cat_ids:
                data["categories"] = cat_ids
        return self._post("posts", data)

    def check_health(self):
        try:
            r = httpx.get(self.api_base, auth=self.auth, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def get_existing_products(self):
        try:
            return self._get("products", {"per_page": 100})
        except Exception:
            return []

    def create_product(self, name, description, price, download_url, categories=None):
        data = {
            "name": name,
            "description": description,
            "regular_price": str(price),
            "type": "simple",
            "virtual": True,
            "downloadable": True,
            "downloads": [
                {"name": f"{name}.zip", "file": download_url}
            ],
            "stock_status": "instock",
        }
        if categories:
            data["categories"] = [{"name": c} for c in categories]
        return self._post("products", data)
