import React, { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE_URL } from "../main";
import { Table } from "@tabler/core";

export default function EventTable() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/events`);
        setEvents(response.data);
      } catch (err) {
        console.error("Error fetching events:", err);
      }
    };

    fetchEvents();
    const interval = setInterval(fetchEvents, 5000); // refresh every 5s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="card m-4 p-4 shadow rounded-2xl">
      <h2 className="text-xl font-bold mb-3">Active Events</h2>
      <Table>
        <thead>
          <tr>
            <th>Event ID</th>
            <th>Start Time</th>
            <th>End Time</th>
            <th>Participants</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.event_id}>
              <td>{event.event_id}</td>
              <td>{new Date(event.start_time).toLocaleString()}</td>
              <td>{new Date(event.end_time).toLocaleString()}</td>
              <td>{event.user_count}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
