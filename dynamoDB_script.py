import boto3
import random
import datetime
from decimal import Decimal, getcontext
from boto3.dynamodb.conditions import *
import time

client = boto3.resource('dynamodb', region_name='eu-central-1')
events_table = client.Table('RASAEDRTable')
radar_table = client.Table('RASARadarTable')

DISTANCE_THRESHOLD = Decimal(str(0.3))
CONFIDENCE_THRESHOLD = Decimal(str(0.8))
VEHICLE_ID = []
TIMESTAMPS = []

def generate_timestamps(nitems):
    global TIMESTAMPS
    unique_ids = set()  # Use a set to store unique vehicle IDs


    while len(unique_ids) < nitems:
        random_time = (datetime.datetime.combine(datetime.date.today(), datetime.time()) +
                       datetime.timedelta(seconds=random.randint(0, 86399))).time()
        new_id = (str(datetime.date.today() + datetime.timedelta(random.randint(1, 999)))
                  + 'T' + random_time.strftime('%H:%M:%S') + 'Z' )
        unique_ids.add(new_id)
    TIMESTAMPS = list(unique_ids)

def generate_vehicle_id(nitems):
    global VEHICLE_ID
    unique_ids = set()  # Use a set to store unique vehicle IDs

    while len(unique_ids) < nitems:
        new_id = str(random.randint(1, 9999)).zfill(4)  # Generate a random ID and pad with zeros if necessary
        unique_ids.add(new_id)
    VEHICLE_ID = list(unique_ids)

EVENT_TYPES = ['rapid acc', 'rapid dec', 'drc event']

getcontext().prec = 3

def generate_radar_reading(vehicleID, timestamp, number_of_readings, potential_accident=False):
    object_type = ["vehicle", "cyclist ", "pedestrian ", "other"]
    object_size = ["small", "medium", "large"]

    radar_readings = []
    for i in range(number_of_readings):
        radar_readings.append({
            "timestamp": timestamp[:-1] + f":{i:03d}",
            "vehicle_id": vehicleID,
            "radar_id": "radar1",
            "distance": Decimal(str(random.uniform(0.001, 50) if not potential_accident else random.uniform(0.001, 5))),
            "velocity": random.randint(0, 30),
            "azimuth_angle": random.randint(0, 360),
            "elevation_angle": random.randint(-90, 90),
            "object_type": random.choice(object_type),
            "object_size": random.choice(object_size),
            "confidence_level": Decimal(str(random.uniform(0.5, 1.0) if potential_accident else random.uniform(0.1, 1.0)))
        })

    return radar_readings

def generate_events(nitems=20):
    events_to_insert = []
    for i in range(nitems):
        for j in range(100):
            event_type = EVENT_TYPES[random.randint(0, len(EVENT_TYPES) - 1)]
            events_to_insert.append({
              "timestamp": TIMESTAMPS[j],
              "vehicle_id": VEHICLE_ID[i],
              "event_id": VEHICLE_ID[i] + '#' + TIMESTAMPS[j],
              "event_type": event_type,
              "acceleration": {
                     "x": random.randint(-10, 10),
                     "y": random.randint(-10, 10),
                     "z": Decimal(str(9.8))
              },
              "location": {
                     "latitude": Decimal(str(37.7749)),
                     "longitude": Decimal(str(-122.4194))
              },
              "vehicle_speed": random.randint(0, 200),
              "fuel_level": random.randint(0, 100),
              "engine_rpm": 3000,
              "throttle_position": random.randint(0, 100),
              "brake_status": random.choice(['applied', 'non applied']),
              "seatbelt_status": random.choice(["locked", 'unlocked']),
              "airbag_deployed": str(random.choice([True, False])),
              "error_codes": ["P0101", "P0455"]
            })

            radar_to_insert = generate_radar_reading(VEHICLE_ID[i], TIMESTAMPS[j], 800, True)
            print(f'Created the {j}-th event')
            with radar_table.batch_writer() as batch:
                for item in radar_to_insert:
                    batch.put_item(Item=item)

        with events_table.batch_writer() as batch:
            for item in events_to_insert:
                batch.put_item(Item=item)


def extract_accidents(vehicle_id):
        #IndexName='EventTypeIndex',
    edr_events = events_table.query(
        KeyConditionExpression=Key('vehicle_id').eq(vehicle_id),
        FilterExpression=Attr('event_type').is_in(['rapid acc', 'rapid dec']),
    )['Items']

    accidents = []

    for event in edr_events:
        timestamp = event['timestamp'][:-1]
        radar_data = radar_table.query(
            KeyConditionExpression=Key('vehicle_id').eq(vehicle_id) & Key('timestamp').begins_with(timestamp),
            FilterExpression=(
                    Attr('object_type').is_in(['vehicle', 'pedestrian', 'cyclist']) &
                    Attr('confidence_level').gt(CONFIDENCE_THRESHOLD) &
                    Attr('distance').lt(DISTANCE_THRESHOLD)
            )
        )['Items']

        if radar_data:
            accidents.append(event['vehicle_id'] + ' ' + radar_data[0]['timestamp'] + ' ' + radar_data[0]['object_type'])

    return accidents


if __name__ == '__main__':
    #print(VEHICLE_ID)
    #print(TIMESTAMPS)

    start = time.time()
    print('Generating events...')
    generate_vehicle_id(1)
    generate_timestamps(100)
    generate_events(1)
    end = time.time()
    print('Events generated in: ')
    print(end - start)

    # start = time.time()
    # print(set(extract_accidents(str(7911))))
    # print(time.time() - start)




