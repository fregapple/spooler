import asyncio

pending_jobs = {}
spool_cache = []
shudown_event = asyncio.Event()
printer_file_list = []