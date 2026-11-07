/**
 * MQTT client standing in for the IPS proxy side of the framework.
 *
 * Publishes voltage setpoints on circuit/setpoint/cmd and subscribes to
 * capacitor-voltage feedback on circuit/state/value (Table 4.3).
 */

#include <mqtt/async_client.h>
#include <nlohmann/json.hpp>

#include <atomic>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

using json = nlohmann::json;
using namespace std::chrono_literals;

namespace {
constexpr const char* kBroker = "tcp://localhost:1883";
constexpr const char* kClientId = "ABB_PROXY";
constexpr const char* kSetpointTopic = "circuit/setpoint/cmd";
constexpr const char* kStateTopic = "circuit/state/value";
constexpr int kQos = 1;

class StateCallback : public virtual mqtt::callback {
public:
    void message_arrived(mqtt::const_message_ptr msg) override {
        try {
            const auto data = json::parse(msg->get_payload_str());
            const double time_s = data.value("time", 0.0);
            const double value = data.at("value").get<double>();
            const double setpoint = data.value("setpoint", 0.0);
            std::cout << "[state] t=" << time_s << " s  "
                      << "Vout=" << value << " V  "
                      << "Vin=" << setpoint << " V\n";
            last_value_.store(value);
            got_state_.store(true);
        } catch (const std::exception& e) {
            std::cerr << "Invalid state payload: " << e.what() << '\n';
        }
    }

    void connection_lost(const std::string& cause) override {
        std::cerr << "Connection lost";
        if (!cause.empty()) {
            std::cerr << ": " << cause;
        }
        std::cerr << '\n';
    }

    bool got_state() const { return got_state_.load(); }
    double last_value() const { return last_value_.load(); }

private:
    std::atomic<bool> got_state_{false};
    std::atomic<double> last_value_{0.0};
};

void publish_setpoint(mqtt::async_client& client, double voltage) {
    const auto payload = json({{"setpoint", voltage}}).dump();
    auto msg = mqtt::make_message(kSetpointTopic, payload);
    msg->set_qos(kQos);
    msg->set_retained(true);  // latest setpoint available to late subscribers
    client.publish(msg)->wait();
    std::cout << "[cmd] setpoint -> " << voltage << " V\n";
}
} 

int main(int argc, char* argv[]) {
    // Default step sequence matches the physical AO1 test (Section 3.4.1).
    std::vector<double> steps = {0.0, 5.0, 10.0};
    auto hold = 5s;

    if (argc >= 2) {
        steps.clear();
        for (int i = 1; i < argc; ++i) {
            steps.push_back(std::stod(argv[i]));
        }
    }

    mqtt::async_client client(kBroker, kClientId);
    StateCallback cb;
    client.set_callback(cb);

    mqtt::connect_options options;
    options.set_clean_session(true);
    options.set_keep_alive_interval(30);

    std::cout << "Connecting to " << kBroker << "...\n";
    client.connect(options)->wait();

    client.subscribe(kStateTopic, kQos)->wait();
    std::cout << "Subscribed to " << kStateTopic << '\n';

    for (const double voltage : steps) {
        publish_setpoint(client, voltage);
        std::this_thread::sleep_for(hold);
    }

    // Leave the last setpoint retained, disconnect cleanly.
    client.disconnect()->wait();
    std::cout << "Done. Last Vout seen: " << cb.last_value() << " V\n";
    return 0;
}
