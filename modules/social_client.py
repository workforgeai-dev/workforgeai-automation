import httpx
import json
import re
from modules import utils
from modules.utils import load_config


class SocialClient:
    def __init__(self):
        cfg = load_config()
        self.config = cfg["social"]

    def post_to_twitter(self, thread_text):
        if not self.config.get("twitter", {}).get("enabled"):
            utils.log("social", "Twitter disabled", "SKIP")
            return False
        tweets = re.findall(r'\d+/\d+[ªº]?\s*(.+?)(?=\d+/\d+|\Z)', thread_text, re.DOTALL)
        if not tweets:
            tweets = [t.strip() for t in thread_text.split("\n\n") if t.strip()]
        for i, tweet in enumerate(tweets):
            tweet = tweet.strip()[:280]
            if not tweet:
                continue
            utils.log("twitter", f"Tweet {i+1}/{len(tweets)}: {utils.truncate_text(tweet)}")
            # TODO: integrate Twitter API v2 with OAuth tokens
            # api.create_tweet(text=tweet)
        return True

    def post_to_facebook(self, content, link=None):
        if not self.config.get("facebook", {}).get("enabled"):
            utils.log("social", "Facebook disabled", "SKIP")
            return False
        utils.log("facebook", f"Post: {utils.truncate_text(content)}")
        # TODO: Facebook Graph API
        return True

    def post_to_instagram(self, image_url, caption):
        if not self.config.get("instagram", {}).get("enabled"):
            utils.log("social", "Instagram disabled", "SKIP")
            return False
        utils.log("instagram", f"Caption: {utils.truncate_text(caption)}")
        # TODO: Instagram Business API
        return True

    def post_to_tiktok(self, video_url, description):
        if not self.config.get("tiktok", {}).get("enabled"):
            utils.log("social", "TikTok disabled", "SKIP")
            return False
        utils.log("tiktok", f"Video: {video_url}, Desc: {utils.truncate_text(description)}")
        # TODO: TikTok API
        return True

    def post_to_youtube(self, video_url, title, description):
        if not self.config.get("youtube", {}).get("enabled"):
            utils.log("social", "YouTube disabled", "SKIP")
            return False
        utils.log("youtube", f"Video: {title}")
        # TODO: YouTube Data API v3
        return True

    def cross_post(self, article_title, article_excerpt, platform, post_content):
        utils.log("social", f"Cross-posting to {platform}")
        if platform == "twitter":
            return self.post_to_twitter(post_content)
        elif platform == "facebook":
            return self.post_to_facebook(post_content, link=article_title)
        elif platform == "instagram":
            return self.post_to_instagram(None, post_content)
        elif platform == "tiktok":
            return self.post_to_tiktok(None, post_content)
        elif platform == "youtube":
            return self.post_to_youtube(None, article_title, post_content)
        utils.log("social", f"Unknown platform: {platform}", "WARN")
        return False
