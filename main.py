import os
import sys
import shutil

import yt_dlp
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util

from logger import MyLogger
from structures import UserPrompts
from effects import EditorEffects

load_dotenv()

my_prompt = UserPrompts(
    title=os.getenv("TITLE", "Never gonna give you up"),
    author=os.getenv("AUTHOR", "Rick Astley"),
    language=os.getenv("LANGUAGE", "en"),
)

sys.stderr = open("error.log", "w")

logger = MyLogger("main").get_logger()
logger.info("Loading SentenceTransformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
embedding1 = model.encode(
    f"The original video music video called {my_prompt.title} by {my_prompt.author}."
)
logger.info("Model loaded successfully.")

ydl_opts = {
    "skip_download": True,
    "extract_flat": "in_playlist",
    "logger": logger,
}

download_opts = {
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.youtube.com/",
    },
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "geo_bypass": True,
    "logger": logger,
    "subtitleslangs": [my_prompt.language],
    "subtitlesformat": "srt",
    "writesubtitles": True,
    # "verbose": True,
}


with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    logger.info("Searching for videos...")
    results = ydl.extract_info(
        f"ytsearch5:{my_prompt.title} {my_prompt.author}", download=False
    )
    logger.info("Search completed.")

    max_entry = None
    max_cos_sim = -1
    if results is None:
        logger.error("No results found.")
        exit(1)

    for entry in results["entries"]:
        description = (
            "Title Video: "
            + entry.get("title", "No title")
            + " from channel: "
            + entry.get("channel", "No uploader")
        )
        embedding2 = model.encode(description)

        # Compute cosine similarity between the embeddings
        cos_sim = util.cos_sim(embedding1, embedding2)

        logger.info(
            f"Video: {entry.get('title', 'No title')}, Channel: {entry.get('channel', 'No uploader')}, Cosine similarity: {cos_sim.item():.4f}"
        )
        if cos_sim > max_cos_sim:
            max_cos_sim = cos_sim.item()
            max_entry = entry

    # Download the video
    if max_entry:
        logger.info(
            f"Best match found: {max_entry.get('title', 'No title')} with cosine similarity {max_cos_sim:.4f}"
        )
        with yt_dlp.YoutubeDL(download_opts) as download_ydl:
            logger.info(f"Downloading {max_entry['url']}")
            ret_code = download_ydl.download([max_entry["url"]])
            if ret_code != 0:
                logger.error(
                    f"Failed to download video: {max_entry['url']}, return code: {ret_code}"
                )
                exit(1)

            metadata = download_ydl.extract_info(max_entry["url"], download=False)
            if not metadata:
                logger.error("Failed to extract metadata from the downloaded video.")
                exit(1)
            # Get subtitles
            file_name = download_ydl.prepare_filename(metadata)
            base_name = os.path.splitext(file_name)[0]
            subtitle_file = f"{base_name}.{my_prompt.language}.srt"

            logger.info(f"Downloaded to {file_name}")

            edited_filename = os.path.splitext(file_name)[0] + "_edited.mp4"
            shutil.copy(file_name, edited_filename)

            editor = EditorEffects(
                file_path=edited_filename,
                subtitle_path=subtitle_file,
                logger=logger,
                metadata=metadata,
            )
            editor.effects_vid(user_prompts=my_prompt)
            editor.add_subtitles()

    else:
        logger.warning("No suitable video found.")

logger.info("Finished")
