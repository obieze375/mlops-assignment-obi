terraform {
  required_version = ">= 1.4"

  required_providers {
    nebius = {
      source  = "nebius/nebius"
      version = ">= 0.6.8"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

# Uses the default Nebius CLI profile (~/.nebius/config.yaml) or NEBIUS_IAM_TOKEN.
# Run `nebius profile create` once before `terraform apply`.
provider "nebius" {
  domain = var.region
}
