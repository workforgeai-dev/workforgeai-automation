#!/usr/bin/env python3
"""
WorkForgeAI Automation Engine - Orchestrator v3.0
100% Pi-local. Zero UM790 dependency. Telegram notifications.
"""
import sys
import json
import datetime
import argparse
from pathlib import Path
from modules import utils
from modules.utils import load_config, load_calendar, save_calendar
from modules.ai_generator import OllamaClient
from modules.wp_client import WordPressClient
from modules.social_client import SocialClient
from modules.product_builder import ProductBuilder


class Orchestrator:
    def __init__(self):
        self.cfg = load_config()
        self.nexus = OllamaClient()
        self.social = SocialClient()
        self.wp = None

        pwd_file = Path(__file__).parent / ".wp_app_pass"
        self.wp_app_password = pwd_file.read_text().strip() if pwd_file.exists() else None

    def init_wordpress(self, username, app_password):
        if app_password:
            self.wp_app_password = app_password
        if not self.wp_app_password:
            utils.log("wp", "No WordPress password available", "ERROR")
            return
        self.wp = WordPressClient(
            self.cfg["wordpress"]["url"],
            username or self.cfg["wordpress"].get("username", "workforgeai@gmail.com"),
            self.wp_app_password,
        )

    def _notify(self, message):
        self.nexus.send_telegram(message)

    def check_health(self):
        results = {}
        results["ollama"] = self.nexus.health_check()
        if self.wp:
            results["wordpress"] = self.wp.check_health()
        results["cpu_temp"] = self._get_cpu_temp()
        results["timestamp"] = datetime.datetime.now().isoformat()
        utils.log("health", json.dumps(results))
        return all(v for k, v in results.items() if isinstance(v, bool))

    def _get_cpu_temp(self):
        try:
            t = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
            return f"{int(t)//1000}C"
        except:
            return "unknown"

    def run_blog_pipeline(self, count=1):
        utils.log("pipeline", f"Starting blog pipeline: {count} article(s)")

        calendar = load_calendar()
        topics = [t for t in calendar["topics"] if t["status"] == "pending"]
        if not topics:
            utils.log("pipeline", "No pending topics in calendar", "SKIP")
            return

        for topic in topics[:count]:
            try:
                utils.log("pipeline", f"Generating: {topic['title']}")
                self._notify(f"Writing article: {topic['title']}...")

                raw = self.nexus.generate_article(
                    topic=topic["title"],
                    keywords=topic["keywords"],
                    language=topic.get("language", "en"),
                )

                meta_desc, content = self.wp.parse_article_response(raw)
                content = self.social.inject_affiliate_links(content)

                result = self.wp.create_post(
                    title=topic["title"],
                    content=content,
                    meta_description=meta_desc,
                    categories=["AI Automation"],
                    status="publish",
                )

                topic["status"] = "published"
                topic["scheduled_date"] = datetime.datetime.now().isoformat()
                post_id = result.get('id', '?')
                post_link = result.get('link', self.cfg["wordpress"]["url"])
                utils.log("pipeline", f"Published: {topic['title']} (ID: {post_id})")
                self._notify(
                    f"Article published!\n\n"
                    f"Title: {topic['title']}\n"
                    f"Link: {post_link}\n"
                    f"Words: {len(content.split())}"
                )

                self._generate_video_for_topic(topic, content)
                save_calendar(calendar)

            except Exception as e:
                utils.log("pipeline", f"Failed: {topic['title']} - {e}", "ERROR")
                self._notify(f"Article FAILED: {topic['title']}\nError: {e}")
                topic["status"] = "failed"
                save_calendar(calendar)

    def _generate_video_for_topic(self, topic, content):
        try:
            from modules.video_pipeline import VideoPipeline
            video = VideoPipeline()
            result = video.generate_video(topic["title"], content, topic.get("language", "en"))
            vpath = result.get('video_path', '?')
            utils.log("video", f"Video generated: {vpath}")
            self._notify(f"Video ready: {vpath}")
            return result
        except ImportError:
            utils.log("video", "VideoPipeline not available", "SKIP")
        except Exception as e:
            utils.log("video", f"Video generation failed: {e}", "ERROR")

    def run_social_pipeline(self):
        utils.log("pipeline", "Running social media pipeline")
        platforms = ["twitter", "facebook", "linkedin"]
        for platform in platforms:
            try:
                self.social.cross_post(
                    "Daily AI automation tip",
                    "New content from WorkForgeAI",
                    platform,
                    f"Check out the latest AI automation insights at workforgeai.com",
                )
            except Exception as e:
                utils.log("pipeline", f"Social post to {platform} failed: {e}", "ERROR")

    def run_video_pipeline(self):
        utils.log("pipeline", "Running standalone video pipeline")
        try:
            from modules.video_pipeline import VideoPipeline
            pipeline = VideoPipeline()
            video = pipeline.generate_video(
                "WorkForgeAI Automation Overview",
                "Learn how AI automation can save you 10+ hours per week.",
                "en"
            )
            utils.log("video", f"Standalone video: {video.get('video_path', '?')}")
        except Exception as e:
            utils.log("video", f"Standalone video failed: {e}", "ERROR")

    def run_products_pipeline(self):
        utils.log("pipeline", "Running products pipeline")
        builder = ProductBuilder()
        packages = builder.build_all()
        for pkg in packages:
            utils.log("pipeline", f"Product package ready: {pkg}")
            if self.wp:
                try:
                    pkg_path = Path(pkg)
                    pkg_name = pkg_path.stem.replace("-", " ").title()
                    price = 49
                    upload_url = f"{self.cfg['wordpress']['url']}/wp-content/uploads/products/{pkg_path.name}"
                    self.wp.create_product(pkg_name, f"AI-powered {pkg_name}", price, upload_url)
                    utils.log("pipeline", f"Uploaded product: {pkg_name}")
                except Exception as e:
                    utils.log("pipeline", f"Product upload failed: {e}", "WARN")

    def run_backup(self):
        utils.log("pipeline", "Running backup")
        self._notify("Backup started")

    def run_weekly_report(self):
        utils.log("pipeline", "Generating weekly report")
        status = self.check_health()
        calendar = load_calendar()
        published = sum(1 for t in calendar["topics"] if t["status"] == "published")
        pending = sum(1 for t in calendar["topics"] if t["status"] == "pending")
        failed = sum(1 for t in calendar["topics"] if t["status"] == "failed")
        report = (
            f"Weekly Report\n\n"
            f"Health: {'OK' if status else 'ISSUES'}\n"
            f"Temp: {self._get_cpu_temp()}\n"
            f"Articles published: {published}\n"
            f"Pending: {pending}\n"
            f"Failed: {failed}\n"
            f"Model: {self.cfg.get('ollama', {}).get('model', '?')}"
        )
        self._notify(report)
        utils.log("report", report)


def main():
    parser = argparse.ArgumentParser(description="WorkForgeAI Automation Engine")
    parser.add_argument("--mode", default="health",
                        choices=["health", "blog", "social", "video", "products", "backup", "report", "all"])
    parser.add_argument("--count", type=int, default=1, help="Number of articles")
    parser.add_argument("--wp-user", help="WordPress username")
    parser.add_argument("--wp-pass", help="WordPress application password")

    args = parser.parse_args()

    orchestrator = Orchestrator()
    orchestrator.init_wordpress(args.wp_user, args.wp_pass)
    if orchestrator.wp:
        utils.log("orchestrator", "WordPress client initialized")
    else:
        utils.log("orchestrator", "WordPress credentials not available", "WARN")

    modes = {
        "health": orchestrator.check_health,
        "blog": lambda: orchestrator.run_blog_pipeline(args.count),
        "social": orchestrator.run_social_pipeline,
        "video": orchestrator.run_video_pipeline,
        "products": orchestrator.run_products_pipeline,
        "backup": orchestrator.run_backup,
        "report": orchestrator.run_weekly_report,
        "all": lambda: (
            orchestrator.check_health(),
            orchestrator.run_blog_pipeline(args.count),
            orchestrator.run_video_pipeline(),
            orchestrator.run_products_pipeline(),
        ),
    }

    fn = modes.get(args.mode)
    if fn:
        result = fn()
        utils.log("orchestrator", f"Mode '{args.mode}' completed")
        return 0 if result is None or result is True else 1
    else:
        utils.log("orchestrator", f"Unknown mode: {args.mode}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
