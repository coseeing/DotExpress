import threading

from client_init import run_client_init


def start_client_init_background(
    *,
    run_client_init=run_client_init,
    thread_factory=threading.Thread,
):
    def worker():
        try:
            run_client_init()
        except Exception:
            pass

    thread = thread_factory(target=worker, daemon=True)
    thread.start()
    return thread
