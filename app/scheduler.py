from apscheduler.schedulers.background import BackgroundScheduler


def start_scheduler(app):
    scheduler = BackgroundScheduler(daemon=True)

    def job():
        with app.app_context():
            from app.utils import run_cleanup
            removed = run_cleanup()
            if removed:
                app.logger.info("Cleanup removed %d expired/spent file(s)", removed)

    interval = app.config["CLEANUP_INTERVAL_MINUTES"]
    scheduler.add_job(job, "interval", minutes=interval, id="tmpbox_cleanup", replace_existing=True)
    scheduler.start()
    return scheduler
