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


async def main(mytimer: func.TimerRequest) -> None:
    if mytimer.past_due:
        logging.info('The timer is past due!')

    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    logging.debug('Meross logging timer trigger function running at %s', utc_timestamp)

    meross_email = os.environ.get('MEROSS_EMAIL')
    meross_password = os.environ.get('MEROSS_PASSWORD')
    meross_device_name = os.environ.get('MEROSS_DEVICE_NAME')
    meross_device_uuid = os.environ.get('MEROSS_DEVICE_UUID')

    # The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
    iothub_conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

    # Initiates the Meross Cloud Manager. This is in charge of handling the communication with the remote endpoint
    manager = MerossManager(meross_email=meross_email, meross_password=meross_password)

    # Starts the manager
    manager.start()

    # The client object is used to interact with your Azure IoT hub.
    device_client = IoTHubDeviceClient.create_from_connection_string(iothub_conn_str)

    # Connect the IOT hub client.
    await device_client.connect()

#    plug_device = manager.get_device_by_name(meross_device_name)
    plug_device = manager.get_device_by_uuid(meross_device_uuid)
    
    if not plug_device:
        # logging.error("The plug %s is not registered." % meross_device_name)
        logging.error("The plug %s is not registered." % meross_device_uuid)
    else:
        if not plug_device.online:
            logging.warn("The plug %s seems to be offline." % plug_device.name)
        else:
            logging.info("Smart plug %s" % plug_device.name)
            logging.info("  uuid : %s" % plug_device.uuid)

            if not plug_device.supports_electricity_reading():
                logging.warn("The plug %s does not support power consumption reading." % plug_device.name)
            else:
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

    # Disconnect Meross
    manager.stop()
    
    # Disconnect IOT hub
    await device_client.disconnect()

    logging.info("Function complete")
