"""
Sample Agent for Testing
"""

class SampleAgent:
    def __init__(self, config=None):
        self.config = config or {}
        self.name = "SampleAgent"
        
    def hello(self):
        return "Hello from SampleAgent!"
        
    def process(self, data):
        return {
            "agent": self.name,
            "processed_data": data,
            "status": "success"
        }
        
    def self_describe(self):
        return {
            "name": self.name,
            "description": "A sample agent for testing purposes",
            "methods": {
                "hello": {
                    "description": "Returns a hello message",
                    "parameters": {}
                },
                "process": {
                    "description": "Processes given data",
                    "parameters": {
                        "data": {
                            "type": "string",
                            "description": "Data to process",
                            "required": True
                        }
                    }
                }
            }
        }

if __name__ == "__main__":
    agent = SampleAgent()
    print(agent.hello())