import argparse
import asyncio
import os
import time

from rich import print
from rich.traceback import install as traceback_install

from api.asyncdownloader import AsyncDownloader
from api.tiktokscraper import TiktokScraper

traceback_install(theme="vim")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Download TikTok videos by USERNAME")
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        help="TikTok username, Example (google, @google, https://www.tiktok.com/@google)",
    )
    parser.add_argument(
        "-sj",
        "--save_json",
        default=False,
        action="store_true",
        help="Save video info as JSON file",
    )
    parser.add_argument(
        "-mx",
        "--maximized_windows",
        default=False,
        action="store_true",
        help="Maximize browser size",
    )
    parser.add_argument(
        "-el",
        "--enable_log",
        default=False,
        action="store_true",
        help="For debugging purpose",
    )
    parser.add_argument(
        "-hl",
        "--headless",
        default=False,
        action="store_true",
        help="For headless setting",
    )
    parser.add_argument(
        "-ts",
        "--transient",
        default=False,
        action="store_true",
        help="Close the progress bar after all the downloads/tasks are finished",
    )
    parser.add_argument(
        "-ic",
        "--instant_clear",
        default=False,
        action="store_true",
        help="Close the progress bar immediately after one task is completed",
    )
    return parser.parse_args()


def timer_wrapper(coroutine):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        await coroutine(*args, **kwargs)
        elapsed_time = time.time() - start_time
        print(f"\n[green]Total elapsed time: {elapsed_time:.2f} seconds[/]\n")

    return wrapper


@timer_wrapper
async def main():
    os.system("cls" if os.name == "nt" else "clear")
    args = parse_arguments()
    if not args.username:
        os.system("python main.py -h" if os.name == "nt" else "python3 main.py -h")
        return
    tiktok_scraper = TiktokScraper(
        channel_url=args.username,
        headless=args.headless,
        enable_log=args.enable_log,
        max_windows=args.maximized_windows,
    )
    username = tiktok_scraper.get_username
    tiktok_scraper.scrape_video_link()
    await AsyncDownloader(
        username=username,
        save_json=args.save_json,
        transient=args.transient,
        instant_clear=args.instant_clear,
    )


if __name__ == "__main__":
    asyncio.run(main())
