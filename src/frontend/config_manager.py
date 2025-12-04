import json
import os

class ConfigManager:
    _instance = None
    _config = {}
    _config_path = os.path.join(os.getcwd(), 'config.json')

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r') as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self._config = {}
        else:
            print("Config file not found, using defaults.")
            self._config = {}

    def get_modules(self) -> dict:
        return self._config.get('modules', {})

    def get_gestures(self) -> dict:
        return self._config.get('gestures', {})
