import asyncio
import json
import os
from datetime import datetime
from http.cookies import SimpleCookie

import aiofiles
import aiohttp
import inquirer
from bs4 import BeautifulSoup, Tag
from rich.live import Live
from rich.progress import Progress, TaskID
from rich.prompt import Prompt
from user_agent import generate_user_agent

from exception import ScriptTagNotFoundError, TextfileNotFoundError
from terminal.console import console
from terminal.progress import ProgressBar


class VideoDownloader:
    TXT_FILE = None
    USER_AGENT = generate_user_agent()

    async def __aenter__(self):
        self.client = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *_):
        await self.client.close()

    async def _get_tiktok_video_details(
        self, session: aiohttp.ClientSession, tiktok_video_url: str
    ):
        headers = {"User-Agent": self.USER_AGENT}
        async with session.get(tiktok_video_url, headers=headers) as response:
            response.raise_for_status()
            soup = BeautifulSoup(await response.text(), "lxml")
            script_tag = soup.select_one("script#__UNIVERSAL_DATA_FOR_REHYDRATION__")
            if script_tag:
                return self._handle_script_tag(script_tag, response)
            raise ScriptTagNotFoundError("Script tag is not found.")

    def _handle_script_tag(self, script_tag: Tag, response: aiohttp.ClientResponse):
        tag_contents = script_tag.contents[0]
        universal = json.loads(tag_contents)
        default_scope = universal.get("__DEFAULT_SCOPE__", {})
        video_details = default_scope.get("webapp.video-detail", {})
        video_info = video_details.get("itemInfo", {}).get("itemStruct", {})
        video_dict = video_info.get("video", {})

        return {
            "id": video_info.get("id", ""),
            "desc": video_info.get("desc", ""),
            "createTime": datetime.utcfromtimestamp(
                int(video_info.get("createTime", 0))
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "unwatermarked": video_dict.get("playAddr", ""),
            "watermarked": video_dict.get("downloadAddr", ""),
            "bitrate": video_dict.get("bitrate", ""),
            "cookies": response.cookies,
            "author": video_info.get("author", {}),
        }

    async def _download_video_core(
        self,
        session: aiohttp.ClientSession,
        video_download_url: str,
        create_time: str,
        cookies: SimpleCookie,
        tiktok_video_url: str,
        job_progress: Progress,
        overall_progress: Progress,
        overall_task: TaskID,
        instant_clear: bool,
    ):
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.tiktok.com/",
            "Range": "bytes=0-",
            "Origin": "https://www.tiktok.com",
            "DNT": "1",
            "Sec-GPC": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
        if video_download_url:
            async with session.get(
                video_download_url, headers=headers, cookies=cookies
            ) as response:
                response.raise_for_status()
                await self._handle_video_response(
                    response,
                    video_download_url,
                    create_time,
                    tiktok_video_url,
                    job_progress,
                    overall_progress,
                    overall_task,
                    instant_clear,
                )
        else:
            console.print(
                f"[red1] Couldn't find video download URL for[/] {tiktok_video_url}"
            )
            overall_progress.update(overall_task, advance=1)

    async def _handle_video_response(
        self,
        response: aiohttp.ClientResponse,
        video_download_url: str,
        create_time: str,
        tiktok_video_url: str,
        job_progress: Progress,
        overall_progress: Progress,
        overall_task: TaskID,
        instant_clear: bool,
    ):
        if response.status == 206:
            videos_directory = "Tiktok VIDEOS"
            os.makedirs(videos_directory, exist_ok=True)

            username = tiktok_video_url.split("@")[-1].split("/")[0]
            video_id = tiktok_video_url.split("/")[-1]
            video_date = create_time.split(" ")[0]

            user_directory = os.path.join(videos_directory, username)
            os.makedirs(user_directory, exist_ok=True)
            filename = f"{user_directory}/video-{video_id}-{video_date}.mp4"

            async with aiofiles.open(filename, "wb") as file:
                content_length = int(response.headers.get("Content-Length", 0))
                job_task = job_progress.add_task(
                    f"[blue_violet]Downloading [blue1]{video_id}",
                    total=content_length,
                )
                received = 0
                async for chunk in response.content.iter_any():
                    if chunk:
                        await file.write(chunk)
                        received += len(chunk)
                        job_progress.update(job_task, completed=received)

                overall_progress.update(overall_task, advance=1)

            if instant_clear:
                job_progress.remove_task(job_task)
        else:
            console.print(
                f"Streaming failed for url {video_download_url}: {response.status}"
            )

    async def _download_video(
        self,
        session: aiohttp.ClientSession,
        result: dict,
        tiktok_video_url: str,
        job_progress: Progress,
        overall_progress: Progress,
        overall_task: TaskID,
        instant_clear: bool,
    ):
        await self._download_video_core(
            session,
            result["unwatermarked"],
            result["createTime"],
            result["cookies"],
            tiktok_video_url,
            job_progress,
            overall_progress,
            overall_task,
            instant_clear,
        )

    def load_urls(self, username: str):
        url_directory = "Tiktok URL"
        if username:
            filename = os.path.join(url_directory, f"{username}.txt")
        else:
            text_file_list = [f for f in os.listdir(url_directory)]
            if not text_file_list:
                raise TextfileNotFoundError(
                    f"No text file found in the folder '{url_directory}'"
                )

            text_file = inquirer.List(
                "filename",
                message="Select a filename:",
                choices=text_file_list,
            )
            answer = inquirer.prompt([text_file])
            self.TXT_FILE = answer["filename"]
            filename = os.path.join(url_directory, self.TXT_FILE)

        with open(filename, "r") as file:
            return [url.strip() for url in file if url.strip()]

    def url_limiter(self, tiktok_video_urls: list):
        prompt_for_input = lambda message: Prompt.ask(message)

        user_input = prompt_for_input(
            f"Found '[green1]{len(tiktok_video_urls)}[/]' URLs! [violet]Do you want to limit URLs?[/] Press '[blue]ENTER[/]' to skip"
        )
        while True:
            if not user_input.strip():
                console.print()
                return tiktok_video_urls
            elif user_input.isdigit():
                console.print()
                return tiktok_video_urls[: int(user_input)]
            else:
                user_input = prompt_for_input(
                    f"[red1]Input error![/] [violet]Enter only digits[/] or Press '[blue]ENTER[/]' to download all '[green1]{len(tiktok_video_urls)}[/]' URLs"
                )

    async def download_videos(
        self,
        session: aiohttp.ClientSession,
        url_limiter: list,
        job_progress: Progress,
        overall_progress: Progress,
        overall_task: TaskID,
        username: str,
        save_json: bool,
        instant_clear: bool,
    ):
        results_coro = [
            self._get_tiktok_video_details(session, tiktok_video_url)
            for tiktok_video_url in url_limiter
        ]
        results = await asyncio.gather(*results_coro)

        if save_json:
            json_directory = "Tiktok JSON"
            os.makedirs(json_directory, exist_ok=True)
            if username:
                filename = os.path.join(json_directory, f"{username}.json")
            else:
                filename = os.path.join(
                    json_directory, f"{self.TXT_FILE.split('.')[0]}.json"
                )

            with open(filename, "w") as file:
                json.dump(results, file, indent=4)

        videos_coro = [
            self._download_video(
                session,
                result,
                tiktok_video_url,
                job_progress,
                overall_progress,
                overall_task,
                instant_clear,
            )
            for result, tiktok_video_url in zip(results, url_limiter)
        ]
        await asyncio.gather(*videos_coro)


async def AsyncDownloader(
    username: str, save_json: bool, transient: bool, instant_clear: bool
):
    async with VideoDownloader() as downloader:
        tiktok_video_urls = downloader.load_urls(username)
        url_limiter = downloader.url_limiter(tiktok_video_urls)
        job_progress, overall_progress = ProgressBar.setup_progress_bars()
        overall_task = overall_progress.add_task(
            "[yellow1]Overall progress...", total=len(url_limiter)
        )
        with Live(
            ProgressBar.create_progess_panel(job_progress, overall_progress),
            refresh_per_second=10,
            transient=transient,
        ):
            await downloader.download_videos(
                downloader.client,
                url_limiter,
                job_progress,
                overall_progress,
                overall_task,
                username,
                save_json,
                instant_clear,
            )
