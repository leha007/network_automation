import json
import logging
import os
import sys
from collections import OrderedDict
from json import JSONDecodeError
from multiprocessing.pool import ThreadPool

from netmiko import Netmiko, NetMikoTimeoutException, NetMikoAuthenticationException
from tqdm import tqdm

logger = logging.getLogger(__name__)

g_log_dir_name = "log"


def init_logger():
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    s_handler = logging.StreamHandler(sys.stdout)
    f_handler = logging.FileHandler(str(os.path.basename(__file__).split(".")[0]) + ".log")

    s_handler.setFormatter(formatter)
    f_handler.setFormatter(formatter)

    logger.addHandler(s_handler)
    logger.addHandler(f_handler)

    if not os.path.exists(g_log_dir_name):
        logger.debug("Creating {0} directory".format(g_log_dir_name))
        os.mkdir(g_log_dir_name)


def get_worker_logger(f_name):
    lgr = logging.getLogger(f_name)
    lgr.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    f_handler = logging.FileHandler(os.path.join(g_log_dir_name, f_name + ".log"))
    f_handler.setFormatter(formatter)
    lgr.addHandler(f_handler)
    return lgr


def parse_config():
    conf_file = "config.json"
    logger.info("Reading configuration file [{0}]".format(conf_file))
    with open(conf_file, "r") as json_file:
        return json.load(json_file, object_pairs_hook=OrderedDict)


def write_memory(conn):
    if conn.is_alive():
        logger.info("Saving configuration to memory")
        logger.info(conn.send_command_expect('write memory'))


def execute_on_device_wrapper(args):
    execute_on_device(*args)


def execute_on_device(lgr, global_cmd, k_device, v_device):
    lgr.info("++++++++Connecting to [{0}] device++++++++".format(k_device))
    try:
        pass
        with Netmiko(**v_device.get("conn")) as conn:
            lgr.info("Device Promt: {0}".format(conn.find_prompt()))
            if not conn.check_enable_mode():
                lgr.info("Not in privileged mode, switching to enable")
                conn.enable()
                lgr.info("Promt: {0}".format(conn.find_prompt()))
            if len(v_device.get("cmd")) > 0:
                lgr.info("Executing local commands")
                lgr.info(conn.send_config_set(v_device.get("cmd")))
                if v_device.get("write_memory"):
                    write_memory(conn)
            elif len(global_cmd) > 0:
                lgr.info("Executing global commands")
                lgr.info(conn.send_config_set(global_cmd))
                if v_device.get("write_memory"):
                    write_memory(conn)
            else:
                lgr.warning("No global or local commands found for [{0}] device".format(k_device))
    except ValueError as e:
        lgr.error(e)
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        lgr.error("Failed to connect to [{0}] device, reason: {1}".format(k_device, e))
    lgr.info("++++++++Disconnected from [{0}] device++++++++".format(k_device))


def get_number_of_threads(conf_threads, number_of_devices):
    rc = os.cpu_count()
    if number_of_devices > rc:
        rc *= 2
    else:
        rc = number_of_devices
    if isinstance(conf_threads, str) and conf_threads == "auto":
        logger.info("Using auto for multiprocessing setting")
    elif isinstance(conf_threads, str):
        try:
            rc = int(conf_threads)
        except ValueError:
            logger.warning("Failed to convert {0} to int".format(conf_threads))
    elif isinstance(conf_threads, int):
        rc = conf_threads
    else:
        logger.warning("{0} unknown variable, using auto setting".format(threads))
    logger.info("Initializing {0} workers".format(rc))
    return rc


def run_config(conf):
    is_multi = conf.get("options").get("use_multiprocessing")
    logger.info("Running{0} automation according to config file".format(" multiprocess" if is_multi else ""))

    if is_multi:
        with ThreadPool(processes=get_number_of_threads(conf.get("options").get("threads"),
                                                        len(conf.get("devices")))) as workers_pool:
            for _ in tqdm(workers_pool.imap_unordered(execute_on_device_wrapper, [
                (get_worker_logger(k_device), conf.get("global_cmd"),
                 k_device, v_device) for k_device, v_device in conf.get("devices").items()]),
                          desc="Working on devices", unit="device", total=len(conf.get("devices"))):
                pass
        workers_pool.join()
    else:
        for k_device, v_device in conf.get("devices").items():
            execute_on_device(get_worker_logger(k_device), conf.get("global_cmd"), k_device, v_device)


def main():
    logger.info("---------------------------")
    logger.info("Welcome to Network automation")
    try:
        conf = parse_config()
        run_config(conf)
    except FileNotFoundError as e:
        logger.error(e)
    except JSONDecodeError as e:
        logger.error("Failed to parse config file: [{0}]".format(e))
    logger.info("Finished execution, goodbye")
    logger.info("---------------------------")


if __name__ == "__main__":
    init_logger()
    main()
