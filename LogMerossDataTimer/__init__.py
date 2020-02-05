import os
import time
import datetime
import logging

import azure.functions as func

from random import randint

from meross_iot.cloud.devices.power_plugs import GenericPlug
from meross_iot.manager import MerossManager
from meross_iot.meross_event import MerossEventType


def main(mytimer: func.TimerRequest) -> None:
    if mytimer.past_due:
        logging.info('The timer is past due!')

    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    logging.info('Meross logging timer trigger function running at %s', utc_timestamp)

    EMAIL = os.environ.get('MEROSS_EMAIL')
    PASSWORD = os.environ.get('MEROSS_PASSWORD')

    # Initiates the Meross Cloud Manager. This is in charge of handling the communication with the remote endpoint
    manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)

    # Starts the manager
    manager.start()

    # Get all plugs
    plugs = manager.get_devices_by_kind(GenericPlug)

    for p in plugs:  # type: GenericPlug
        if not p.online:
            print("The plug %s seems to be offline." % p.name)
            continue

        print("Smart plug %s" % p.name)

        if not p.supports_electricity_reading():
            print("The plug %s does not support power consumption reading." % p.name)
            continue
            
        print("Current consumption is: %s" % str(p.get_electricity()))

    manager.stop()
    
    print("Function complete")
