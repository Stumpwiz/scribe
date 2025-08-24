import json
import logging

from scribe.tools.email_inbox_monitor_tool import EmailInboxMonitorTool


if __name__ == "__main__":
    # Configure basic logging to console
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

    tool = EmailInboxMonitorTool()
    result = tool._run(max_results=10)

    print(json.dumps(result, indent=2))
