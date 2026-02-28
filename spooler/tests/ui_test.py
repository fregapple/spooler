import asyncio

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Log, ProgressBar, Static

# ── Header ───────────────────────────────────────────────────


class HeaderPanel(Static):
    def compose(self) -> ComposeResult:
        yield Static(
            "███████╗██████╗  ██████╗  ██████╗ ██╗     ███████╗██████╗\n"
            "██╔════╝██╔══██╗██╔═══██╗██╔═══██╗██║     ██╔════╝██╔══██╗\n"
            "███████╗██████╔╝██║   ██║██║   ██║██║     █████╗  ██████╔╝\n"
            "╚════██║██╔═══╝ ██║   ██║██║   ██║██║     ██╔══╝  ██╔══██╗\n"
            "███████║██║     ╚██████╔╝╚██████╔╝███████╗███████╗██║  ██║\n"
            "╚══════╝╚═╝      ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝\n"
            "Spoolman • Centauri Carbon • OrcaSlicer Bridge",
            classes="header-text",
        )


# ── Left column: printer + progress ──────────────────────────


class PrinterInfoPanel(Static):
    printer = reactive("X1C")
    status = reactive("Idle")
    job = reactive("—")
    layer = reactive("0 / 0")
    eta = reactive("--:--")
    nozzle = reactive("0°C")
    bed = reactive("0°C")
    speed = reactive("100%")
    fan = reactive("0%")

    def render(self):
        return (
            f"   Printer  {self.printer:<10}     Status  {self.status}\n"
            f"   Job      {self.job}\n"
            f"   Layer    {self.layer:<10}     ETA     {self.eta}\n"
            f"   Nozzle   {self.nozzle:<10}   Bed     {self.bed}\n"
            f"   Speed    {self.speed:<10}   Fan     {self.fan}"
        )


class ProgressPanel(Static):
    progress = reactive(0)
    active = reactive(True)

    def compose(self) -> ComposeResult:
        self.bar = ProgressBar(total=100)
        yield self.bar

    def watch_progress(self, value: int):
        if self.active:
            self.bar.update(progress=value)


# ── DevicePanel (framed device card with title) ──────────────


class DevicePanel(Static):
    def __init__(self, title: str, stats: dict, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.stats = stats

    def render(self):
        lines = [f" {key:<14} {value}" for key, value in self.stats.items()]
        body = "\n".join(lines)
        return f"[b]{self.title}[/b]\n{body}"


# ── Main app ─────────────────────────────────────────────────


class Dashboard(App):
    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    HeaderPanel {
        height: 9;
        border: round $accent;
        content-align: center middle;
        color: cyan;
    }

    .header-text {
        height: 9;
        content-align: center top;
        text-align: center;
        border: none;
        color: cyan;
    }

    Horizontal#middle {
        height: 12;
    }

    Vertical#left {
        width: 1fr;
        border: round $accent;
        padding: 1;
    }

    /* FIX: Right column now matches left column border */
    Vertical#right {
        width: 1fr;
        border: round $accent;
        padding: 1;
    }

    PrinterInfoPanel {
        height: 7;
    }

    ProgressPanel {
        height: 3;
    }

    DevicePanel {
        width: 50%;
        border: round $accent;
        margin-bottom: 1;
    }

    Log {
        border: round $accent;
    }
    """

    def compose(self) -> ComposeResult:
        yield HeaderPanel()

        with Horizontal(id="middle"):
            with Vertical(id="left"):
                yield PrinterInfoPanel()
                yield ProgressPanel()

            with Vertical(id="right"):
                yield DevicePanel(
                    "Air Purifier",
                    {
                        "Power:": "On",
                        "Mode:": "Auto",
                        "Fan Speed:": "Mid",
                        "Filter Level:": "82%",
                        "Filter Days:": "143",
                    },
                )

                yield DevicePanel(
                    "Lights",
                    {
                        "Power:": "Off",
                        "Brightness:": "0%",
                        "Color:": "#FFFFFF",
                    },
                )

        yield Log()

    async def on_mount(self):
        log = self.query_one(Log)
        log.write("[INFO] Spooler UI test started")
        log.write("[INFO] This is the new cockpit layout")

        progress = self.query_one(ProgressPanel)

        async def update_progress():
            for i in range(101):
                progress.progress = i
                await asyncio.sleep(0.03)

        self.run_worker(update_progress())


if __name__ == "__main__":
    Dashboard().run()
