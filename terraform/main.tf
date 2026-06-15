# Single H100 VM for the MLOps assignment (Qwen3-30B-A3B + vLLM).
# Platform: gpu-h100-sxm, preset: 1gpu-16vcpu-200gb (1× H100 80GB).

resource "nebius_compute_v1_disk" "boot" {
  name           = "${var.vm_name}-boot"
  parent_id      = var.project_id
  size_gibibytes = var.boot_disk_size_gib
  type           = "NETWORK_SSD"
  source_image_family = {
    image_family = "ubuntu24.04-cuda13.0"
  }
  block_size_bytes = 4096
}

resource "nebius_compute_v1_instance" "h100" {
  name      = var.vm_name
  parent_id = var.project_id

  resources = {
    platform = "gpu-h100-sxm"
    preset   = "1gpu-16vcpu-200gb"
  }

  boot_disk = {
    existing_disk = {
      id = nebius_compute_v1_disk.boot.id
    }
    attach_mode = "READ_WRITE"
  }

  cloud_init_user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    ssh_public_key = var.ssh_public_key
    repo_url       = var.repo_url
  })

  network_interfaces = [
    {
      name       = "eth0"
      ip_address = {}
      public_ip_address = {
        static = true
      }
      subnet_id = var.subnet_id
    }
  ]
}

output "instance_id" {
  value = nebius_compute_v1_instance.h100.id
}

output "public_ip" {
  description = "SSH target for the assignment VM."
  value       = try(nebius_compute_v1_instance.h100.status.network_interfaces[0].public_ip_address.address, "")
}

output "ssh_hint" {
  value = "ssh ubuntu@${try(nebius_compute_v1_instance.h100.status.network_interfaces[0].public_ip_address.address, "<public-ip>")}"
}
