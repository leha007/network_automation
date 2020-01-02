import json
import logging
import sys
from collections import OrderedDict
from json import JSONDecodeError

from netmiko import Netmiko, NetMikoTimeoutException, NetMikoAuthenticationException

logger = logging.getLogger(__name__)


def init_logger():
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def parse_config():
    conf_file = "config.json"
    logger.info("Reading configuration file [%s]" % conf_file)
    with open(conf_file, "r") as json_file:
        return json.load(json_file, object_pairs_hook=OrderedDict)


def write_memory(conn):
    if conn.is_alive():
        logger.info("Saving configuration to memory")
        logger.info(conn.send_command_expect('write memory'))


def run_config(conf):
    logger.info("Running automation according to config file")
    for k_device, v_device in conf.get("devices").items():
        logger.info("Connecting to [%s] device" % k_device)
        try:
            with Netmiko(**v_device.get("conn")) as conn:
                logger.info("Promt: %s" % conn.find_prompt())
                if not conn.check_enable_mode():
                    logger.info("Not in privileged mode, switching to enable")
                    conn.enable()
                    logger.info("Promt: %s" % conn.find_prompt())
                if len(v_device.get("cmd")) > 0:
                    logger.info("Executing local commands")
                    logger.info(conn.send_config_set(v_device.get("cmd")))
                    write_memory(conn)
                elif len(conf.get("global_cmd")) > 0:
                    logger.info("Executing global commands")
                    logger.info(conn.send_config_set(conf.get("global_cmd")))
                    write_memory(conn)
                else:
                    logger.warning("No global or local commands found for [%s] device" & k_device)
        except ValueError as e:
            logger.error(e)
        except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
            logger.error("Failed to connect to [%s] device, reason: %s" % k_device, e)


def main():
    logger.info("Welcome to CISCO automation")
    try:
        conf = parse_config()
        run_config(conf)
    except FileNotFoundError as e:
        logger.error(e)
    except JSONDecodeError as e:
        logger.error("Failed to parse config file: [%s]" % e)
    logger.info("Finished execution, goodbye")


if __name__ == "__main__":
    init_logger()
    main()
