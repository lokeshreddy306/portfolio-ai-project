resource "google_compute_firewall" "allow_http" {

  name = "allow-http"

  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "5000"]
  }

  source_ranges = ["0.0.0.0/0"]

  target_tags = ["http-server"]
}
