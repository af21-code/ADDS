using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace AddsTelemetryClient
{
    public record TelemetryPacket(
        double timestamp_ms,
        double vehicle_speed_kph,
        int engine_rpm,
        double clutch_slip_rpm,
        string fsm_state,
        double fuel_saved_pct
    );

    class Program
    {
        static void Main()
        {
            const int listenPort = 5005;
            using var udpClient = new UdpClient(listenPort);
            var remoteEndPoint = new IPEndPoint(IPAddress.Any, listenPort);

            Console.WriteLine($"[VCARB-Style Telemetry Receiver] Listening on UDP port {listenPort}...");

            while (true)
            {
                byte[] receivedBytes = udpClient.Receive(ref remoteEndPoint);
                string json = Encoding.UTF8.GetString(receivedBytes);
                var packet = JsonSerializer.Deserialize<TelemetryPacket>(json);

                if (packet is not null)
                {
                    Console.WriteLine(
                        $"[{packet.timestamp_ms,7:F1} ms] State: {packet.fsm_state,-12} | " +
                        $"Speed: {packet.vehicle_speed_kph,6:F2} km/h | " +
                        $"RPM: {packet.engine_rpm,5} | Slip: {packet.clutch_slip_rpm,5:F1} RPM"
                    );
                }
            }
        }
    }
}
