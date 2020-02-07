import os
import asyncio
import datetime
import logging
import time
import uuid

import azure.functions as func

from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message

from meross_iot.cloud.devices.power_plugs import GenericPlug
from meross_iot.manager import MerossManager
from meross_iot.meross_event import MerossEventType

async def log_device_usage(plug_device: GenericPlug) -> None:
    device_uuid = plug_device.uuid

    # The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
    iothub_conn_str = os.getenv("IOTHUB_DEVICE_CONNSTR_" + device_uuid)

    if not iothub_conn_str:
        logging.warn("The plug '%s' (%s) is not configured." % (device_uuid, plug_device.name))
        return

    # The client object is used to interact with your Azure IoT hub.
    device_client = IoTHubDeviceClient.create_from_connection_string(iothub_conn_str)

    # Connect the IOT hub client.
    await device_client.connect()

    logging.info("Smart plug %s" % plug_device.name)
    logging.info("  uuid : %s" % plug_device.uuid)

    electricity = plug_device.get_electricity()

    converted = {}
    converted["voltage"] = electricity["voltage"] * 0.1
    converted["current"] = electricity["current"] * 0.001
    converted["power"] = electricity["power"] * 0.001

    logging.debug("sending message")
    msg = Message(str(converted))
    msg.message_id = uuid.uuid4()

    await device_client.send_message(msg)
    logging.debug("done sending message")

    # Disconnect IOT hub
    await device_client.disconnect()

async def main(mytimer: func.TimerRequest) -> None:
    if mytimer.past_due:
        logging.info('The timer is past due!')

    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    logging.debug('Meross logging timer trigger function running at %s', utc_timestamp)

    meross_email = os.environ.get('MEROSS_EMAIL')
    meross_password = os.environ.get('MEROSS_PASSWORD')

    # Initiates the Meross Cloud Manager. This is in charge of handling the communication with the remote endpoint
    manager = MerossManager(meross_email=meross_email, meross_password=meross_password)

    # Starts the manager
    manager.start()

    plugs = manager.get_devices_by_kind(GenericPlug)

    for plug_device in plugs:  # type: GenericPlug
        if not plug_device.online:
            logging.warn("The plug %s seems to be offline." % plug_device.name)
            continue

        if not plug_device.supports_electricity_reading():
            logging.warn("The plug %s does not support power consumption reading." % plug_device.name)
            continue

        await log_device_usage(plug_device)

    # Disconnect Meross
    manager.stop()
    
    logging.info("Function complete")
