from rich.console import Group
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


class ProgressBar:
    @staticmethod
    def setup_progress_bars():
        job_progress = Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TextColumn("•"),
            TransferSpeedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(compact=True, elapsed_when_finished=True),
        )
        overall_progress = Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
        )
        return job_progress, overall_progress

    @staticmethod
    def create_progess_panel(job_progress: Progress, overall_progress: Progress):
        return Panel(Group(job_progress, overall_progress))
