const API_URL = "http://localhost:5721";

export async function getEvents() {
  const response = await fetch(`${API_URL}/events`);
  return response.json();
}
