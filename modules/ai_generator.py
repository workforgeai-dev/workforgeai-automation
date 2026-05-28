import httpx
from modules.utils import load_config

class OllamaClient:
    def __init__(self):
        cfg = load_config()
        ollama_cfg = cfg.get('ollama', {})
        self.base_url = ollama_cfg.get('base_url', 'http://localhost:11434')
        self.model = ollama_cfg.get('model', 'qwen2.5:3b')
        self.timeout = ollama_cfg.get('timeout', 600)

    def _chat(self, prompt):
        r = httpx.post(
            f'{self.base_url}/api/chat',
            json={'model': self.model, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()['message']['content']

    def health_check(self):
        try:
            r = httpx.get(f'{self.base_url}/api/tags', timeout=5)
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
