import httpx
from modules import utils
from modules.utils import load_config


class NEXUSClient:
    def __init__(self):
        cfg = load_config()
        self.base_url = cfg["nexus"]["api_url"]
        self.api_key = cfg.get("nexus", {}).get("api_key", "")
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
        self.timeout = 120

    def _api_url(self, path):
        return f"{self.base_url}{path}"

    def health_check(self):
        try:
            r = httpx.get(self._api_url("/health"), headers=self.headers, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def _post(self, path, data):
        r = httpx.post(
            self._api_url(path),
            json=data,
            headers=self.headers,
            timeout=self.timeout,
        )
        if r.status_code == 200:
            return r.json()
        raise Exception(f"NEXUS API error: {r.status_code} - {r.text}")

    def generate_article(self, topic, keywords, language="en", word_count=1500):
        lang_instruction = (
            "Write in Portuguese from Portugal (use European Portuguese)."
            if language == "pt"
            else "Write in English."
        )
        prompt = f"""You are a professional tech blogger for WorkForgeAI.com.
Write a comprehensive blog article about: {topic}

{lang_instruction}

Requirements:
- Minimum {word_count} words
- 4-6 H2 section headings
- Include introduction and conclusion
- Natural SEO keyword placement for: {', '.join(keywords)}
- Include 2-3 internal CTAs linking to WorkForgeAI products
- Professional but accessible tone for developers and tech entrepreneurs
- No markdown code blocks - just plain HTML paragraphs with <h2> and <p> tags
- Meta description (max 160 chars) at the start, wrapped in <!-- meta: -->

Format the output as:
<!-- meta: META DESCRIPTION HERE -->
<article>
HTML content here...
</article>"""

        result = self._post("/v2/chat", {"message": prompt, "model": "nexus-omni", "stream": False})
        return result.get("response", "")

    def generate_social_post(self, article_text, platform, language="en"):
        platform_instructions = {
            "twitter": "Write a thread of 5 tweets (each <280 chars). Format as: 1/5 ... 2/5 ...",
            "facebook": "Write a single engaging Facebook post (150-300 chars) with a call to action.",
            "linkedin": "Write a professional LinkedIn post (200-400 chars) with hashtags.",
        }
        instruction = platform_instructions.get(platform, "Write a short social media post.")
        prompt = f"""Based on this article, {instruction}
Language: {'English' if language == 'en' else 'Portuguese from Portugal'}
Article: {utils.truncate_text(article_text, 3000)}"""

        result = self._post("/v2/chat", {"message": prompt, "model": "nexus-omni", "stream": False})
        return result.get("response", "")
