# Program adapted from ChatGPT response: https://chatgpt.com/share/6720f1b3-23a0-8005-833e-b4d84e186d76

from flask import Flask, request, jsonify
from waitress import serve
from geopy.distance import geodesic
import time

app = Flask(__name__)

# Dictionary to store player data
players_data = {}

# Proximity radius in meters, determines if players have passed by each other
PROXIMITY_RADIUS = 30
# Update frequency in seconds
UPDATE_FREQUENCY = 100

@app.route('/generate_player_id', methods=['POST'])
def generate_player_id():
    data = request.get_json()
    name = data.get("Name")
    avatar = data.get("Avatar")
    location = data.get("location")

    player_id = len(players_data)
    players_data[player_id] = {
        "ID": player_id,
        "Name": name,
        "Avatar": avatar,
        "location": location,
        "timestamp": time.time(),
        "incoming_friend_requests": {},
        "outgoing_friend_requests": {}
    }

    print(players_data)
    
    return jsonify({"player_id": player_id}), 200

@app.route('/get_nearby_players', methods=['POST'])
def get_nearby_players():
    data = request.get_json()
    player_id = data.get("player_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if player_id is None or latitude is None or longitude is None:
        return jsonify({"error": "Invalid data"}), 400

    # Update player location on server
    players_data[player_id]["location"] = {
        "latitude": latitude,
        "longitude": longitude
    }
    current_timestamp = time.time()
    players_data[player_id]["timestamp"] = current_timestamp

    # Get nearby players
    nearby_players = {}
    current_position = (latitude, longitude)

    for other_id, info in players_data.items():
        if other_id == player_id:
            continue

        # Get the other player's name
        name = info["Name"]

        # Get the other player's avatar
        avatar = info["Avatar"]
        
        # Calculate the distance
        other_position = (info["location"]["latitude"], info["location"]["longitude"])
        distance = geodesic(current_position, other_position).meters
        print(f"Distance between {players_data[player_id]["Name"]} and {name} is {distance}m")

        # Calculate update timing difference between players
        other_timestamp = info["timestamp"]
        time_difference = current_timestamp - other_timestamp

        # If other player is nearby, add them to nearby players dict
        if distance <= PROXIMITY_RADIUS and time_difference <= UPDATE_FREQUENCY:
            nearby_players[other_id] = {
                "ID": other_id,
                "Name": name,
                "Avatar": avatar
            }
            print(players_data[player_id]["Name"] + " passed by " + name)

    return jsonify(nearby_players), 200

@app.route('/get_incoming_friend_requests', methods=['POST'])
def get_incoming_friend_requests():
    data = request.get_json()
    player_id = data.get("player_id")

    return jsonify(players_data[player_id]["incoming_friend_requests"]), 200

@app.route('/get_outgoing_friend_requests', methods=['POST'])
def get_outgoing_friend_requests():
    data = request.get_json()
    player_id = data.get("player_id")

    # Save current outgoing requests
    response = jsonify(players_data[player_id]["outgoing_friend_requests"])

    to_remove = []

    # Loop through all outgoing requests
    for key in players_data[player_id]["outgoing_friend_requests"].keys():
        # If an outgoing request is not pending (i.e. "accepted" or "rejected"), add the key to a list for later removal
        if players_data[player_id]["outgoing_friend_requests"][key] != "pending":
            to_remove.append(key)

    # Delete outgoing requests using keys in list
    for key in to_remove:
        players_data[player_id]["outgoing_friend_requests"].pop(key)
            
    # Return outgoing requests for processing by client
    return response, 200

@app.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    data = request.get_json()
    sender_id = data.get("sender_id")
    recipient_id = data.get("recipient_id")

    # Append current friend request to recipient's incoming requests
    players_data[recipient_id]["incoming_friend_requests"][sender_id] = "pending"

    # Append current friend request to sender's outgoing requests
    players_data[sender_id]["outgoing_friend_requests"][recipient_id] = "pending"

    print(f"{players_data[sender_id]['Name']} sent a friend request to {players_data[recipient_id]['Name']}")

    return "Friend request sent!", 200

@app.route('/respond_to_friend_request', methods=['POST'])
def respond_to_friend_request():
    data = request.get_json()
    sender_id = data.get("sender_id")
    recipient_id = data.get("recipient_id")
    accepted = data.get("accepted")

    # Set to accepted/declined for processing by sender
    if accepted:
        players_data[recipient_id]["incoming_friend_requests"][sender_id] = "accepted"
        players_data[sender_id]["outgoing_friend_requests"][recipient_id] = "accepted"
    else:
        players_data[recipient_id]["incoming_friend_requests"][sender_id] = "declined"
        players_data[sender_id]["outgoing_friend_requests"][recipient_id] = "declined"

    print(f"{players_data[recipient_id]['Name']} {players_data[recipient_id]['incoming_friend_requests'][sender_id]} {players_data[sender_id]['Name']}'s friend request") # "A accepted/declined B's friend request"

    return "Friend request processed!", 200

if __name__ == '__main__':
    serve(app, host="0.0.0.0", port=5000)
