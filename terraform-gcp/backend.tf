terraform {
  backend "gcs" {
    bucket = "portfolio-ai-tf-state"
    prefix = "terraform/state"
  }
}
