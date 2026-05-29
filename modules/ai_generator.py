import httpx
from modules.utils import load_config, log


class OllamaClient:
    def __init__(self):
        cfg = load_config()
        self.nexus_cfg = cfg.get('nexus', {})
        self.ollama_cfg = cfg.get('ollama', {})
        self.remote_url = self.nexus_cfg.get('api_url', 'http://192.168.1.116:8000')
        self.remote_model = self.nexus_cfg.get('model', 'nexus-omni')
        self.local_url = self.ollama_cfg.get('base_url', 'http://localhost:11434')
        self.local_model = self.ollama_cfg.get('model', 'qwen2.5:3b')
        self.timeout = self.ollama_cfg.get('timeout', 600)
        self.use_remote = False
        self._check_remote()

    def _check_remote(self):
        try:
            r = httpx.get(f'http://192.168.1.116:11434/api/tags', timeout=5)
            if r.status_code == 200:
                self.use_remote = True
                log('ai', f'Using UM790 Ollama ({self.remote_model})')
            else:
                log('ai', 'UM790 Ollama unhealthy, using local', 'WARN')
        except Exception:
            self.use_remote = False
            log('ai', 'UM790 unreachable, using local Ollama', 'WARN')

    def _chat_remote(self, prompt):
        r = httpx.post(
            f'http://192.168.1.116:11434/api/chat',
            json={'model': self.remote_model, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()['message']['content']

    def _chat_local(self, prompt):
        r = httpx.post(
            f'{self.local_url}/api/chat',
            json={'model': self.local_model, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()['message']['content']

    def _chat(self, prompt):
        if self.use_remote:
            try:
                return self._chat_remote(prompt)
            except Exception as e:
                log('ai', f'Remote failed: {e}, falling back to local', 'WARN')
                self.use_remote = False
        return self._chat_local(prompt)

    def health_check(self):
        if self.use_remote:
            try:
                r = httpx.get(f'http://192.168.1.116:11434/api/tags', timeout=5)
                return r.status_code == 200
            except Exception:
                pass
        try:
            r = httpx.get(f'{self.local_url}/api/tags', timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def generate_article(self, topic, keywords, language='en', word_count=1500):
        lang_instruction = 'Write in Portuguese from Portugal (use European Portuguese).' if language == 'pt' else 'Write in English.'
        keywords_str = ', '.join(keywords)
        prompt = f'''You are a professional tech blogger for WorkForgeAI.com.
Write a comprehensive blog article about: {topic}

{lang_instruction}

Requirements:
- Minimum {word_count} words
- 4-6 H2 section headings (use actual <h2> tags)
- Include introduction and conclusion
- Natural SEO keyword placement for: {keywords_str}
- Include 2-3 internal CTAs linking to WorkForgeAI products
- Professional but accessible tone for developers and tech entrepreneurs
- Use ONLY clean HTML with <h2> and <p> tags
- CRITICAL: Do NOT output markdown code blocks, backticks, or HTML entities like &lt; &gt; &quot;
- CRITICAL: Do NOT wrap output in <!DOCTYPE html> or <html> tags
- CRITICAL: Do NOT use &#8220; or any HTML entity codes - use actual characters
- Meta description (max 160 chars) at the start, wrapped in <!-- meta: -->

Format EXACTLY:
<!-- meta: META DESCRIPTION HERE -->
<article>
HTML content here with <h2> and <p> only
</article>'''
        return self._chat(prompt)

    def generate_social_post(self, article_text, platform, language='en'):
        platform_instructions = {
            'twitter': 'Write a thread of 5 tweets. Separate each tweet with --- on its own line. Each tweet must be under 280 characters.',
            'facebook': 'Write a single engaging Facebook post (150-300 chars) with a call to action.',
            'linkedin': 'Write a professional LinkedIn post (200-400 chars) with hashtags.',
        }
        instruction = platform_instructions.get(platform, 'Write a short social media post.')
        prompt = f'''Based on this article, {instruction}
Language: {'English' if language == 'en' else 'Portuguese from Portugal'}
Article: {article_text[:3000]}'''
        return self._chat(prompt)

    def generate(self, prompt):
        return self._chat(prompt)
