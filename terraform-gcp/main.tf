resource "google_compute_instance" "portfolio_vm" {

  name         = "portfolio-vm"
  machine_type = "e2-standard-2"
  zone         = "asia-south1-a"

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30
    }
  }

  network_interface {
    network = "default"

    access_config {
    }
  }

  metadata_startup_script = <<-EOF
#!/bin/bash

apt update

apt install -y docker.io docker-compose git

systemctl enable docker
systemctl start docker

EOF

  tags = ["http-server"]
}
