# run_ingestor.py

import logging
import asyncio
from src.scribe.config.loader import load_task_from_yaml
from src.scribe.config.tasks import monitor_and_ingest_email_reports

# Optional: Customize logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def main():
    logging.info("Initializing IngestorAgent task execution...")

    try:
        task = load_task_from_yaml("monitor_and_ingest_email_reports")
        logging.info("Task metadata loaded successfully. Executing external task function...")
        # Manually invoke the external async function following CrewAI v0.14+ conventions
        result = asyncio.run(monitor_and_ingest_email_reports(None, getattr(task, 'agent', None), task))
        logging.info("Task function completed.")
        print("\n📬 Task Result:")
        print(result)
    except Exception as e:
        logging.exception("Task execution failed due to an error.")
        print(f"\n❌ Error during task execution: {e}")


if __name__ == "__main__":
    main()
