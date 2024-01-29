import aiohttp
import asyncio
import json
import os


async def fetch(session, hash_value, name, api_key):
    api_url = f'https://api.ordinalsbot.com/search?hash={hash_value}'
    headers = {'x-api-key': api_key}

    async with session.get(api_url, headers=headers) as response:
        api_response = await response.json()

    count = api_response['count']
    inscriptionid = None if count == 0 else api_response['results'][0]['inscriptionid'] if count == 1 else min(
        api_response['results'], key=lambda x: x['createdat'])['inscriptionid']

    return {'name': name, 'hash': hash_value, 'inscriptionid': inscriptionid, 'inscribed': count}


async def update_status(session, status_list_to_update, api_key):
    tasks = [fetch(session, item['hash'], item['index'], api_key)
             for item in status_list_to_update]
    api_responses = await asyncio.gather(*tasks)

    index_to_inscriptionid = {}

    for status_item, api_response in zip(status_list_to_update, api_responses):
        index = status_item['index']
        status_item['inscriptionid'] = api_response['inscriptionid']
        status_item['inscribed'] = api_response['inscribed']

        index_to_inscriptionid[index] = status_item['inscriptionid']

    return index_to_inscriptionid


def initialize_status_file(status_file_path, items_count):
    initial_status = {
        "mintedNumber": 0,
        "data": [None] * items_count
    }

    with open(status_file_path, 'w') as status_file:
        json.dump(initial_status, status_file, indent=2)


async def main():
    api_key = '5949f0ce-ce56-4f93-a1d2-5468de231da0'
    items_file_path = 'data/items.json'
    status_file_path = 'data/status.json'

    with open(items_file_path, 'r') as items_file:
        items_data = json.load(items_file)

    # Check if status.json exists, if not, initialize it
    if not os.path.isfile(status_file_path):
        initialize_status_file(status_file_path, len(items_data))

    with open(status_file_path, 'r') as status_file:
        status_data = json.load(status_file)

    minted_count = 0
    minted_count_before = status_data['mintedNumber']

    # Filter out items with null inscriptionid from status_data's data
    status_list_to_update = [{'index': i, 'name': items_data[i]['name'], 'hash': items_data[i]['hash'],
                              'inscriptionid': None, 'inscribed': 0} for i in range(len(items_data)) if status_data['data'][i] is None]

    print("Starting hash check. This may take a few minutes...")
    async with aiohttp.ClientSession() as session:
        index_to_inscriptionid = await update_status(session, status_list_to_update, api_key)

    # Update status.json
    minted_count = sum(
        1 for item in status_list_to_update if item['inscriptionid'] is not None)
    status_data['mintedNumber'] += minted_count

    # Update data
    for index, inscriptionid in index_to_inscriptionid.items():
        status_data['data'][index] = inscriptionid

    with open(status_file_path, 'w') as status_file:
        json.dump(status_data, status_file, indent=2)

    minted_count_added = minted_count
    minted_count_after = status_data['mintedNumber']

    # Print the results
    print("Update summary:")
    print(f"Total supply of collection: {len(items_data)}")
    print(f"Minted items before update: {minted_count_before}")
    print(f"Items updated in this run : {len(status_list_to_update)}")
    print(f"Newly minted in this run  : {minted_count_added}")
    print(f"Total minted after update : {minted_count_after}")

    print("Update status completed.")

if __name__ == "__main__":
    asyncio.run(main())
