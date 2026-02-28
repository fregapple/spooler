class PrintState:
    def __init__(self):
        self.active = False
        self.paused = False
        self.stopped = False
        self.waiting_for_idle = False
        self.multi_print_info = True
        self.last_progress = None
        self.filename = None
        self.shortname = None
        self.job = None
        self.total_extrusions = None

    def reset(self):
        self.active = False
        self.paused = False
        self.stopped = False
        self.waiting_for_idle = False
        self.multi_print_info = True
        self.last_progress = None
        self.filename = None
        self.shortname = None
        self.job = None
        self.total_extrusions = None