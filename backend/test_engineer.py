from ai.engineer import RaceEngineer

engineer = RaceEngineer()

sample = {
    "lap": 18,
    "speed": 302,
    "rpm": 11800,
    "throttle": 100,
    "brake": False,
    "gear": 8,
    "drs": 12
}

message = engineer.process(sample)

print(message)