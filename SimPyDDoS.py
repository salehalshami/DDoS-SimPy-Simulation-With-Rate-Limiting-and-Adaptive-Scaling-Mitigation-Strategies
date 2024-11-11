# This code simulates different mitigation strategies for handling DDoS attack on a server
# using the SimBy framework. It also tests varios cobinations of user and attacker request
# rates to evaluate two scenarios: rate limiting and adaptive scaling.

# Import Libraries
import simpy # provides a framework for simulating real-life events and processes.
import random # helps ingenerating random delays.
import matplotlib.pyplot as plt # used for visualizing the results through bar charts.

# Parameters
# These are initial configuration settings:
SERVER_INITIAL_CAPACITY = 1  # The starting server capacity.
SIM_TIME = 50 # Total simulation time.
RATE_LIMIT = 1       # Maximum requests per second for rate-limiing mode.
QUEUE_THRESHOLD = 3  # Queue length threshold to trigger adaptive scaling.
SCALING_DURATION = 5 # Duration for which the server capacity is scaled up in adaptive scaling.

# Different rate combinations for testing
# Each tuple represents different rates for user and attack requests, allowing us to test how
# the system handles varying loads. 
rate_combinations = [
    (100, 10),  # Scenario 1
    (50, 15),   # Scenario 2
    (80, 5),    # Scenario 3
    (60, 20)    # Scenario 4
]

# Server Class
# This class models the server behavior:
class Server:
    def __init__(self, env, scaling=False):
        self.env = env # The simulation environment
        self.server = simpy.Resource(env, capacity=SERVER_INITIAL_CAPACITY) # Represents server resources
                                                                    # with specified capacity.
        self.scaling = scaling # Boolean indicationg if adaptive scaling is enabled.
        self.server_capacity = SERVER_INITIAL_CAPACITY # Stores initial capacity to reset after scaling.
        self.legitimate_processed_requests = 0 # Tracking metric for legitimate processed requests.
        self.legitimate_dropped_requests = 0  # Tracking metric for legitimate dropped requests.
        self.response_times = [] # Collects response times for analysis.

# Process Requests
# This method processes requests by adding a simulated delay and record the response time.
    def process_request(self, request_type, start_time):
        yield self.env.timeout(random.expovariate(1.0))
        response_time = self.env.now - start_time
        self.response_times.append(response_time)
        print(f"{self.env.now:.2f}s: {request_type} request processed")

# Rate-Limited Requests
# This function implements rate-limiting by checking if the server's usage is
# below 'RATE_LIMIT'.If exceeded, legitimate requests are dropped.
    def rate_limited_request(self, request_type):
        # Apply rate limiting only to legitimate requests
        if request_type == "Legitimate" and self.server.count >= RATE_LIMIT:
            self.legitimate_dropped_requests += 1
            print(f"{self.env.now:.2f}s: {request_type} request dropped due to rate limit")
        else:
            start_time = self.env.now
            with self.server.request() as req:
                yield req
                yield self.env.process(self.process_request(request_type, start_time))
                if request_type == "Legitimate":
                    self.legitimate_processed_requests += 1

# Scale Resources
# If adaptive scaling is enabled, this function temporarily increases the server
# capacity when the queue length exceeds 'QUEUE_THROSHOLD'.
    def scale_resources(self):
        if self.scaling and len(self.server.queue) >= QUEUE_THRESHOLD:
            print(f"{self.env.now:.2f}s: Scaling up resources")
            self.server.capacity += 1
            yield self.env.timeout(SCALING_DURATION)
            self.server.capacity = self.server_capacity
            print(f"{self.env.now:.2f}s: Scaling down resources")

# Legitimate Request
# This function simulates legitimate requests, handling rate limiting and adaptive scaling.
def legitimate_user(env, server, scenario, user_rate):
    while True:
        yield env.timeout(random.expovariate(user_rate))
        print(f"{env.now:.2f}s: Legitimate request")
        
        if scenario == "Rate-Limiting":
            yield env.process(server.rate_limited_request("Legitimate"))
        elif scenario == "Adaptive Scaling":
            start_time = env.now
            with server.server.request() as req:
                yield req
                yield env.process(server.process_request("Legitimate", start_time))
                server.legitimate_processed_requests += 1
            env.process(server.scale_resources())

# Attacker Request Function
# This function generates attack requests at specified rates and handles requests
# based on the chosen mitigation scenario.
def attacker(env, server, scenario, attack_rate):
    while True:
        yield env.timeout(random.expovariate(attack_rate))
        print(f"{env.now:.2f}s: Attack request")

        if scenario == "Rate-Limiting":
            yield env.process(server.rate_limited_request("Attack"))
        elif scenario == "Adaptive Scaling":
            start_time = env.now
            with server.server.request() as req:
                yield req
                yield env.process(server.process_request("Attack", start_time))
            env.process(server.scale_resources())

# Running the Simulation
# This function initialize the environment, sets up processes for legitimate users and
# attackers, and runs the simulation. it returns key matrics for analysis. 
def run_simulation(scenario, user_rate, attack_rate):
    print(f"\n--- Running simulation with {scenario} mitigation strategy---")
    env = simpy.Environment()
    server = Server(env, scaling=(scenario == "Adaptive Scaling"))

    # Start processes
    env.process(legitimate_user(env, server, scenario, user_rate))
    env.process(attacker(env, server, scenario, attack_rate))

    # Run simulation
    env.run(until=SIM_TIME)

    # Collect metrics
    avg_response_time = sum(server.response_times) / len(server.response_times) if server.response_times else 0
    processed_requests = server.legitimate_processed_requests
    dropped_requests = server.legitimate_dropped_requests

    return avg_response_time, processed_requests, dropped_requests

# The Results
# Main Execution Loop
# Run simulations for each rate combination under both scenarios and stores the results
results = {"Rate-Limiting": {}, "Adaptive Scaling": {}}
for user_rate, attack_rate in rate_combinations:
    label = f"User Rate: {user_rate}, Attack Rate: {attack_rate}"
    results["Rate-Limiting"][label] = run_simulation("Rate-Limiting", user_rate, attack_rate)
    results["Adaptive Scaling"][label] = run_simulation("Adaptive Scaling", user_rate, attack_rate)

# Plot the results
for mitigation_strategy in results:
    scenarios = list(results[mitigation_strategy].keys())
    avg_response_times = [results[mitigation_strategy][scenario][0] for scenario in scenarios]
    processed_requests = [results[mitigation_strategy][scenario][1] for scenario in scenarios]
    dropped_requests = [results[mitigation_strategy][scenario][2] for scenario in scenarios]

    fig, ax = plt.subplots(3, 1, figsize=(12, 18)) # To create three vertically stacked subplots, one for
    # each metric, and define the dememinsions of the entire figure with 'figsize' attribute.
    
    fig.suptitle(f"{mitigation_strategy} Results") # To add a main title to the figure

    # Average Response Time subplots
    ax[0].bar(scenarios, avg_response_times, color=['#4C72B0', '#55A868', '#C44E52', '#8172B2'])
    ax[0].set_title("Average Response Time for Each Scenario")
    ax[0].set_ylabel("Time (s)") # To add label for the y-axis
    ax[0].tick_params(axis='x') # Formatting the x-axis 
    for i, v in enumerate(avg_response_times):
        ax[0].text(i, v + 0.1, f"{v:.2f}", ha='center') # Each bar includes the correspondind value 

    # Processed Legitimate Requests subplots
    ax[1].bar(scenarios, processed_requests, color=['#4C72B0', '#55A868', '#C44E52', '#8172B2'])
    ax[1].set_title("Processed Legitimate Requests for Each Scenario")
    ax[1].set_ylabel("Processed Requests")
    ax[1].tick_params(axis='x')
    for i, v in enumerate(processed_requests):
        ax[1].text(i, v + 0.1, str(v), ha='center')

    # Dropped Legitimate Requests subplots
    ax[2].bar(scenarios, dropped_requests, color=['#4C72B0', '#55A868', '#C44E52', '#8172B2'])
    ax[2].set_title("Dropped Legitimate Requests for Each Scenario")
    ax[2].set_ylabel("Dropped Requests")
    ax[2].tick_params(axis='x')
    for i, v in enumerate(dropped_requests):
        ax[2].text(i, v + 0.1, str(v), ha='center')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # To adjust subplot spacing to ensure emements do not overlap
    # 'rect' parameter shifts the layout to accommodate the main title
    plt.show()
