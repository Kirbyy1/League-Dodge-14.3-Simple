from lcu_driver import Connector
import json
import urllib.parse
import asyncio

# Initialize the connector here but don't start it yet
connector = Connector()

async def get_id_token(connection):
    response = await connection.request('get', '/lol-rso-auth/v1/authorization/id-token')
    if response.status == 200:
        data = await response.json()
        return data.get('token')
    else:
        print("Failed to get ID token. Status code:", response.status)

async def get_summoner_jwt(connection):
    response = await connection.request('get', '/lol-summoner/v1/current-summoner/jwt')
    if response.status == 200:
        summoner_jwt = await response.text()
        return summoner_jwt.strip('"')
    else:
        print("Failed to get Summoner JWT. Status code:", response.status)

async def get_rso_user_info(connection):
    response = await connection.request('get', '/lol-rso-auth/v1/authorization/userinfo')
    if response.status == 200:
        data = await response.json()
        return data.get('userInfo')
    else:
        print("Failed to get RSO User Info. Status code:", response.status)

async def get_rso_inventory_jwt(connection):
    response = await connection.request('get', '/lol-inventory/v1/champSelectInventory')
    if response.status == 200:
        data = await response.json()
        return data
    else:
        print("Failed to get Inventory JWT. Status code:", response.status)

async def get_current_game_version(connection):
    response = await connection.request('get', '/lol-patch/v1/game-version')
    if response.status == 200:
        data = await response.json()
        # Assuming the game version is directly in the response body
        print(f"Current Game Version: {data}")  # Print the fetched game version
        return data
    else:
        print("Failed to get current game version. Status code:", response.status)
        return None
    
async def create_practice_game(connection, game_config):
    # Quit any existing game session first
    quit_game_response = await connection.request('post', "/lol-login/v1/session/invoke?destination=gameService&method=quitGame&args=[]", json={})
    if quit_game_response.status in [200, 201]:
        print("Successfully quit any existing game.")
    else:
        print(f"Failed to quit existing game. Status code: {quit_game_response.status}")

    # Create a new practice game
    serialized_game_config = json.dumps([game_config])
    args_encoded = urllib.parse.quote_plus(serialized_game_config)
    create_game_response = await connection.request('post', f"/lol-login/v1/session/invoke?destination=gameService&method=createPracticeGameV4&args={args_encoded}", json={})
    if create_game_response.status in [200, 201]:
        print("Practice game created successfully.")
        game_id_response = await create_game_response.json()
        if 'body' in game_id_response and 'id' in game_id_response['body']:
            game_id = int(float(game_id_response['body']['id']))
            print(f"Game ID: {game_id}")

            # Start champion selection
            args_for_champ_select = json.dumps(["1", "1"])  # You might need to adjust these parameters
            args_encoded_for_champ_select = urllib.parse.quote_plus(args_for_champ_select)
            champ_select_response = await connection.request('post', f"/lol-login/v1/session/invoke?destination=gameService&method=startChampionSelection&args={args_encoded_for_champ_select}", json={})
            if champ_select_response.status in [200, 201]:
                print("Champion selection started successfully.")

                # Select a champion
                args_for_select_champion = json.dumps(["1", "1000"])  # Replace "1" with session ID and "1000" with the champion ID
                args_encoded_for_select_champion = urllib.parse.quote_plus(args_for_select_champion)
                select_champion_response = await connection.request('post', f"/lol-login/v1/session/invoke?destination=gameService&method=selectChampionV2&args={args_encoded_for_select_champion}", json={})
                if select_champion_response.status in [200, 201]:
                    print("Champion selected successfully.")

                    # Lock in the champion
                    lock_in_response = await connection.request('post', "/lol-login/v1/session/invoke?destination=gameService&method=championSelectCompleted&args=[]", json={})
                    if lock_in_response.status in [200, 201]:
                        print("Champion locked in successfully.")
                    else:
                        print(f"Failed to lock in champion. Status code: {lock_in_response.status}")
                else:
                    print(f"Failed to select champion. Status code: {select_champion_response.status}")
            else:
                print(f"Failed to start champion selection. Status code: {champ_select_response.status}")
        else:
            print("Game created, but no game ID found in the response.")
    else:
        print("Failed to create practice game.")
        print(f"Response status code: {create_game_response.status}, response body: {await create_game_response.json()}")

@connector.ready
async def connected(connection):
    print('Connected to the LCU API.')
    # Logic to get tokens and user info, and create a game lobby
    GetRSOIdToken = await get_id_token(connection)
    GetRSOSummonerJWT = await get_summoner_jwt(connection)
    GetRSOUserInfo = await get_rso_user_info(connection)
    GetRSOInventoryJWT = await get_rso_inventory_jwt(connection)
    current_game_version = await get_current_game_version(connection)
    
    # Define the game configuration
    gameMap = {
        "__class": "com.riotgames.platform.game.map.GameMap",
        "description": "",
        "displayName": "",
        "mapId": 11,
        "minCustomPlayers": 1,
        "name": "",
        "totalPlayers": 10
    }

    practiceGameConfig = {
        "__class": "com.riotgames.platform.game.PracticeGameConfig",
        "allowSpectators": "ALL",
        "spectatorDelayEnabled": True,
        "gameMap": gameMap,
        "gameMode": "CLASSIC",
        "gameMutators": [],
        "gameName": "test lobbyuwu",
        "gamePassword": "",
        "gameTypeConfig": 1,
        "gameVersion": current_game_version,
        "maxNumPlayers": 10,
        "passbackDataPacket": None,
        "passbackUrl": None,
        "region": ""
    }
    game_config = {
        "__class": "com.riotgames.platform.game.lcds.dto.CreatePracticeGameRequestDto",
        "practiceGameConfig": practiceGameConfig,
        "simpleInventoryJwt": GetRSOInventoryJWT,
        "playerGcoTokens": {
            "__class": "com.riotgames.platform.util.tokens.PlayerGcoTokens",
            "idToken": GetRSOIdToken,
            "userInfoJwt": GetRSOUserInfo,
            "summonerToken": GetRSOSummonerJWT
        }
    }

    await create_practice_game(connection, game_config)

@connector.close
async def disconnected(connection):
    print('Disconnected from the LCU API.')

if __name__ == '__main__':
    connector.start()
