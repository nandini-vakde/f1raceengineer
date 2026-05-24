import fastf1

# 1. Enable caching in a local directory
fastf1.Cache.enable_cache('f1_cache') 

# 2. Get a specific session (Year, Location, Session Type)
# Session types: 'FP1', 'FP2', 'FP3', 'Q' (Qualifying), 'S' (Sprint), 'R' (Race)
session = fastf1.get_session(2024, 'Monaco', 'R')

# 3. Download and load the data into memory
session.load()
