import httpx
import json
import re
import time
import hashlib
import hmac
import base64
import uuid
import urllib.parse
from modules import utils
from modules.utils import load_config


class SocialClient:
    def __init__(self):
        cfg = load_config()
        self.config = cfg.get("social", {})
        self.affiliates = self.config.get("affiliates", {})
        self.twitter_cfg = self.config.get("twitter", {})
        self.facebook_cfg = self.config.get("facebook", {})
        self.instagram_cfg = self.config.get("instagram", {})
        self.tiktok_cfg = self.config.get("tiktok", {})
        self.youtube_cfg = self.config.get("youtube", {})
        self.linkedin_cfg = self.config.get("linkedin", {})
        self.http = httpx.Client(timeout=60.0, follow_redirects=True)

    # ------------------------------------------------------------------
    #  Affiliate link injection
    # ------------------------------------------------------------------

    def inject_affiliate_links(self, content):
        if not self.affiliates:
            return content
        for keyword, url in self.affiliates.items():
            if not keyword or not url:
                continue
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            replacement = f'<a href="{url}">{keyword}</a>'
            content = pattern.sub(replacement, content)
        return content

    # ------------------------------------------------------------------
    #  OAuth 1.0a signature helper  (Twitter/X)
    # ------------------------------------------------------------------

    @staticmethod
    def _oauth1_sign(method, url, consumer_key, consumer_secret, token, token_secret):
        nonce = base64.b64encode(uuid.uuid4().bytes).decode().strip("=")
        ts = str(int(time.time()))
        oauth = {
            "oauth_consumer_key": consumer_key,
            "oauth_nonce": nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": ts,
            "oauth_token": token,
            "oauth_version": "1.0",
        }
        encoded = sorted(
            (urllib.parse.quote(k, safe="~"), urllib.parse.quote(str(v), safe="~"))
            for k, v in oauth.items()
        )
        ps = "&".join(f"{k}={v}" for k, v in encoded)
        base_str = (
            f"{method.upper()}&"
            f"{urllib.parse.quote(url, safe='~')}&"
            f"{urllib.parse.quote(ps, safe='~')}"
        )
        signing_key = (
            f"{urllib.parse.quote(consumer_secret, safe='~')}&"
            f"{urllib.parse.quote(token_secret, safe='~')}"
        )
        signature = base64.b64encode(
            hmac.new(signing_key.encode(), base_str.encode(), hashlib.sha1).digest()
        ).decode()
        oauth["oauth_signature"] = signature
        header = "OAuth " + ", ".join(
            f'{urllib.parse.quote(k, safe="~")}="{urllib.parse.quote(str(v), safe="~")}"'
            for k, v in sorted(oauth.items())
        )
        return header

    # ------------------------------------------------------------------
    #  Twitter / X  API v2  (OAuth 2.0 Bearer or OAuth 1.0a User Context)
    # ------------------------------------------------------------------

    def post_to_twitter(self, thread_text):
        if not self.twitter_cfg.get("enabled", False):
            utils.log("social", "Twitter disabled", "SKIP")
            return False

        api_key = (self.twitter_cfg.get("api_key") or "").strip()
        api_secret = (self.twitter_cfg.get("api_secret") or "").strip()
        bearer_token = (self.twitter_cfg.get("bearer_token") or "").strip()
        access_token = (self.twitter_cfg.get("access_token") or "").strip()
        access_secret = (self.twitter_cfg.get("access_secret") or "").strip()

        use_oauth1 = bool(api_key and api_secret and access_token and access_secret)
        if not bearer_token and not use_oauth1:
            utils.log("twitter", "Twitter API credentials not configured", "WARN")
            return False

        tweets = [t.strip() for t in thread_text.split("---") if t.strip()]
        if not tweets:
            utils.log("twitter", "No tweet content found", "WARN")
            return False

        prev_id = None
        for i, text in enumerate(tweets):
            text = text[:280]
            if not text:
                continue
            payload = {"text": text}
            if prev_id:
                payload["reply"] = {"in_reply_to_tweet_id": prev_id}

            try:
                if use_oauth1:
                    auth = self._oauth1_sign(
                        "POST", "https://api.twitter.com/2/tweets",
                        api_key, api_secret, access_token, access_secret,
                    )
                    headers = {"Authorization": auth, "Content-Type": "application/json"}
                else:
                    headers = {
                        "Authorization": f"Bearer {bearer_token}",
                        "Content-Type": "application/json",
                    }

                r = self.http.post(
                    "https://api.twitter.com/2/tweets", json=payload, headers=headers
                )
                if r.status_code in (200, 201):
                    data = r.json()
                    tid = data.get("data", {}).get("id")
                    if tid:
                        prev_id = tid
                    utils.log("twitter", f"Posted tweet {i+1}/{len(tweets)} (id={tid})")
                else:
                    utils.log(
                        "twitter",
                        f"Failed tweet {i+1}: {r.status_code} {r.text[:200]}",
                        "ERROR",
                    )
                    return False
            except Exception as e:
                utils.log("twitter", f"Exception posting tweet {i+1}: {e}", "ERROR")
                return False
        return True

    # ------------------------------------------------------------------
    #  Facebook  Graph API
    # ------------------------------------------------------------------

    def post_to_facebook(self, content, link=None):
        if not self.facebook_cfg.get("enabled", False):
            utils.log("social", "Facebook disabled", "SKIP")
            return False

        page_id = (self.facebook_cfg.get("page_id") or "").strip()
        access_token = (self.facebook_cfg.get("access_token") or "").strip()
        if not page_id or not access_token:
            utils.log("facebook", "Facebook API credentials not configured", "WARN")
            return False

        url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
        payload = {"message": content, "access_token": access_token}
        if link:
            payload["link"] = link

        try:
            r = self.http.post(url, data=payload)
            data = r.json()
            if r.status_code == 200 and "id" in data:
                utils.log("facebook", f"Posted to page {page_id} (id={data['id']})")
                return True
            err = data.get("error", {}).get("message", r.text[:200])
            utils.log("facebook", f"Failed: {err}", "ERROR")
            return False
        except Exception as e:
            utils.log("facebook", f"Exception: {e}", "ERROR")
            return False

    # ------------------------------------------------------------------
    #  Instagram  Graph API  (Business / Creator)
    # ------------------------------------------------------------------

    def post_to_instagram(self, image_url, caption):
        if not self.instagram_cfg.get("enabled", False):
            utils.log("social", "Instagram disabled", "SKIP")
            return False

        account_id = (self.instagram_cfg.get("business_account_id") or "").strip()
        access_token = (self.instagram_cfg.get("access_token") or "").strip()
        if not account_id or not access_token:
            utils.log("instagram", "Instagram API credentials not configured", "WARN")
            return False
        if not image_url:
            utils.log("instagram", "No image URL provided", "WARN")
            return False

        base = "https://graph.facebook.com/v19.0"
        try:
            # Step 1 -- create media container
            r1 = self.http.post(
                f"{base}/{account_id}/media",
                data={
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": access_token,
                },
            )
            d1 = r1.json()
            if r1.status_code != 200 or "id" not in d1:
                err = d1.get("error", {}).get("message", r1.text[:200])
                utils.log("instagram", f"Container creation failed: {err}", "ERROR")
                return False
            container_id = d1["id"]
            utils.log("instagram", f"Container created (id={container_id})")

            # Step 2 -- publish
            r2 = self.http.post(
                f"{base}/{account_id}/media_publish",
                data={
                    "creation_id": container_id,
                    "access_token": access_token,
                },
            )
            d2 = r2.json()
            if r2.status_code == 200 and "id" in d2:
                utils.log("instagram", f"Published media (id={d2['id']})")
                return True
            err = d2.get("error", {}).get("message", r2.text[:200])
            utils.log("instagram", f"Publish failed: {err}", "ERROR")
            return False
        except Exception as e:
            utils.log("instagram", f"Exception: {e}", "ERROR")
            return False

    # ------------------------------------------------------------------
    #  TikTok  Content Posting API  (Direct Post)
    # ------------------------------------------------------------------

    def post_to_tiktok(self, video_url, description):
        if not self.tiktok_cfg.get("enabled", False):
            utils.log("social", "TikTok disabled", "SKIP")
            return False

        client_key = (self.tiktok_cfg.get("client_key") or "").strip()
        access_token = (self.tiktok_cfg.get("access_token") or "").strip()
        if not client_key or not access_token:
            utils.log("tiktok", "TikTok API credentials not configured", "WARN")
            return False
        if not video_url:
            utils.log("tiktok", "No video URL provided", "WARN")
            return False

        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": video_url,
                },
                "post_info": {
                    "title": description[:220],
                    "privacy_level": "PUBLIC",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
            }
            r = self.http.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                json=payload,
                headers=headers,
            )
            d = r.json()
            if r.status_code == 200 and d.get("data", {}).get("status_code") == 0:
                pub_id = d["data"].get("publish_id", "unknown")
                utils.log("tiktok", f"Video queued (publish_id={pub_id})")
                return True
            code = d.get("data", {}).get("status_code", r.status_code)
            utils.log("tiktok", f"Init failed: status_code={code} {r.text[:200]}", "ERROR")
            return False
        except Exception as e:
            utils.log("tiktok", f"Exception: {e}", "ERROR")
            return False

    # ------------------------------------------------------------------
    #  YouTube  Data API v3  (resumable upload protocol)
    # ------------------------------------------------------------------

    def post_to_youtube(self, video_url, title, description):
        if not self.youtube_cfg.get("enabled", False):
            utils.log("social", "YouTube disabled", "SKIP")
            return False

        refresh_token = (self.youtube_cfg.get("refresh_token") or "").strip()
        if not refresh_token:
            utils.log("youtube", "YouTube refresh_token not configured", "WARN")
            return False
        if not video_url:
            utils.log("youtube", "No video URL provided", "WARN")
            return False

        # api_key field acts as OAuth client_id; optionally add
        # youtube.client_secret to config.yaml if your OAuth client
        # requires one (web-app credentials).
        client_id = (self.youtube_cfg.get("api_key") or "").strip()
        client_secret = (self.youtube_cfg.get("client_secret") or "").strip()

        try:
            # 1 -- exchange refresh token for access token
            token_payload = {
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            if client_id:
                token_payload["client_id"] = client_id
            if client_secret:
                token_payload["client_secret"] = client_secret

            tr = self.http.post(
                "https://oauth2.googleapis.com/token", data=token_payload
            )
            if tr.status_code != 200:
                utils.log(
                    "youtube",
                    f"Token refresh failed: {tr.status_code} {tr.text[:200]}",
                    "ERROR",
                )
                return False
            access_token = tr.json()["access_token"]

            # 2 -- download video
            utils.log("youtube", f"Downloading video from {video_url}")
            vr = self.http.get(video_url)
            if vr.status_code != 200:
                utils.log("youtube", f"Failed to download video: {vr.status_code}", "ERROR")
                return False
            video_bytes = vr.content
            file_size = len(video_bytes)

            if file_size == 0:
                utils.log("youtube", "Downloaded video is empty", "ERROR")
                return False

            # 3 -- create resumable upload session
            snippet = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                },
                "status": {"privacyStatus": "public"},
            }
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(file_size),
                "X-Upload-Content-Type": "video/*",
            }
            sr = self.http.post(
                "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                json=snippet,
                headers=headers,
            )
            if sr.status_code not in (200, 201):
                utils.log(
                    "youtube",
                    f"Resumable session failed: {sr.status_code} {sr.text[:200]}",
                    "ERROR",
                )
                return False

            upload_url = sr.headers.get("Location") or sr.headers.get("location")
            if not upload_url:
                utils.log("youtube", "No Location header in resumable session response", "ERROR")
                return False

            # 4 -- upload binary data
            upload_headers = {
                "Content-Length": str(file_size),
                "Content-Type": "video/*",
            }
            ur = self.http.put(upload_url, content=video_bytes, headers=upload_headers)
            if ur.status_code in (200, 201):
                vid_data = ur.json()
                vid_id = vid_data.get("id", "unknown")
                utils.log("youtube", f"Uploaded video (id={vid_id})")
                return True
            utils.log(
                "youtube",
                f"Upload failed: {ur.status_code} {ur.text[:200]}",
                "ERROR",
            )
            return False
        except Exception as e:
            utils.log("youtube", f"Exception: {e}", "ERROR")
            return False

    # ------------------------------------------------------------------
    #  LinkedIn  API v2  (UGC Posts)
    # ------------------------------------------------------------------

    def post_to_linkedin(self, content, title=""):
        if not self.linkedin_cfg.get("enabled", False):
            utils.log("social", "LinkedIn disabled", "SKIP")
            return False

        access_token = (self.linkedin_cfg.get("access_token") or "").strip()
        org_id = (self.linkedin_cfg.get("organization_id") or "").strip()
        if not access_token or not org_id:
            utils.log("linkedin", "LinkedIn API credentials not configured", "WARN")
            return False

        author_urn = f"urn:li:organization:{org_id}"
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content[:3000]},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }
            r = self.http.post(
                "https://api.linkedin.com/v2/ugcPosts", json=payload, headers=headers
            )
            if r.status_code in (200, 201):
                post_id = r.json().get("id", "unknown")
                utils.log("linkedin", f"Posted (id={post_id})")
                return True
            utils.log(
                "linkedin",
                f"Failed: {r.status_code} {r.text[:200]}",
                "ERROR",
            )
            return False
        except Exception as e:
            utils.log("linkedin", f"Exception: {e}", "ERROR")
            return False

    # ------------------------------------------------------------------
    #  Cross-post dispatcher
    # ------------------------------------------------------------------

    def cross_post(self, article_title, article_excerpt, platform, post_content):
        utils.log("social", f"Cross-posting to {platform}")
        post_content = self.inject_affiliate_links(post_content)

        mapping = {
            "twitter": lambda: self.post_to_twitter(post_content),
            "facebook": lambda: self.post_to_facebook(post_content, link=article_title),
            "instagram": lambda: self.post_to_instagram(None, post_content),
            "tiktok": lambda: self.post_to_tiktok(None, post_content),
            "youtube": lambda: self.post_to_youtube(None, article_title, post_content),
            "linkedin": lambda: self.post_to_linkedin(post_content, article_title),
        }
        handler = mapping.get(platform)
        if handler is None:
            utils.log("social", f"Unknown platform: {platform}", "WARN")
            return False
        return handler()
