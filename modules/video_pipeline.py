import asyncio
import os
import re
import tempfile
import textwrap
from pathlib import Path

import edge_tts
import numpy as np

from modules.ai_generator import NEXUSClient
from modules.utils import load_config, log


try:
    from moviepy import (
        AudioFileClip,
        CompositeVideoClip,
        TextClip,
        VideoClip,
        concatenate_videoclips,
        vfx,
    )
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# Font selection — Linux-friendly paths
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_FONT_BOLD = _FONT_CANDIDATES[0]
for _f in _FONT_CANDIDATES:
    if Path(_f).exists():
        _FONT_BOLD = _f
        break

_FONT_REGULAR = _FONT_BOLD.replace("-Bold", "").replace("Bold", "")
if not Path(_FONT_REGULAR).exists():
    _FONT_REGULAR = _FONT_BOLD


BASE_DIR = Path(__file__).parent.parent
VIDEOS_DIR = BASE_DIR / "products" / "videos"


class VideoPipeline:
    def __init__(self):
        self.cfg = load_config()
        self.nexus = NEXUSClient()
        self.videos_dir = VIDEOS_DIR
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self._tmp_files = []

    # ------------------------------------------------------------------
    #  PUBLIC API
    # ------------------------------------------------------------------

    def generate_video(self, topic, article_text, language="en"):
        log("VideoPipeline", "Generating video for topic: %s" % topic)
        script = self.generate_script(topic, article_text)
        if not script:
            raise RuntimeError("Script generation returned empty result")
        log("VideoPipeline", "Script generated (%d chars)" % len(script))
        audio_path = self.generate_voiceover(script, language)
        log("VideoPipeline", "Voiceover saved: %s" % audio_path)
        output_path = str(self.videos_dir / self._safe_filename(topic, "mp4"))
        video_path = self.create_video(audio_path, script, topic, output_path)
        log("VideoPipeline", "Video saved: %s" % video_path)
        self._cleanup()
        from moviepy import VideoFileClip
        with VideoFileClip(video_path) as clip:
            duration = clip.duration
        return {
            "video_path": video_path,
            "duration_seconds": round(duration, 1),
            "topic": topic,
            "language": language,
        }

    def generate_script(self, topic, article_text):
        prompt = (
            "You are a professional video script writer for WorkForgeAI.com.\n"
            "Create a 60-second short-form video script (TikTok/Reels/Shorts) about:\n\n"
            "TOPIC: %s\n\n"
            "REFERENCE CONTENT:\n%s\n\n"
            "FORMAT REQUIREMENTS:\n"
            "- Exactly 6 to 8 sentences, each on its own line\n"
            "- No numbering, no timestamps, no scene directions, no music cues\n"
            "- Start with a strong hook sentence\n"
            "- Middle sentences explain the value or key points\n"
            "- Final sentence must be: 'Visit workforgeai.com to learn more.'\n"
            "- Total: 120-150 words\n"
            "- Conversational, energetic tone suitable for social media\n\n"
            "OUTPUT ONLY THE SENTENCES, ONE PER LINE. NO OTHER TEXT."
        ) % (topic, article_text[:4000])

        result = self.nexus._post("/v1/nexus", {
            "text": prompt,
            "agent": "nexus",
            "use_cache": True,
        })
        raw = result.get("response", "")
        lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
        lines = [re.sub(r"^[-*\d\.\)\[\]]+\s*", "", l) for l in lines]
        lines = [l for l in lines if len(l) > 10]
        return "\n".join(lines)

    def generate_voiceover(self, script, language="en"):
        voice_map = {
            "pt": "pt-PT-DuarteNeural",
            "en": "en-US-JennyNeural",
        }
        voice = voice_map.get(language, "en-US-JennyNeural")
        audio_path = str(Path(tempfile.gettempdir()) / self._safe_filename("voiceover", "mp3"))
        self._tmp_files.append(audio_path)
        asyncio.run(self._do_tts(script, voice, audio_path))
        return audio_path

    def create_video(self, audio_path, script, topic, output_path):
        if not HAS_MOVIEPY or not HAS_PIL:
            raise ImportError("moviepy and pillow are required for video creation")

        with AudioFileClip(audio_path) as audio:
            total_duration = audio.duration
        if total_duration < 5:
            total_duration = 30

        segments = self._split_script(script, min_segments=5, max_segments=8)
        seg_duration = total_duration / len(segments)

        bg_clip = self._make_gradient_background(duration=total_duration)

        text_clips = []
        for i, seg_text in enumerate(segments):
            start = i * seg_duration
            clip = self._make_caption_clip(
                text=seg_text,
                duration=seg_duration,
                start=start,
            )
            text_clips.append(clip)

        bar = self._make_progress_bar(total_duration)
        text_clips.append(bar)

        branding = self._make_branding(total_duration)
        text_clips.append(branding)

        video = CompositeVideoClip(
            [bg_clip] + text_clips + [TextClip(text=" ", font=_FONT_BOLD, font_size=1, duration=total_duration)],
            size=(1080, 1920),
        )
        audio_clip = AudioFileClip(audio_path)
        video = video.with_audio(audio_clip)

        video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="medium",
            bitrate="4000k",
            threads=2,
        )
        video.close()
        return output_path

    def get_video_path(self, topic):
        return str(self.videos_dir / self._safe_filename(topic, "mp4"))

    # ------------------------------------------------------------------
    #  INTERNALS
    # ------------------------------------------------------------------

    @staticmethod
    async def _do_tts(text, voice, output_path):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    def _split_script(self, script, min_segments=5, max_segments=8):
        sentences = [s.strip() for s in script.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if len(sentences) <= max_segments:
            return sentences
        n = min(max_segments, len(sentences))
        groups = [[] for _ in range(n)]
        for idx, sent in enumerate(sentences):
            groups[idx % n].append(sent)
        return [" ".join(g) for g in groups]

    def _safe_filename(self, topic, ext):
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", topic.lower())
        safe = re.sub(r"_+", "_", safe).strip("_")
        return "%s_%s.%s" % (safe, os.urandom(4).hex(), ext)

    def _make_gradient_background(self, duration, size=(1080, 1920)):
        w, h = size
        img = Image.new("RGB", (w, h), color="#0f0f1e")
        draw = ImageDraw.Draw(img)
        top_color = (15, 15, 30)
        mid_color = (25, 15, 45)
        bottom_color = (40, 10, 60)
        for y in range(h):
            ratio = y / h
            if ratio < 0.5:
                t = ratio * 2
                r = int(top_color[0] * (1 - t) + mid_color[0] * t)
                g = int(top_color[1] * (1 - t) + mid_color[1] * t)
                b = int(top_color[2] * (1 - t) + mid_color[2] * t)
            else:
                t = (ratio - 0.5) * 2
                r = int(mid_color[0] * (1 - t) + bottom_color[0] * t)
                g = int(mid_color[1] * (1 - t) + bottom_color[1] * t)
                b = int(mid_color[2] * (1 - t) + bottom_color[2] * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        cx, cy = w // 2, h // 3
        for r in range(max(0, cy - 200), min(h, cy + 200)):
            for c in range(max(0, cx - 150), min(w, cx + 150)):
                dx, dy = c - cx, r - cy
                dist = np.sqrt(dx**2 + dy**2)
                if dist < 200:
                    alpha = 1 - dist / 200
                    px = img.getpixel((c, r))
                    glow = int(40 * alpha)
                    img.putpixel(
                        (c, r),
                        (min(px[0] + glow, 255), min(px[1] + glow, 255), min(px[2] + glow * 2, 255)),
                    )
        bg_array = np.array(img)
        return VideoClip(lambda t: bg_array, duration=duration).with_fps(1)

    def _make_caption_clip(self, text, duration, start, size=(1080, 1920)):
        wrapped = textwrap.fill(text, width=35)
        txt_clip = TextClip(
            text=wrapped,
            font=_FONT_BOLD,
            font_size=52,
            color="white",
            stroke_color="black",
            stroke_width=2,
            size=(size[0] - 120, None),
            method="caption",
            text_align="center",
        )
        txt_clip = txt_clip.with_duration(duration).with_position(("center", size[1] * 0.35))
        txt_clip = txt_clip.with_start(start)
        fade_duration = min(0.5, duration * 0.1)
        txt_clip = txt_clip.with_effects([vfx.FadeIn(fade_duration), vfx.FadeOut(fade_duration)])
        return txt_clip

    def _make_progress_bar(self, total_duration, size=(1080, 1920)):
        bar_height = 6
        bar_width = size[0] - 200
        bar_x = (size[0] - bar_width) // 2
        bar_y = size[1] - 120

        def make_frame(t):
            progress = t / total_duration if total_duration > 0 else 0
            fill = int(bar_width * progress)
            frame = np.zeros((bar_height, bar_width, 3), dtype=np.uint8)
            if fill > 0:
                frame[:, :fill] = (100, 180, 255)
            frame[:, fill:] = (60, 60, 80)
            if fill > 2:
                edge = max(0, fill - 2)
                frame[:, edge:min(fill, bar_width)] = (200, 230, 255)
            return frame

        bar_clip = VideoClip(make_frame, duration=total_duration)
        bar_clip = bar_clip.with_position((bar_x, bar_y)).with_duration(total_duration)
        return bar_clip

    def _make_branding(self, total_duration, size=(1080, 1920)):
        brand_clip = TextClip(
            text="workforgeai.com",
            font=_FONT_BOLD,
            font_size=30,
            color=(150, 150, 180),
            stroke_color="black",
            stroke_width=1,
        )
        fade_in_start = max(0, total_duration - 8)
        brand_duration = total_duration - fade_in_start
        brand_clip = (
            brand_clip.with_duration(brand_duration)
            .with_position(("center", 1800))
            .with_start(fade_in_start)
            .with_effects([vfx.FadeIn(1)])
        )
        return brand_clip

    def _cleanup(self):
        for p in list(self._tmp_files):
            try:
                if p and Path(p).exists():
                    Path(p).unlink()
            except Exception:
                pass
        self._tmp_files = []

    def __del__(self):
        if hasattr(self, "_tmp_files"):
            self._cleanup()
