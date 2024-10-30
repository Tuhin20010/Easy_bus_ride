class Bus:
    def __init__(self, bus_number, bus_name, route):
        self.bus_number = bus_number
        self.bus_name = bus_name
        self.route = route

    def to_dict(self):
        return {
            "bus_number": self.bus_number,
            "bus_name": self.bus_name,
            "route": self.route
        }
