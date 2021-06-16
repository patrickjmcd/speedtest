import sys
import logging
from os import getenv

import speedtest
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from requests import ConnectTimeout, ConnectionError

log_level = logging.DEBUG
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s -  - %(message)s", level=log_level)

def setup_speedtest(server=None):
    """
    Initializes the Speed Test client with the provided server
    :param server: Int
    :return: None
    """
    speedtest.build_user_agent()

    logging.debug('Setting up SpeedTest.net client')

    if server is None:
        server = []
    else:
        server = server.split()  # Single server to list

    try:
        st = speedtest.Speedtest()
    except speedtest.ConfigRetrievalError:
        logging.critical(
            'Failed to get speedtest.net configuration.  Aborting')
        sys.exit(1)

    st.get_servers(server)

    logging.debug('Picking the closest server')

    st.get_best_server()

    logging.info('Selected Server %s in %s',
                st.best['id'], st.best['name'])

    return st

def send_results(results):
    """
    Formats the payload to send to InfluxDB
    :rtype: None
    """
    result_dict = results.dict()
    pt = Point("speed_test_results")
    pt.field('download', result_dict['download'])
    pt.field('upload', result_dict['upload'])
    pt.field('ping', result_dict['server']['latency'])
    pt.tag('server', result_dict['server']['id'])
    pt.tag('server_name', result_dict['server']['name'])
    pt.tag('server_country', result_dict['server']['country'])

    if getenv("INFLUXDB_V2_URL"):
        client = InfluxDBClient.from_env_properties()
        write_api = client.write_api(write_options=SYNCHRONOUS)
        if write_api.write("speedtests/autogen", 'patrickjmcd', pt):
            logging.debug('Data written to InfluxDB')
        else:
            logging.error("Data not written to influxdb")

def run_speed_test(server=None):
    """
    Performs the speed test with the provided server
    :param server: Server to test against
    """
    logging.info('Starting Speed Test For Server %s', server)

    try:
        st = setup_speedtest(server)
    except speedtest.NoMatchedServers:
        logging.error('No matched servers: %s', server)
        return
    except speedtest.ServersRetrievalError:
        logging.critical('Cannot retrieve speedtest.net server list. Aborting')
        return
    except speedtest.InvalidServerIDType:
        logging.error('%s is an invalid server type, must be int', server)
        return

    logging.info('Starting download test')
    st.download()
    logging.info('Starting upload test')
    st.upload()


    send_results(st.results)

    results = st.results.dict()
    logging.info('Download: %sMbps - Upload: %sMbps - Latency: %sms',
                round(results['download'] / 1000000, 2),
                round(results['upload'] / 1000000, 2),
                results['server']['latency']
                )


def run(server=None):
    run_speed_test(server)

if __name__ == "__main__":
    run()