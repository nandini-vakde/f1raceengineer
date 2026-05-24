import fastf1

# 1. Enable caching in a local directory
fastf1.Cache.enable_cache('f1_cache') 

# 2. Get a specific session (Year, Location, Session Type)
# Session types: 'FP1', 'FP2', 'FP3', 'Q' (Qualifying), 'S' (Sprint), 'R' (Race)
session = fastf1.get_session(2024, 'Monaco', 'R')

# 3. Download and load the data into memory
session.load()

# Access the overall results DataFrame
results = session.results

# View specific columns for the top 5 finishers
print(results[['Position', 'BroadcastName', 'TeamName', 'GridPosition', 'Points']].head())

# Get all laps from the session
all_laps = session.laps

# Filter for a specific driver (e.g., Max Verstappen 'VER')
ver_laps = all_laps.pick_driver('VER')

# Get their absolute fastest lap
fastest_lap = ver_laps.pick_fastest()

# Access specific values from that lap
print(f"Fastest Lap Time: {fastest_lap['LapTime']}")
print(f"Sector 1 Time: {fastest_lap['Sector1Time']}")
print(f"Tire Compound Used: {fastest_lap['Compound']}")

# Get the telemetry data for Verstappen's fastest lap
telemetry = fastest_lap.get_telemetry()

# This is also a DataFrame; print the first few rows
print(telemetry[['Speed', 'RPM', 'Throttle', 'Brake', 'X', 'Y']].head())

# Find his maximum speed during that lap
max_speed = telemetry['Speed'].max()
print(f"Top Speed on fastest lap: {max_speed} km/h")